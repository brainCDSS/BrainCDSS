import { useEffect, useMemo, useRef, useState } from "react";
import type { FormEvent } from "react";

import { getAIAnalyses, getAIAnalysisResult } from "../ai-analysis/api";
import type { AIAnalysisItem, AIAnalysisResult } from "../ai-analysis/types";
import { getClinicians } from "../assessments/api";
import type { Clinician } from "../assessments/types";
import { getActiveHospitals, getHospitalDetail } from "../appointments/api";
import { createConsultation, getConsultations } from "../consultations/api";
import type {
  ConsultationListItem,
  ConsultationPriority,
  ConsultationType,
} from "../consultations/types";
import { getImagingStudies } from "../imaging/api";
import type { ImagingStudy } from "../imaging/types";
import { getPatientEncounters } from "../medication-safety/api";
import type { EncounterListItem } from "../medication-safety/types";
import { loadAuthSession } from "../auth/session";
import { getPatient, getPatients } from "./api";
import type { Patient, PatientDetail } from "./types";
import "./css/patient_chart.css";

type Destination = "imaging" | "ai-results" | "consultations" | "prescriptions";
interface Props { patient: Patient | null; encounterId: string | null; patients?: Patient[]; onSelectPatient?: (patient: Patient) => void; onNavigate?: (destination: Destination) => void; canViewAIAnalyses?: boolean; canViewConsultations?: boolean }
interface ChartData { studies: ImagingStudy[]; analyses: AIAnalysisItem[]; consultations: ConsultationListItem[] }
interface TimelineEvent { id: string; at: string; title: string; detail: string; tone: "imaging" | "ai" | "consultation" }
const PAGE_SIZE = 6;

function sex(value: string | null) { return value === "M" || value === "MALE" ? "남" : value === "F" || value === "FEMALE" ? "여" : value || "-"; }
function age(patient: Patient) { return patient.estimated_age === null ? "-" : `${patient.estimated_age}세`; }
function encounterBadge(encounter?: { status?: string | null; endedAt?: string | null }) {
  if (encounter?.endedAt) return { label: "완료", tone: "completed" };
  if (encounter?.status === "IN_PROGRESS") return { label: "진료중", tone: "in-progress" };
  if (encounter?.status === "REGISTERED") return { label: "진료대기", tone: "registered" };
  return null;
}
function dateTime(value?: string | null) { if (!value) return "-"; const date = new Date(value); return Number.isNaN(date.getTime()) ? value : date.toLocaleString("ko-KR", { month: "2-digit", day: "2-digit", hour: "2-digit", minute: "2-digit" }); }
function analysisName(value: string) { const key = value.toUpperCase(); if (key.includes("ISCHEM")) return "허혈성 뇌졸중"; if (key.includes("HEMORRH")) return "출혈성 뇌졸중"; if (key.includes("ANEURYSM")) return "뇌동맥류"; return value; }
function consultationStatusLabel(value?: string | null) {
  const labels: Record<string, string> = {
    REQUESTED: "요청됨",
    ACCEPTED: "수락됨",
    IN_PROGRESS: "검토 중",
    REJECTED: "거절됨",
    COMPLETED: "회신 완료",
    RESPONDED: "회신 완료",
    CANCELLED: "취소됨",
  };
  return labels[value ?? ""] ?? "-";
}
function consultationPriorityLabel(value?: string | null) {
  const labels: Record<string, string> = { ROUTINE: "일반", URGENT: "응급", STAT: "긴급" };
  return labels[value ?? ""] ?? "-";
}
function consultationTypeLabel(value?: string | null) {
  const labels: Record<string, string> = { RADIOLOGY: "영상의학과", NEUROSURGERY: "신경외과", NEUROLOGY: "신경과" };
  return labels[value ?? ""] ?? "-";
}

export function PatientRail({ selectedId, patients, onSelect }: { selectedId: string | null; patients: Patient[]; onSelect?: (patient: Patient) => void }) {
  const [search, setSearch] = useState(""); const [page, setPage] = useState(1); const [encounterBadges, setEncounterBadges] = useState<Record<string, { label: string; tone: string }>>({});
  const filtered = useMemo(() => { const query = search.trim().toLowerCase(); return query ? patients.filter((item) => item.name.toLowerCase().includes(query) || item.patient_no.toLowerCase().includes(query)) : patients; }, [patients, search]);
  const pages = Math.max(1, Math.ceil(filtered.length / PAGE_SIZE)); const current = Math.min(page, pages); const rows = filtered.slice((current - 1) * PAGE_SIZE, current * PAGE_SIZE);
  useEffect(() => setPage(1), [search]);
  useEffect(() => {
    let active = true;
    if (patients.length === 0) { setEncounterBadges({}); return; }
    void Promise.allSettled(patients.map(async (patient) => ({ patientId: patient.id, encounters: await getPatientEncounters(patient.id) }))).then((results) => {
      if (!active) return;
      const next: Record<string, { label: string; tone: string }> = {};
      results.forEach((result) => {
        if (result.status !== "fulfilled") return;
        const latest = [...result.value.encounters].sort((left, right) => (right.arrived_at ?? "").localeCompare(left.arrived_at ?? ""))[0];
        if (!latest) return;
        if (latest.ended_at) next[result.value.patientId] = { label: "완료", tone: "completed" };
        else if (latest.status === "IN_PROGRESS") next[result.value.patientId] = { label: "진료중", tone: "in-progress" };
        else if (latest.status === "REGISTERED") next[result.value.patientId] = { label: "진료대기", tone: "registered" };
      });
      setEncounterBadges(next);
    });
    return () => { active = false; };
  }, [patients]);
  return <aside className="patient-context-rail"><header className="patient-context-rail__header"><div><span>PATIENT LIST</span><strong>환자 목록</strong></div><small>{patients.length}명</small></header><label className="patient-context-search"><span aria-hidden="true">⌕</span><input type="search" value={search} onChange={(event) => setSearch(event.target.value)} placeholder="이름 또는 등록번호 검색" /></label><div className="patient-context-list">{rows.map((item) => { const demographics = [sex(item.sex), age(item)].filter((value) => value !== "-").join(" · "); const badge = encounterBadges[item.id]; return <button key={item.id} type="button" className={`patient-context-item${item.id === selectedId ? " is-selected" : ""}`} onClick={() => onSelect?.(item)} aria-current={item.id === selectedId ? "true" : undefined}><span className="patient-context-item__avatar" aria-hidden="true">{item.name.slice(0, 1)}</span><span className="patient-context-item__topline"><strong>{item.name}</strong>{badge && <span className={`patient-mini-status is-${badge.tone}`}>{badge.label}</span>}</span>{demographics && <span className="patient-context-item__demographics">{demographics}</span>}<span className="patient-context-item__meta">환자번호 {item.patient_no}</span></button>; })}{rows.length === 0 && <div className="patient-context-empty">검색 결과가 없습니다.</div>}</div><nav className="patient-context-pagination"><button type="button" disabled={current === 1} onClick={() => setPage((value) => Math.max(1, value - 1))}>‹</button><span><strong>{current}</strong> / {pages}</span><button type="button" disabled={current === pages} onClick={() => setPage((value) => Math.min(pages, value + 1))}>›</button></nav></aside>;
}

export function PatientHeader({ patient, care, onOpenDetails }: { patient: Patient; care?: { department?: string | null; clinician?: string | null; latestVisit?: string | null; diagnosis?: string | null; encounterStatus?: string | null; encounterType?: string | null; arrivedAt?: string | null; endedAt?: string | null }; onOpenDetails?: () => void }) {
  const badge = encounterBadge({ status: care?.encounterStatus, endedAt: care?.endedAt });
  return <header className="patient-context-header patient-context-header--compact">
    <div className="patient-context-header__identity">
      <div className="patient-avatar" aria-hidden="true">{patient.name.slice(0, 1)}</div>
      <div className="patient-context-profile">
        <div className="patient-context-title">
          <h1>{patient.name}</h1>
          <strong>({sex(patient.sex)} / {age(patient)})</strong>
          {badge && <span className={`patient-status is-${badge.tone}`}>{badge.label}</span>}
        </div>
        <div className="patient-context-demographics">
          <span>등록번호 <b>{patient.patient_no}</b></span>
          <span>생년월일 <b>{patient.birth_date || "-"}</b></span>
          <span>성별 <b>{sex(patient.sex)}</b></span>
          <span>키 <b>-</b></span>
          <span>체중 <b>-</b></span>
        </div>
      </div>
    </div>
    <div className="patient-context-allergy" aria-label="알레르기 정보">
      <strong>⚠ 알레르기</strong>
      <span>-</span>
    </div>
    <dl className="patient-context-care">
      {care?.encounterStatus || care?.encounterType || care?.arrivedAt ? <>
        <div><dt>내원일시</dt><dd>{dateTime(care.arrivedAt)}</dd></div>
        <div><dt>Encounter 상태</dt><dd>{care.encounterStatus || "-"}</dd></div>
        <div><dt>내원 형태</dt><dd>{care.encounterType || "-"}</dd></div>
        <div><dt>종료일시</dt><dd>{dateTime(care.endedAt)}</dd></div>
      </> : <>
        <div><dt>진료과</dt><dd>{care?.department || "-"}</dd></div>
        <div><dt>담당의</dt><dd>{care?.clinician || "-"}</dd></div>
        <div><dt>최근 내원</dt><dd>{care?.latestVisit || "-"}</dd></div>
        <div><dt>주진단</dt><dd>{care?.diagnosis || "-"}</dd></div>
      </>}
    </dl>
    {onOpenDetails && <button className="patient-context-detail" type="button" onClick={onOpenDetails}>상세 정보 <span aria-hidden="true">⌄</span></button>}
  </header>;
}

function SummaryCards({
  studies,
  consultations,
  onNavigate,
  canRequestConsultation,
  consultationRequestDisabled,
  onRequestConsultation,
}: {
  studies: ImagingStudy[];
  consultations: ConsultationListItem[];
  onNavigate?: (destination: Destination) => void;
  canRequestConsultation: boolean;
  consultationRequestDisabled: boolean;
  onRequestConsultation?: () => void;
}) {
  const latest = studies[0];
  const consultation = consultations[0];

  return (
    <section className="patient-summary-grid">
      <article className="patient-summary-card">
        <header>
          <span>♥</span>
          <h3>Vital Sign</h3>
        </header>

        <div className="summary-empty">
          <strong>Vital API 미연결</strong>
          <span>BP / HR / RR / BT 데이터가 없습니다.</span>
        </div>
      </article>

      <article className="patient-summary-card">
        <header>
          <span>▣</span>
          <h3>최근 영상검사</h3>
          <small>{latest ? dateTime(latest.study_at) : "-"}</small>
        </header>

        {latest ? (
          <div className="patient-recent-study-list">
            {studies.slice(0, 3).map((study) => (
              <div key={study.id}>
                <strong>{study.modality}</strong>
                <span>{study.status}</span>
                <time>{dateTime(study.study_at)}</time>
              </div>
            ))}
          </div>
        ) : (
          <div className="summary-empty">
            <strong>검사 없음</strong>
            <span>연결된 영상검사가 없습니다.</span>
          </div>
        )}

        <button
          type="button"
          onClick={() => onNavigate?.("imaging")}
        >
          검사 상세 보기 ›
        </button>
      </article>

      <article className="patient-summary-card">
        <header>
          <span>♧</span>
          <h3>협진 현황</h3>

          <div className="patient-consultation-actions">
            {canRequestConsultation && (
              <button
                type="button"
                className="patient-consultation-request"
                disabled={consultationRequestDisabled}
                onClick={onRequestConsultation}
              >
                협진 요청
              </button>
            )}

            <button
              type="button"
              onClick={() => onNavigate?.("consultations")}
            >
              더보기 ›
            </button>
          </div>
        </header>

        {consultation ? (
          <dl>
            <div>
              <dt>협진 대상</dt>
              <dd>{consultationTypeLabel(consultation.type)}</dd>
            </div>
            <div>
              <dt>현재 상태</dt>
              <dd>{consultationStatusLabel(consultation.status)}</dd>
            </div>
            <div>
              <dt>우선순위</dt>
              <dd>{consultationPriorityLabel(consultation.priority)}</dd>
            </div>
          </dl>
        ) : (
          <div className="summary-empty">
            <strong>협진 없음</strong>
            <span>조회 가능한 협진이 없습니다.</span>
          </div>
        )}
      </article>
    </section>
  );
}

function Viewer({ studies, selected, onSelect, onOpen }: { studies: ImagingStudy[]; selected: ImagingStudy | null; onSelect: (id: string) => void; onOpen?: () => void }) {
  return <section className="patient-dashboard-card brain-viewer-card"><header className="patient-card-header is-dark"><h2>뇌 영상 Viewer</h2><div className="viewer-series-tabs">{studies.slice(0, 4).map((item) => <button key={item.id} type="button" className={selected?.id === item.id ? "is-active" : ""} onClick={() => onSelect(item.id)}>{item.modality}</button>)}</div></header><div className="brain-viewer-stage">{selected ? <div className="viewer-study-state"><div className="viewer-scan-placeholder"><span /><span /><span /></div><strong>{selected.modality} · {selected.series}</strong><p>실제 영상은 기존 영상 업무 Viewer에서 확인할 수 있습니다.</p><button type="button" onClick={onOpen}>전체화면 보기</button></div> : <div className="viewer-study-state is-empty"><strong>연결된 뇌 영상이 없습니다.</strong></div>}</div></section>;
}

function Analysis({ item, result, loading, error, onOpen }: { item: AIAnalysisItem | null; result: AIAnalysisResult | null; loading: boolean; error: string | null; onOpen?: () => void }) {
  const findings = result ? Object.entries(result.structured_findings).slice(0, 2) : [];
  return <section className="patient-dashboard-card ai-result-card"><header className="patient-card-header"><h2>AI 분석 결과</h2><small>{item ? dateTime(item.requested_at) : "-"}</small></header>{loading ? <div className="panel-empty-state">AI 결과를 불러오는 중입니다.</div> : error ? <div className="panel-empty-state is-error">{error}</div> : !item ? <div className="panel-empty-state"><strong>AI 분석 결과가 없습니다.</strong></div> : !result ? <div className="panel-empty-state"><strong>{analysisName(item.analysis_type)}</strong><span>현재 상태: {item.status}</span></div> : <div className="analysis-result-body"><dl className="analysis-metrics"><div><dt>분석 유형</dt><dd>{analysisName(item.analysis_type)}</dd></div><div><dt>Confidence</dt><dd>{result.confidence == null ? "-" : `${Math.round(result.confidence * 100)}%`}</dd></div><div><dt>병변 개수</dt><dd>{result.lesion_count}</dd></div><div><dt>병변 총 부피</dt><dd>{result.total_volume_ml} mL</dd></div><div><dt>Severity</dt><dd>{result.severity || "-"}</dd></div><div><dt>추정 위치</dt><dd>{String(result.structured_findings.location ?? "-")}</dd></div></dl><div className="analysis-findings"><span>주요 소견</span>{findings.length ? findings.map(([key, value]) => <p key={key}><strong>{key.replaceAll("_", " ")}</strong> {typeof value === "object" ? JSON.stringify(value) : String(value)}</p>) : <p>구조화된 주요 소견이 없습니다.</p>}</div><button className="patient-panel-link" type="button" onClick={onOpen}>상세 결과 보기 ›</button></div>}</section>;
}

function Timeline({ events }: { events: TimelineEvent[] }) { return <section className="patient-dashboard-card timeline-card"><header className="patient-card-header"><h2>진료기록 / 경과</h2><button type="button" disabled title="전체 진료기록 조회 API가 제공되지 않습니다.">전체보기</button></header>{events.length ? <ol className="clinical-timeline">{events.map((event) => <li key={event.id} className={`is-${event.tone}`}><time>{dateTime(event.at)}</time><div><strong>{event.title}</strong><p>{event.detail}</p></div></li>)}</ol> : <div className="panel-empty-state"><strong>표시할 진료 경과가 없습니다.</strong><span>영상·AI·협진 이벤트가 시간순으로 표시됩니다.</span></div>}</section>; }
function Prescriptions({ onOpen }: { onOpen?: () => void }) { return <section className="patient-dashboard-card recent-prescriptions-card"><header className="patient-card-header"><h2>최근 처방</h2></header><div className="panel-empty-state"><strong>최근 처방 내역이 없습니다.</strong><span>의료진용 환자별 처방 목록 API가 제공되지 않습니다.</span></div><button className="patient-panel-link recent-prescriptions-card__open" type="button" onClick={onOpen}>처방 / DUR 열기</button></section>; }

export default function PatientChart({ patient, encounterId, patients = [], onSelectPatient, onNavigate, canViewAIAnalyses = false, canViewConsultations = false }: Props) {
  const [activeTab, setActiveTab] = useState<"summary" | "clinical">("summary");
  const [patientList, setPatientList] = useState<Patient[]>(patients); const [data, setData] = useState<ChartData>({ studies: [], analyses: [], consultations: [] });
  const [isPermissionModalOpen, setIsPermissionModalOpen] = useState(false);
  const [patientDetail, setPatientDetail] = useState<PatientDetail | null>(null); const [loading, setLoading] = useState(false); const [error, setError] = useState<string | null>(null); const [selectedStudyId, setSelectedStudyId] = useState<string | null>(null); const [analysisResults, setAnalysisResults] = useState<Record<string, AIAnalysisResult>>({}); const [analysisLoading, setAnalysisLoading] = useState(false); const [analysisError, setAnalysisError] = useState<string | null>(null); const clinicalRequestId = useRef(0); const analysisRequestId = useRef(0);
  const [encounter, setEncounter] = useState<EncounterListItem | null>(null); const [encounterLoading, setEncounterLoading] = useState(false); const [encounterError, setEncounterError] = useState<string | null>(null); const encounterRequestId = useRef(0);
  const automaticPatientId = useRef<string | null>(null);
  const currentUser = loadAuthSession()?.user;
  const currentRole = currentUser?.role.code;
  const isNurse = currentRole === "NURSE";
  const canRequestConsultation = currentRole === "NEUROLOGIST";

  const [isConsultationRequestOpen, setIsConsultationRequestOpen] = useState(false);
  const [consultationType, setConsultationType] = useState<ConsultationType>("RADIOLOGY");
  const [selectedClinicianId, setSelectedClinicianId] = useState("");
  const [consultationClinicians, setConsultationClinicians] = useState<Clinician[]>([]);
  const [consultationCliniciansLoading, setConsultationCliniciansLoading] = useState(false);
  const [consultationCliniciansError, setConsultationCliniciansError] = useState<string | null>(null);
  const [consultationPriority, setConsultationPriority] = useState<ConsultationPriority>("ROUTINE");
  const [consultationReason, setConsultationReason] = useState("");
  const [consultationSubmitting, setConsultationSubmitting] = useState(false);
  const [consultationRequestError, setConsultationRequestError] = useState<string | null>(null);

  const consultationRequestDisabled =
    encounterLoading ||
    !encounterId ||
    !encounter ||
    (encounter.status !== "REGISTERED" && encounter.status !== "IN_PROGRESS");

  useEffect(() => {
    let active = true;
    void getPatients().then((response) => {
      if (active) setPatientList(response.results);
    }).catch(() => {
      if (active) setError("환자 목록을 불러오지 못했습니다.");
    });
    return () => { active = false; };
  }, []);

  useEffect(() => {
    const requestId = ++clinicalRequestId.current;
    setPatientDetail(null); setData({ studies: [], analyses: [], consultations: [] }); setSelectedStudyId(null); setAnalysisResults({}); setAnalysisError(null); setError(null);
    if (!patient) { setLoading(false); return; }
    setLoading(true);
    const analysesRequest = canViewAIAnalyses ? getAIAnalyses() : Promise.resolve({ count: 0, results: [] as AIAnalysisItem[] });
    const consultationsRequest = canViewConsultations ? getConsultations() : Promise.resolve({ count: 0, results: [] as ConsultationListItem[] });
    void Promise.allSettled([getPatient(patient.id), getImagingStudies({ patientId: patient.id }), analysesRequest, consultationsRequest]).then(([detail, imaging, analyses, consultations]) => {
      if (clinicalRequestId.current !== requestId) return;
      if (detail.status === "fulfilled") setPatientDetail(detail.value);
      setData({ studies: imaging.status === "fulfilled" ? imaging.value : [], analyses: analyses.status === "fulfilled" ? analyses.value.results : [], consultations: consultations.status === "fulfilled" ? consultations.value.results : [] });
      if ([detail, imaging, analyses, consultations].some((request) => request.status === "rejected")) setError("일부 환자 임상 데이터를 불러오지 못했습니다.");
      setLoading(false);
    });
    return () => { if (clinicalRequestId.current === requestId) clinicalRequestId.current += 1; };
  }, [patient?.id, canViewAIAnalyses, canViewConsultations]);

  useEffect(() => {
    const requestId = ++encounterRequestId.current;
    setEncounter(null); setEncounterError(null);
    if (!patient || !encounterId) { setEncounterLoading(false); return; }
    setEncounterLoading(true);
    void getPatientEncounters(patient.id).then((items) => {
      if (encounterRequestId.current !== requestId) return;
      const matched = items.find((item) => (item.encounter_id ?? item.id) === encounterId) ?? null;
      setEncounter(matched);
      if (!matched) setEncounterError("연결된 Encounter 정보를 조회할 수 없습니다.");
    }).catch(() => {
      if (encounterRequestId.current === requestId) setEncounterError("Encounter 정보를 불러오지 못했습니다.");
    }).finally(() => {
      if (encounterRequestId.current === requestId) setEncounterLoading(false);
    });
    return () => { if (encounterRequestId.current === requestId) encounterRequestId.current += 1; };
  }, [encounterId, patient?.id]);

  useEffect(() => {
    if (patient) {
      automaticPatientId.current = null;
      return;
    }

    const firstPatient = patientList[0];
    if (!firstPatient || !onSelectPatient || automaticPatientId.current === firstPatient.id) return;

    automaticPatientId.current = firstPatient.id;
    onSelectPatient(firstPatient);
  }, [onSelectPatient, patient, patientList]);

  const displayPatient = patientDetail?.id === patient?.id ? patientDetail : patient;
  const studies = useMemo(() => patient ? data.studies.filter((item) => item.patient_id === patient.id).sort((a, b) => (b.study_at ?? "").localeCompare(a.study_at ?? "")) : [], [data.studies, patient]);
  const studyIds = useMemo(() => new Set(studies.map((item) => item.id)), [studies]); const analyses = useMemo(() => data.analyses.filter((item) => studyIds.has(item.study_id)).sort((a, b) => b.requested_at.localeCompare(a.requested_at)), [data.analyses, studyIds]); const consultations = useMemo(() => patient ? data.consultations.filter((item) => item.patient_summary?.id === patient.id).sort((a, b) => b.requested_at.localeCompare(a.requested_at)) : [], [data.consultations, patient]);
  const selectedStudy = studies.find((item) => item.id === selectedStudyId) ?? studies[0] ?? null; const selectedAnalysis = analyses[0] ?? null; const selectedAnalysisResult = selectedAnalysis ? analysisResults[selectedAnalysis.analysis_id] ?? null : null;
  useEffect(() => { const id = ++analysisRequestId.current; if (!selectedAnalysis || selectedAnalysis.status !== "COMPLETED" || analysisResults[selectedAnalysis.analysis_id]) { setAnalysisLoading(false); return; } setAnalysisLoading(true); setAnalysisError(null); getAIAnalysisResult(selectedAnalysis.analysis_id).then((value) => { if (analysisRequestId.current === id) setAnalysisResults((current) => ({ ...current, [value.analysis_id]: value })); }).catch(() => { if (analysisRequestId.current === id) setAnalysisError("AI 상세 결과를 불러오지 못했습니다."); }).finally(() => { if (analysisRequestId.current === id) setAnalysisLoading(false); }); }, [selectedAnalysis?.analysis_id, selectedAnalysis?.status, analysisResults]);
  const events = useMemo<TimelineEvent[]>(() => [...studies.map((item) => ({ id: `study-${item.id}`, at: item.study_at ?? "", title: `${item.modality} 영상검사`, detail: `${item.series} · ${item.status}`, tone: "imaging" as const })), ...analyses.map((item) => ({ id: `ai-${item.analysis_id}`, at: item.requested_at, title: `${analysisName(item.analysis_type)} AI 분석`, detail: `${item.status} · ${item.stage}`, tone: "ai" as const })), ...consultations.map((item) => ({ id: `consult-${item.consultation_id}`, at: item.requested_at, title: `${consultationTypeLabel(item.type)} 협진 요청`, detail: `${consultationStatusLabel(item.status)} · ${consultationPriorityLabel(item.priority)}`, tone: "consultation" as const }))].sort((a, b) => b.at.localeCompare(a.at)), [studies, analyses, consultations]);

  function resetConsultationRequestForm() {
    setConsultationType("RADIOLOGY");
    setSelectedClinicianId("");
    setConsultationPriority("ROUTINE");
    setConsultationReason("");
    setConsultationRequestError(null);
  }

  function closeConsultationRequest() {
    if (consultationSubmitting) return;
    setIsConsultationRequestOpen(false);
    resetConsultationRequestForm();
  }

  useEffect(() => {
    if (!isConsultationRequestOpen) return;

    let active = true;
    setSelectedClinicianId("");
    setConsultationClinicians([]);
    setConsultationCliniciansLoading(true);
    setConsultationCliniciansError(null);

    async function loadConsultationClinicians() {
      try {
        const hospitalIds = currentUser?.hospital?.id
          ? [currentUser.hospital.id]
          : (await getActiveHospitals()).results.map((hospital) => hospital.id);
        const hospitals = await Promise.all(hospitalIds.map(getHospitalDetail));
        const department = hospitals
          .flatMap((hospital) => hospital.departments)
          .find(
            (item) => item.code.trim().toUpperCase() === consultationType,
          );

        if (!department) return;

        const response = await getClinicians(department.id);

        if (active) {
          setConsultationClinicians(
            response.clinicians.filter((clinician) => clinician.is_active),
          );
        }
      } catch {
        if (active) {
          setConsultationCliniciansError(
            "의료진 목록을 불러오지 못했습니다.",
          );
        }
      } finally {
        if (active) setConsultationCliniciansLoading(false);
      }
    }

    void loadConsultationClinicians();
    return () => {
      active = false;
    };
  }, [consultationType, currentUser?.hospital?.id, isConsultationRequestOpen]);

  async function handleConsultationRequest(
    event: FormEvent<HTMLFormElement>,
  ) {
    event.preventDefault();

    if (!patient || !encounterId || !encounter) {
      setConsultationRequestError("현재 활성 Encounter가 없습니다.");
      return;
    }

    if (!selectedClinicianId) {
      setConsultationRequestError("협진 의료진을 선택해 주세요.");
      return;
    }

    const reason = consultationReason.trim();
    if (!reason) {
      setConsultationRequestError("요청 사유를 입력해 주세요.");
      return;
    }

    try {
      setConsultationSubmitting(true);
      setConsultationRequestError(null);

      await createConsultation({
        encounter_id: encounterId,
        consultation_type: consultationType,
        assigned_to_id: selectedClinicianId,
        priority: consultationPriority,
        reason,
      });

      const refreshed = await getConsultations();

      setData((current) => ({
        ...current,
        consultations: refreshed.results,
      }));

      setIsConsultationRequestOpen(false);
      resetConsultationRequestForm();
    } catch (error) {
      const isActiveDuplicate =
        error instanceof Error &&
        error.message.includes("CONSULTATION_ACTIVE_DUPLICATE");
      setConsultationRequestError(
        isActiveDuplicate
          ? "이미 동일 의료진에게 진행 중인 협진이 있습니다."
          : "협진 요청을 보내지 못했습니다.",
      );
    } finally {
      setConsultationSubmitting(false);
    }
  }

  function selectPatient(nextPatient: Patient) { setSelectedStudyId(null); setError(null); setActiveTab("summary"); onSelectPatient?.(nextPatient); }
  return <section className="patient-context-dashboard">
    <div className="patient-workspace">
      <PatientRail selectedId={patient?.id ?? null} patients={patientList.length ? patientList : patients} onSelect={selectPatient} />
      {displayPatient && <PatientHeader patient={displayPatient} care={encounter ? { arrivedAt: encounter.arrived_at, endedAt: encounter.ended_at, encounterStatus: encounter.status, encounterType: encounter.encounter_type } : undefined} />}
      {patient ? <main className={`patient-context-main${activeTab === "clinical" ? " is-clinical" : ""}`}>
        <nav className="patient-chart-tabs" aria-label="환자 정보 탭"><button type="button" className={activeTab === "summary" ? "is-active" : ""} onClick={() => setActiveTab("summary")}>요약</button><button type="button" className={activeTab === "clinical" ? "is-active" : ""} onClick={() => setActiveTab("clinical")}>진료정보</button></nav>
        {activeTab === "clinical" && <section className="patient-clinical-info"><h2>진료정보</h2><dl><div><dt>내원일시</dt><dd>{encounter?.arrived_at ?? "-"}</dd></div><div><dt>Encounter 상태</dt><dd>{encounter?.status ?? "-"}</dd></div></dl></section>}
        {encounterLoading ? <div className="patient-encounter-state">Encounter 정보를 불러오는 중입니다.</div> : !encounterId ? <div className="patient-encounter-state is-empty">현재 활성 Encounter가 없습니다.</div> : encounterError ? <div className="patient-encounter-state is-empty">{encounterError}</div> : null}
        {error && <div className="patient-data-warning">{error}</div>}
        <SummaryCards
          studies={studies}
          consultations={consultations}
          onNavigate={onNavigate}
          canRequestConsultation={canRequestConsultation}
          consultationRequestDisabled={consultationRequestDisabled}
          onRequestConsultation={() => {
            setConsultationRequestError(null);
            setIsConsultationRequestOpen(true);
          }}
        />
        <div className="patient-clinical-focus">{loading ? <div className="patient-chart-loading">환자 임상 데이터를 불러오는 중입니다.</div> : <><Viewer studies={studies} selected={selectedStudy} onSelect={setSelectedStudyId} onOpen={() => onNavigate?.("imaging")} /><Analysis item={selectedAnalysis} result={selectedAnalysisResult} loading={analysisLoading} error={analysisError} onOpen={() => onNavigate?.("ai-results")} /></>}</div>
      </main> : <main className="patient-context-main patient-context-main--empty"><div className="patient-selection-empty"><strong>선택된 환자가 없습니다.</strong><span>왼쪽 환자 목록에서 환자를 선택해 주세요.</span></div></main>}
    </div>
    <aside className="patient-context-aside"><Prescriptions onOpen={() => isNurse ? setIsPermissionModalOpen(true) : onNavigate?.("prescriptions")} /><Timeline events={patient ? events : []} /></aside>
    {isConsultationRequestOpen && (
      <div className="consultation-request-backdrop" role="presentation">
        <section
          className="consultation-request-modal"
          role="dialog"
          aria-modal="true"
          aria-labelledby="consultation-request-title"
        >
          <header className="consultation-request-modal__header">
            <h2 id="consultation-request-title">협진 요청</h2>
            <button
              type="button"
              aria-label="닫기"
              disabled={consultationSubmitting}
              onClick={closeConsultationRequest}
            >
              ×
            </button>
          </header>

          <form
            className="consultation-request-form"
            onSubmit={handleConsultationRequest}
          >
            <div className="consultation-request-form__row">
              <label>
                <span>협진 대상 *</span>
                <select
                  value={consultationType}
                  disabled={consultationSubmitting}
                  onChange={(event) => {
                    setConsultationType(
                      event.target.value as ConsultationType,
                    );
                    setSelectedClinicianId("");
                  }}
                >
                  <option value="RADIOLOGY">영상의학과</option>
                  <option value="NEUROSURGERY">신경외과</option>
                </select>
              </label>

              <label>
                <span>협진 의료진 *</span>
                <select
                  value={selectedClinicianId}
                  disabled={consultationSubmitting || consultationCliniciansLoading}
                  onChange={(event) =>
                    setSelectedClinicianId(event.target.value)
                  }
                >
                  <option value="">
                    {consultationCliniciansLoading
                      ? "의료진을 불러오는 중..."
                      : "의료진을 선택하세요"}
                  </option>
                  {!consultationCliniciansLoading && consultationClinicians.map(
                    (clinician) => (
                      <option key={clinician.id} value={clinician.user_id}>
                        {clinician.name}
                      </option>
                    ),
                  )}
                  {!consultationCliniciansLoading &&
                    !consultationCliniciansError &&
                    consultationClinicians.length === 0 && (
                      <option value="" disabled>
                        선택 가능한 의료진이 없습니다.
                      </option>
                    )}
                </select>
              </label>
            </div>

            {consultationCliniciansError && (
              <p className="consultation-request-error">
                {consultationCliniciansError}
              </p>
            )}

            <label>
              <span>우선순위 *</span>
              <select
                value={consultationPriority}
                disabled={consultationSubmitting}
                onChange={(event) =>
                  setConsultationPriority(
                    event.target.value as ConsultationPriority,
                  )
                }
              >
                <option value="ROUTINE">일반</option>
                <option value="URGENT">응급</option>
                <option value="STAT">긴급</option>
              </select>
            </label>

            <label>
              <span>요청 사유 *</span>
              <textarea
                value={consultationReason}
                disabled={consultationSubmitting}
                placeholder="협진이 필요한 사유를 입력하세요."
                onChange={(event) => setConsultationReason(event.target.value)}
              />
            </label>

            {consultationRequestError && (
              <p className="consultation-request-error">
                {consultationRequestError}
              </p>
            )}

            <footer className="consultation-request-form__actions">
              <button
                type="button"
                disabled={consultationSubmitting}
                onClick={closeConsultationRequest}
              >
                취소
              </button>

              <button
                type="submit"
                className="is-primary"
                disabled={
                  consultationSubmitting ||
                  consultationRequestDisabled ||
                  !selectedClinicianId
                }
              >
                {consultationSubmitting ? "요청 중" : "협진 요청"}
              </button>
            </footer>
          </form>
        </section>
      </div>
    )}
    {isPermissionModalOpen && <div className="permission-modal-backdrop" role="presentation"><section className="permission-modal" role="dialog" aria-modal="true" aria-labelledby="permission-modal-title"><div className="permission-modal__image" aria-hidden="true" /><h2 id="permission-modal-title">처방 / DUR 접근권한이 없습니다</h2><p>관리자에게 문의하세요</p><button type="button" onClick={() => setIsPermissionModalOpen(false)}>확인</button></section></div>}
  </section>;
}
