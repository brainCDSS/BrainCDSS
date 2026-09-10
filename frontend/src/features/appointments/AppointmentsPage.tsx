import { useCallback, useEffect, useMemo, useState } from "react";

import type { LoginUser } from "../auth/types";
import {
  acceptAppointment,
  completeAppointment,
  getAppointmentDetail,
  getAppointmentRequests,
  getClinicianSchedule,
  getStaffAppointments,
  rejectAppointment,
  saveClinicianSchedule,
} from "./api";
import type { ScheduleRule, StaffAppointment } from "./types";

import "./appointments.css";

type PageTab = "appointments" | "schedule" | "requests" | "manage";
const APPOINTMENTS_PER_PAGE = 8; //한화면에 목록 몇개 출력할지 결정

const STATUS_OPTIONS = ["", "REQUESTED", "CONFIRMED", "IN_PROGRESS", "COMPLETED", "CANCELLED", "REJECTED"];
const WEEKDAYS = ["월", "화", "수", "목", "금", "토", "일"];

function todayValue() {
  const now = new Date();
  return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, "0")}-${String(now.getDate()).padStart(2, "0")}`;
}

function appointmentId(item: StaffAppointment & { id?: string }) {
  return item.appointment_id || item.id || "";
}

function appointmentStart(item: StaffAppointment) {
  return item.start_at ?? item.slot?.start_at ?? null;
}

function formatTime(value?: string | null) {
  if (!value) return "-";
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? value : date.toLocaleTimeString("ko-KR", { hour: "2-digit", minute: "2-digit", hour12: false });
}

function formatDateTime(value?: string | null) {
  if (!value) return "-";
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? value : date.toLocaleString("ko-KR");
}

function normalize(items: Array<StaffAppointment & { id?: string }>) {
  return items.map((item) => ({ ...item, appointment_id: appointmentId(item) })).filter((item) => item.appointment_id);
}

function can(user: LoginUser, permission: string) {
  return user.permissions.includes(permission);
}

export default function AppointmentsPage({ currentUser }: { currentUser: LoginUser }) {
  const [activeTab, setActiveTab] = useState<PageTab>("appointments");
  const [date, setDate] = useState(todayValue());
  const [status, setStatus] = useState("");
  const [search, setSearch] = useState("");
  const [clinicianId, setClinicianId] = useState("");
  const [appointments, setAppointments] = useState<StaffAppointment[]>([]);
  const [requests, setRequests] = useState<StaffAppointment[]>([]);
  const [selected, setSelected] = useState<StaffAppointment | null>(null);
  const [schedule, setSchedule] = useState<ScheduleRule[]>([]);
  const [draftRule, setDraftRule] = useState<ScheduleRule>({ weekday: 0, start_time: "09:00", end_time: "17:00", slot_minutes: 30, effective_from: todayValue(), effective_to: null, is_active: true });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);
  const [page, setPage] = useState(1);
  const [totalCount, setTotalCount] = useState(0);
  const [usesApiPagination, setUsesApiPagination] = useState(false);
  const [hasNextPage, setHasNextPage] = useState(false);
  const [hasPreviousPage, setHasPreviousPage] = useState(false);

  const role = currentUser.role.code;
  const isDoctor = role === "NEUROLOGIST" || role === "NEUROSURGEON";
  const isNurse = role === "NURSE";
  const isAdmin = role === "SYSTEM_ADMIN";
  const mayReadStaff = can(currentUser, "appointment.read.staff");
  const mayManageSchedule = can(currentUser, "schedule.manage");

  const loadAppointments = useCallback(async () => {
    if (!mayReadStaff) return;
    setLoading(true);
    setError(null);
    try {
      const response = await getStaffAppointments({ date, clinicianId: clinicianId || undefined, status: status || undefined, page, pageSize: APPOINTMENTS_PER_PAGE });
      const apiPaginated = Array.isArray(response.results);
      const items = normalize(response.results ?? response.appointments ?? []);
      setAppointments(items);
      setUsesApiPagination(apiPaginated);
      setTotalCount(apiPaginated ? (response.count ?? items.length) : items.length);
      setHasNextPage(apiPaginated && response.next != null);
      setHasPreviousPage(apiPaginated && response.previous != null);
    } catch {
      setError("예약 일정을 불러오지 못했습니다. 현재 계정의 역할과 권한을 확인해 주세요.");
    } finally {
      setLoading(false);
    }
  }, [clinicianId, date, mayReadStaff, page, status]);

  useEffect(() => { void loadAppointments(); }, [loadAppointments]);

  const clinicianOptions = useMemo(() => {
    const values = new Map<string, string>();
    appointments.forEach((item) => {
      const id = item.clinician?.id ?? item.clinician_id;
      if (id) values.set(id, item.clinician?.name ?? id);
    });
    return [...values.entries()];
  }, [appointments]);

  const visibleAppointments = useMemo(() => {
    const keyword = search.trim().toLowerCase();
    if (!keyword) return appointments;
    return appointments.filter((item) => `${item.patient?.name ?? ""} ${item.patient?.patient_no ?? ""} ${item.patient_id ?? ""}`.toLowerCase().includes(keyword));
  }, [appointments, search]);

  const pagedAppointments = useMemo(() => {
    if (usesApiPagination) return visibleAppointments;
    const start = (page - 1) * APPOINTMENTS_PER_PAGE;
    return visibleAppointments.slice(start, start + APPOINTMENTS_PER_PAGE);
  }, [page, usesApiPagination, visibleAppointments]);
  const visibleTotal = usesApiPagination ? totalCount : visibleAppointments.length;
  const pageCount = Math.max(1, Math.ceil(visibleTotal / APPOINTMENTS_PER_PAGE));

  useEffect(() => { setPage(1); }, [search, status, date, clinicianId]);

  const todayAppointments = useMemo(() => appointments.filter((item) => appointmentStart(item)?.slice(0, 10) === date), [appointments, date]);
  const hasTimelineData = todayAppointments.some((item) => appointmentStart(item));
  const summary = {
    scheduled: todayAppointments.filter((item) => item.status === "CONFIRMED").length,
    waiting: todayAppointments.filter((item) => item.status === "REQUESTED").length,
    completed: todayAppointments.filter((item) => item.status === "COMPLETED").length,
  };

  async function selectAppointment(item: StaffAppointment) {
    setActionError(null);
    try {
      const detail = await getAppointmentDetail(item.appointment_id);
      setSelected({ ...detail, appointment_id: appointmentId(detail) });
    } catch {
      setSelected(item);
      setActionError("예약 상세를 불러오지 못했습니다.");
    }
  }

  async function handleComplete() {
    if (!selected) return;
    setActionError(null);
    try {
      await completeAppointment(selected.appointment_id);
      await loadAppointments();
      setSelected(null);
    } catch { setActionError("완료 처리에 실패했습니다."); }
  }

  async function loadRequests() {
    if (!isNurse || !mayReadStaff) return;
    setLoading(true);
    setError(null);
    try { setRequests(normalize((await getAppointmentRequests({ date, clinicianId: clinicianId || undefined })).results)); }
    catch { setError("예약 요청을 불러오지 못했습니다."); }
    finally { setLoading(false); }
  }

  async function processRequest(id: string, action: "accept" | "reject") {
    setActionError(null);
    try {
      if (action === "accept") await acceptAppointment(id);
      else {
        const reason = window.prompt("거절 사유를 입력해 주세요.");
        if (!reason?.trim()) return;
        await rejectAppointment(id, reason.trim());
      }
      await loadRequests();
      await loadAppointments();
    } catch { setActionError(action === "accept" ? "예약 승인에 실패했습니다." : "예약 거절에 실패했습니다."); }
  }

  async function loadSchedule() {
    if (!clinicianId) return;
    setLoading(true);
    setError(null);
    try {
      const response = await getClinicianSchedule(clinicianId, date, date);
      setSchedule((response.rules ?? response.results ?? []).filter((rule) => !rule.clinician_id || rule.clinician_id === clinicianId));
    } catch { setError("의료진 스케줄을 불러오지 못했습니다."); }
    finally { setLoading(false); }
  }

  async function saveSchedule() {
    if (!clinicianId || !mayManageSchedule) return;
    setActionError(null);
    try {
      const response = await saveClinicianSchedule(clinicianId, schedule);
      setSchedule(response.rules ?? response.results ?? []);
    } catch { setActionError("스케줄 저장에 실패했습니다."); }
  }

  function openTab(tab: PageTab) {
    setActiveTab(tab);
    setError(null);
    setActionError(null);
    if (tab === "requests") void loadRequests();
    if ((tab === "schedule" || tab === "manage") && clinicianId) void loadSchedule();
  }

  return <section className="appointment-page">
    <header className="appointment-heading"><div><span>Clinical schedule</span><h2>예약 · 일정</h2><p>Backend 예약 및 의료진 일정 API에 연결된 업무 화면입니다.</p></div><label>조회 날짜<input type="date" value={date} onChange={(event) => setDate(event.target.value)} /></label></header>

    <section className="appointment-today" aria-label="오늘 일정 요약">
      <header><div><span>Today summary</span><h3>오늘 일정 <strong>{date.replaceAll("-", ".")}</strong></h3></div>{!hasTimelineData && <small>API 응답에 예약 시간이 없어 오늘 집계를 계산할 수 없습니다.</small>}</header>
      <div className="appointment-summary-grid">
        {[['진료 예정', hasTimelineData ? summary.scheduled : '-'], ['진료중', '-'], ['대기', hasTimelineData ? summary.waiting : '-'], ['진료 완료', hasTimelineData ? summary.completed : '-']].map(([label, value]) => <article key={String(label)}><span>{label}</span><strong>{value}</strong></article>)}
      </div>
    </section>

    <nav className="appointment-tabs" aria-label="예약 일정 분류">
      <button className={activeTab === "appointments" ? "is-active" : ""} onClick={() => openTab("appointments")} type="button">예약 목록</button>
      <button className={activeTab === "schedule" ? "is-active" : ""} onClick={() => openTab("schedule")} type="button">진료 일정</button>
      <button className={activeTab === "requests" ? "is-active" : ""} onClick={() => openTab("requests")} type="button" disabled={!isNurse}>예약 요청</button>
      <button className={activeTab === "manage" ? "is-active" : ""} onClick={() => openTab("manage")} type="button" disabled={!(isDoctor || isNurse) || !mayManageSchedule}>스케줄 관리</button>
    </nav>

    {(activeTab === "appointments" || activeTab === "schedule") && <div className="appointment-workspace">
      <main className="appointment-list-card">
        <div className="appointment-filters"><label>환자 검색<input value={search} onChange={(event) => setSearch(event.target.value)} placeholder="환자명, 환자번호 또는 ID" /></label><label>상태<select value={status} onChange={(event) => setStatus(event.target.value)}>{STATUS_OPTIONS.map((value) => <option value={value} key={value || "all"}>{value || "전체"}</option>)}</select></label><label>날짜<input type="date" value={date} onChange={(event) => setDate(event.target.value)} /></label><label>담당 의료진<select value={clinicianId} onChange={(event) => setClinicianId(event.target.value)}><option value="">API 범위 전체</option>{clinicianOptions.map(([id, name]) => <option value={id} key={id}>{name}</option>)}</select></label></div>
        <div className="appointment-list-meta"><strong>총 {visibleTotal}건</strong></div>
        {!mayReadStaff || isAdmin ? <div className="appointment-empty">현재 역할에는 의료진 예약 일정 API 접근 권한이 없습니다.
        </div> : loading ? <div className="appointment-empty">불러오는 중...</div> : error ? <div className="appointment-empty is-error">{error}</div> : pagedAppointments.length === 0 ? <div className="appointment-empty">조회된 예약 일정이 없습니다.</div> : <div className="appointment-table-wrap"><table><thead><tr><th>시간</th><th>환자</th><th>진료과</th><th>담당의</th><th>상태</th><th>예약 유형</th><th>작업</th></tr></thead><tbody>{pagedAppointments.map((item) => <tr key={item.appointment_id} onClick={() => void selectAppointment(item)}><td>{formatTime(appointmentStart(item))}</td><td><strong>{item.patient?.name ?? item.patient_id ?? "-"}</strong><small>{item.patient?.patient_no ?? ""}</small></td><td>{item.department?.name ?? item.department_id ?? "-"}</td><td>{item.clinician?.name ?? item.clinician_id ?? "-"}</td><td><span className={`appointment-status is-${item.status.toLowerCase()}`}>{item.status}</span></td><td>{item.request_type ?? "-"}</td><td><button type="button">상세</button></td></tr>)}</tbody></table></div>}
        {mayReadStaff && !isAdmin && !loading && !error && visibleTotal > 0 && <nav className="appointment-pagination" aria-label="예약 목록 페이지"><button type="button" aria-label="이전 페이지" disabled={page <= 1 || (usesApiPagination && !hasPreviousPage)} onClick={() => setPage((current) => Math.max(1, current - 1))}>‹</button><span><strong>{page}</strong> / {pageCount}</span><button type="button" aria-label="다음 페이지" disabled={page >= pageCount || (usesApiPagination && !hasNextPage)} onClick={() => setPage((current) => Math.min(pageCount, current + 1))}>›</button></nav>}
      </main>
      <aside className="appointment-detail-card"><header><span>Appointment detail</span><h3>예약 상세</h3></header>{selected ? <><dl><div><dt>예약 ID</dt><dd>{selected.appointment_id}</dd></div><div><dt>환자</dt><dd>{selected.patient?.name ?? selected.patient_id ?? "-"}</dd></div><div><dt>일정</dt><dd>{formatDateTime(appointmentStart(selected))}</dd></div><div><dt>진료과</dt><dd>{selected.department?.name ?? selected.department_id ?? "-"}</dd></div><div><dt>담당의</dt><dd>{selected.clinician?.name ?? selected.clinician_id ?? "-"}</dd></div><div><dt>상태</dt><dd>{selected.status}</dd></div><div><dt>예약 유형</dt><dd>{selected.request_type ?? "-"}</dd></div><div><dt>요청 시각</dt><dd>{formatDateTime(selected.requested_at)}</dd></div>{selected.rejection_reason && <div><dt>거절 사유</dt><dd>{selected.rejection_reason}</dd></div>}{selected.cancel_reason && <div><dt>취소 사유</dt><dd>{selected.cancel_reason}</dd></div>}</dl>{selected.status === "CONFIRMED" && can(currentUser, "appointment.complete") && <div className="appointment-actions"><button type="button" onClick={() => void handleComplete()}>완료 처리</button></div>}</> : <div className="appointment-empty is-detail-empty">예약을 선택하면 상세 정보가 표시됩니다.</div>}{actionError && <p className="appointment-action-error">{actionError}</p>}</aside>
    </div>}

    {activeTab === "requests" && <section className="appointment-list-card">{!isNurse ? <div className="appointment-empty">예약 요청 처리는 간호사 역할에서만 사용할 수 있습니다.</div> : loading ? <div className="appointment-empty">불러오는 중...</div> : error ? <div className="appointment-empty is-error">{error}</div> : requests.length === 0 ? <div className="appointment-empty">승인 대기 예약 요청이 없습니다.</div> : <div className="appointment-request-list">{requests.map((item) => <article key={item.appointment_id}><div><strong>{item.patient?.name ?? item.patient_id ?? "환자 정보 없음"}</strong><span>{formatDateTime(item.requested_at)} · {item.request_type ?? "-"}</span></div><span className="appointment-status is-requested">{item.status}</span><div><button type="button" disabled={!can(currentUser, "appointment.accept")} onClick={() => void processRequest(item.appointment_id, "accept")}>승인</button><button type="button" disabled={!can(currentUser, "appointment.reject")} onClick={() => void processRequest(item.appointment_id, "reject")}>거절</button></div></article>)}</div>}{actionError && <p className="appointment-action-error">{actionError}</p>}</section>}

    {activeTab === "manage" && <section className="appointment-schedule-card"><header><div><span>Schedule management</span><h3>의료진 스케줄 관리</h3></div><div><select value={clinicianId} onChange={(event) => setClinicianId(event.target.value)}><option value="">담당 의료진 선택</option>{clinicianOptions.map(([id, name]) => <option value={id} key={id}>{name}</option>)}</select><button type="button" disabled={!clinicianId} onClick={() => void loadSchedule()}>조회</button></div></header>{!clinicianId ? <div className="appointment-empty">현재 예약 응답에서 확인된 담당 의료진을 선택해 주세요. 로그인 응답에는 clinician_id가 제공되지 않습니다.</div> : <><div className="schedule-rule-editor"><label>요일<select value={draftRule.weekday} onChange={(event) => setDraftRule((rule) => ({ ...rule, weekday: Number(event.target.value) }))}>{WEEKDAYS.map((day, index) => <option key={day} value={index}>{day}</option>)}</select></label><label>시작<input type="time" value={draftRule.start_time} onChange={(event) => setDraftRule((rule) => ({ ...rule, start_time: event.target.value }))} /></label><label>종료<input type="time" value={draftRule.end_time} onChange={(event) => setDraftRule((rule) => ({ ...rule, end_time: event.target.value }))} /></label><label>간격<input type="number" min="1" value={draftRule.slot_minutes} onChange={(event) => setDraftRule((rule) => ({ ...rule, slot_minutes: Number(event.target.value) }))} /></label><label>적용 시작<input type="date" value={draftRule.effective_from} onChange={(event) => setDraftRule((rule) => ({ ...rule, effective_from: event.target.value }))} /></label><button type="button" onClick={() => setSchedule((rules) => [...rules, draftRule])}>규칙 추가</button></div>{schedule.length === 0 ? <div className="appointment-empty is-compact">등록된 스케줄 규칙이 없습니다.</div> : <div className="schedule-rule-list">{schedule.map((rule, index) => <div key={rule.id ?? index}><strong>{WEEKDAYS[rule.weekday] ?? rule.weekday}</strong><span>{rule.start_time}–{rule.end_time}</span><span>{rule.slot_minutes}분</span><span>{rule.effective_from}–{rule.effective_to ?? "계속"}</span><label><input type="checkbox" checked={rule.is_active} onChange={(event) => setSchedule((previous) => previous.map((item, itemIndex) => itemIndex === index ? { ...item, is_active: event.target.checked } : item))} /> 활성</label></div>)}</div>}</>}<footer><button type="button" disabled={!clinicianId || !mayManageSchedule || schedule.length === 0} onClick={() => void saveSchedule()}>스케줄 저장</button></footer>{actionError && <p className="appointment-action-error">{actionError}</p>}</section>}
  </section>;
}
