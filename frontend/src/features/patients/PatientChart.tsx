import { lazy, Suspense, useEffect, useMemo, useRef, useState } from "react";
import type { FormEvent } from "react";
import { getApiRequestStatus } from "../../api/client";

import { getAIAnalyses, getAIAnalysisResult } from "../ai-analysis/api";
import type { AIAnalysisItem, AIAnalysisResult } from "../ai-analysis/types";
import {
  createTriageReview,
  getAssessmentsByEncounter,
  getClinicians,
  getTriageReviews,
} from "../assessments/api";
import type {
  AssessmentDetailResponse,
  Clinician,
  TriagePriority,
  TriageReviewListResponse,
} from "../assessments/types";
import {
  latestCompletedAssessment,
  parseInitialAssessment,
} from "../assessments/viewModel";
import type {
  InitialAssessmentLike,
} from "../assessments/viewModel";
import { getActiveHospitals, getHospitalDetail } from "../appointments/api";
import { createConsultation, getConsultations } from "../consultations/api";
import type {
  ConsultationListItem,
  ConsultationDraft,
  ConsultationPriority,
  ConsultationType,
} from "../consultations/types";
import { getImagingStudies } from "../imaging/api";
import type { ImagingStudy } from "../imaging/types";
import ClinicalNotesReadOnly from "../clinical-notes/ClinicalNotesReadOnly";
import { getCurrentMedications, getPatientEncounters } from "../medication-safety/api";
import type { CurrentMedicationItem, EncounterListItem } from "../medication-safety/types";
import { loadAuthSession } from "../auth/session";
import { getPatient, getPatientTimeline, getPatients } from "./api";
import type { PatientTimelineEvent } from "./api";
import type { Patient, PatientDetail } from "./types";
import "./css/patient_chart.css";

const NiftiViewer = lazy(() => import("../ai-analysis/NiftiViewer"));

type Destination = "imaging" | "ai-results" | "consultations" | "prescriptions";
interface Props { patient: Patient | null; encounterId: string | null; patients?: Patient[]; onSelectPatient?: (patient: Patient) => void; onNavigate?: (destination: Destination) => void; canViewAIAnalyses?: boolean; canViewConsultations?: boolean; consultationDraft?: ConsultationDraft | null; onConsultationDraftConsumed?: () => void }
interface ChartData { studies: ImagingStudy[]; analyses: AIAnalysisItem[]; consultations: ConsultationListItem[] }
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

function isAbnormalClinicalValue(
  value?: string | null,
) {
  const normalized =
    value?.trim().toUpperCase() ?? "";

  if (!normalized) {
    return false;
  }

  if (normalized === "ABNORMAL") {
    return true;
  }

  const abnormalTerms = [
    "있음",
    "불안정",
    "장애",
    "마비",
    "저하",
    "실어증",
    "기면",
    "어지럼",
  ];

  return abnormalTerms.some(
    (term) => normalized.includes(term),
  );
}

function triagePriorityLabel(value?: string | null) {
  const labels: Record<string, string> = {
    EMERGENCY: "응급",
    URGENT: "긴급",
    NON_EMERGENCY: "비응급",
  };
  return labels[value ?? ""] ?? "-";
}

function lkwElapsedLabel(value: string | null, now: number) {
  if (!value) return "-";

  const timestamp = new Date(value).getTime();
  if (Number.isNaN(timestamp) || timestamp > now) return "-";

  const totalMinutes = Math.floor((now - timestamp) / 60_000);

  if (totalMinutes < 60) {
    return `${totalMinutes}분 전`;
  }

  const hours = Math.floor(totalMinutes / 60);
  const minutes = totalMinutes % 60;

  if (hours < 24) {
    return minutes > 0
      ? `${hours}시간 ${minutes}분 전`
      : `${hours}시간 전`;
  }

  const days = Math.floor(hours / 24);
  const remainHours = hours % 24;

  return remainHours > 0
    ? `${days}일 ${remainHours}시간 전`
    : `${days}일 전`;
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

export function PatientHeader({
  patient,
  care,
  assessment,
  onOpenDetails,
}: {
  patient: Patient;
  care?: {
    department?: string | null;
    clinician?: string | null;
    latestVisit?: string | null;
    diagnosis?: string | null;
    encounterStatus?: string | null;
    encounterType?: string | null;
    arrivedAt?: string | null;
    endedAt?: string | null;
  };
  assessment?: InitialAssessmentLike | null;
  onOpenDetails?: () => void;
}) {
  const badge = encounterBadge({
    status: care?.encounterStatus,
    endedAt: care?.endedAt,
  });

  const parsedAssessment =
    assessment
      ? parseInitialAssessment(assessment)
      : null;

  const allergyInfo =
    "allergy_info" in patient &&
    typeof patient.allergy_info === "string"
      ? patient.allergy_info.trim()
      : "";
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
          <span>
            키 <b>{parsedAssessment?.heightCm ?? "-"}</b>
          </span>
          <span>
            체중 <b>{parsedAssessment?.weightKg ?? "-"}</b>
          </span>
        </div>
      </div>
    </div>
    <div
      className="patient-context-allergy"
      aria-label="알레르기 정보"
    >
      <strong>⚠ 알레르기</strong>
      <span>
        {allergyInfo || "미기록"}
      </span>
    </div>
    <dl className="patient-context-care">
      {care?.encounterStatus || care?.encounterType || care?.arrivedAt ? <>
        <div><dt>내원일시</dt><dd>{dateTime(care.arrivedAt)}</dd></div>
        <div><dt>진료 상태</dt><dd>{badge?.label ?? "-"}</dd></div>
        <div><dt>내원 형태</dt><dd>{{ STAT: "긴급", EMERGENCY: "응급", ROUTINE: "일반" }[care.encounterType ?? ""] ?? care.encounterType ?? "-"}</dd></div>
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

function TriageSummaryBar({
  assessment,
  reviewData,
  loading,
  error,
  canReview,
  onReview,
}: {
  assessment: InitialAssessmentLike | null;
  reviewData: TriageReviewListResponse | null;
  loading: boolean;
  error: boolean;
  canReview: boolean;
  onReview: () => void;
}) {
  const [now, setNow] = useState(() => Date.now());

  useEffect(() => {
    const updateNow = () => setNow(Date.now());
    const timer = window.setInterval(updateNow, 60_000);
    const handleVisibilityChange = () => {
      if (document.visibilityState === "visible") {
        updateNow();
      }
    };

    window.addEventListener("focus", updateNow);
    document.addEventListener("visibilitychange", handleVisibilityChange);

    return () => {
      window.clearInterval(timer);
      window.removeEventListener("focus", updateNow);
      document.removeEventListener("visibilitychange", handleVisibilityChange);
    };
  }, []);

  const parsed = assessment
    ? parseInitialAssessment(assessment)
    : null;

  const fastValues = [
    parsed?.fastFace,
    parsed?.fastArm,
    parsed?.fastSpeech,
  ];

  const fastCompleted = fastValues.filter(Boolean).length;
  const fastAbnormal = fastValues.filter(
    (value) => isAbnormalClinicalValue(value),
  ).length;

  const fastStatus =
    fastCompleted === 3
      ? fastAbnormal > 0
        ? "POSITIVE"
        : "NEGATIVE"
      : "-";

  const findings = [
    isAbnormalClinicalValue(parsed?.fastFace)
      ? "안면 비대칭"
      : null,
    isAbnormalClinicalValue(parsed?.fastArm)
      ? "상지 위약"
      : null,
    isAbnormalClinicalValue(parsed?.fastSpeech)
      ? "언어 이상"
      : null,
  ].filter((item): item is string => Boolean(item));

  const lkwElapsed = lkwElapsedLabel(parsed?.lkwAt ?? null, now);
  const lkwClock = parsed?.lkwAt
    ? new Date(parsed.lkwAt).toLocaleTimeString("ko-KR", {
        hour: "2-digit",
        minute: "2-digit",
      })
    : "-";

  const effectivePriority =
    reviewData?.effective_priority ??
    parsed?.triagePriority ??
    null;
  const latestReview =
    reviewData?.latest_review ??
    null;

  return (
    <section className="patient-triage-strip" aria-label="BrainCDSS 초기평가 요약">
      <div className="patient-triage-strip__brand">
        <span className="patient-triage-strip__icon" aria-hidden="true">✚</span>
        <div>
          <strong>BrainCDSS Triage</strong>
          <small>초기평가 요약</small>
        </div>
      </div>

      {loading ? (
        <div className="patient-triage-strip__state">초기평가 정보를 불러오는 중입니다.</div>
      ) : error ? (
        <div className="patient-triage-strip__state is-error">초기평가 정보를 불러오지 못했습니다.</div>
      ) : !assessment || !parsed ? (
        <div className="patient-triage-strip__state">완료된 초기평가가 없습니다.</div>
      ) : (
        <>
          <div className="patient-triage-metric">
            <span>FAST</span>
            <strong className={fastStatus === "POSITIVE" ? "is-alert" : ""}>
              {fastStatus}
            </strong>
          </div>

          <div className="patient-triage-metric">
            <span>선별점수</span>
            <strong>
              {parsed.totalScore ?? "-"}
              <small> / 30</small>
            </strong>
          </div>

          <div className="patient-triage-metric">
            <span>LKW</span>
            <strong>{lkwElapsed}</strong>
            <small>{lkwClock}</small>
          </div>

          <div className="patient-triage-findings">
            <span>주요 소견</span>
            {findings.length ? (
              <div>
                {findings.slice(0, 2).map((item) => (
                  <small key={item}>• {item}</small>
                ))}
                {findings.length > 2 && (
                  <b>+{findings.length - 2}</b>
                )}
              </div>
            ) : (
              <small>FAST 이상 소견 없음</small>
            )}
          </div>

          <div className="patient-triage-priority">
            <span>
              {latestReview ? "현재 우선순위" : "초기평가 우선순위"}
            </span>
            <div className="patient-triage-priority__line">
              <strong className={`is-${(effectivePriority ?? "unknown").toLowerCase()}`}>
                {triagePriorityLabel(effectivePriority)}
              </strong>
              {canReview && (
                <button type="button" onClick={onReview}>
                  재평가
                </button>
              )}
            </div>
            <small>
              {latestReview
                ? `초기 ${triagePriorityLabel(parsed.triagePriority)} · ${latestReview.reviewer.name} 재평가`
                : parsed.triagePriority ?? "-"}
            </small>
          </div>
        </>
      )}
    </section>
  );
}

function SummaryCards({
  studies,
  consultations,
  onNavigate,
  canRequestConsultation,
  consultationRequestDisabled,
  onRequestConsultation,
  latestAssessment,
  vitalLoading,
  vitalError,
}: {
  studies: ImagingStudy[];
  consultations: ConsultationListItem[];
  onNavigate?: (destination: Destination) => void;
  canRequestConsultation: boolean;
  consultationRequestDisabled: boolean;
  onRequestConsultation?: () => void;
  latestAssessment: InitialAssessmentLike | null;
  vitalLoading: boolean;
  vitalError: boolean;
}) {
  const latest = studies[0];
  const consultation = consultations[0];
  const parsedAssessment =
    latestAssessment
      ? parseInitialAssessment(latestAssessment)
      : null;
  const bloodPressure =
    parsedAssessment?.bpSys || parsedAssessment?.bpDia
      ? [
          parsedAssessment?.bpSys,
          parsedAssessment?.bpDia,
        ].filter(Boolean).join(" / ")
      : null;
  const heartRate = parsedAssessment?.heartRate ?? null;
  const respRate = parsedAssessment?.respRate ?? null;
  const bodyTemp =
    parsedAssessment?.bodyTemp ?? null;
  const spo2 =
    parsedAssessment?.spo2 ?? null;

  const hasVital =
    bloodPressure !== null ||
    heartRate !== null ||
    respRate !== null ||
    bodyTemp !== null ||
    spo2 !== null ||
    false;

  return (
    <section className="patient-summary-grid">
      <article className="patient-summary-card">
        <header>
          <span>♥</span>
          <h3>Vital Sign</h3>
        </header>

        {vitalLoading ? (
          <div className="summary-empty">
            <strong>Vital 정보를 불러오는 중입니다.</strong>
          </div>
        ) : vitalError ? (
          <div className="summary-empty">
            <strong>Vital 정보를 불러오지 못했습니다.</strong>
          </div>
        ) : !hasVital ? (
          <div className="summary-empty">
            <strong>Vital 기록 없음</strong>
            <span>
              선택된 Encounter의 완료된 초기평가에
              기록된 Vital 정보가 없습니다.
            </span>
          </div>
        ) : (
          <dl>
            <div>
              <dt>BP</dt>
              <dd>{bloodPressure ?? "-"}</dd>
            </div>
            <div>
              <dt>HR</dt>
              <dd>{heartRate ?? "-"}</dd>
            </div>
            <div>
              <dt>RR</dt>
              <dd>{respRate ?? "-"}</dd>
            </div>
            <div>
              <dt>BT</dt>
              <dd>{bodyTemp ?? "-"}</dd>
            </div>
            <div>
              <dt>SpO₂</dt>
              <dd>{spo2 ?? "-"}</dd>
            </div>
            
            
          </dl>
        )}
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

function Viewer({ studies, selected, completedAnalysis, onSelect, onOpen }: { studies: ImagingStudy[]; selected: ImagingStudy | null; completedAnalysis: AIAnalysisItem | null; onSelect: (id: string) => void; onOpen?: () => void }) {
  return <section className="patient-dashboard-card brain-viewer-card"><header className="patient-card-header is-dark"><h2>뇌 영상 Viewer</h2><div className="viewer-series-tabs">{studies.slice(0, 4).map((item) => <button key={item.id} type="button" className={selected?.id === item.id ? "is-active" : ""} onClick={() => onSelect(item.id)}>{item.modality}</button>)}</div></header><div className="brain-viewer-stage">{selected ? <Suspense fallback={<div className="viewer-study-state">영상을 준비하는 중입니다.</div>}><NiftiViewer key={completedAnalysis?.analysis_id ?? selected.id} analysisId={completedAnalysis?.analysis_id} studyId={completedAnalysis ? undefined : selected.id} maskOnly /></Suspense> : <div className="viewer-study-state is-empty"><strong>연결된 뇌 영상이 없습니다.</strong></div>}</div><button className="patient-viewer-open" type="button" onClick={onOpen}>영상 업무 Viewer 열기</button></section>;
}

function reviewLabel(decision?: string | null) { return ({ ACCEPT: "의료진 확인", MODIFY: "의료진 보정", REJECT: "의료진 제외" } as Record<string, string>)[decision ?? ""] ?? "검토 전"; }

function Analysis({ item, result, study, loading, error, onOpen }: { item: AIAnalysisItem | null; result: AIAnalysisResult | null; study: ImagingStudy | null; loading: boolean; error: string | null; onOpen?: () => void }) {
  const positive = result?.is_positive ?? ((result?.lesion_count ?? 0) > 0 ? true : null);
  const headline = positive === true ? "이상 소견 의심" : positive === false ? "유의한 병변 미검출" : "분석 결과 확인 필요";
  return <section className="patient-dashboard-card ai-result-card"><header className="patient-card-header"><h2>AI 분석 결과</h2><small>{item ? dateTime(item.requested_at) : "-"}</small></header>{loading ? <div className="panel-empty-state">AI 결과를 불러오는 중입니다.</div> : error ? <div className="panel-empty-state is-error">{error}</div> : !item ? <div className="panel-empty-state"><strong>AI 분석 결과가 없습니다.</strong></div> : !result ? <div className="panel-empty-state"><strong>{analysisName(item.analysis_type)}</strong><span>현재 상태: {item.status}</span></div> : <div className="analysis-result-body"><div className={`analysis-clinical-headline${positive === true ? " is-positive" : ""}`}><span>{positive === true ? "●" : "○"}</span><div><strong>{headline}</strong><small>{analysisName(item.analysis_type)} · 분석 완료</small></div></div><dl className="analysis-context"><div><dt>분석 대상</dt><dd>{study ? `${study.modality} · ${study.series}` : "연결 영상"}</dd></div><div><dt>의료진 검토</dt><dd>{reviewLabel(result.latest_review?.decision)}</dd></div></dl><div className="analysis-summary-heading">병변 요약</div><dl className="analysis-metrics"><div><dt>병변 개수</dt><dd>{result.lesion_count ?? "-"}</dd></div><div><dt>총 부피</dt><dd>{result.total_volume_ml == null ? "-" : `${result.total_volume_ml} mL`}</dd></div></dl><p className="analysis-clinical-note">마스크가 왼쪽 영상에 표시되어 있습니다. AI 결과는 진단 보조 정보이므로 원본 영상과 임상 소견을 함께 검토하세요.</p><button className="patient-panel-link" type="button" onClick={onOpen}>상세 분석 보기 ›</button></div>}</section>;
}

function Timeline({ events, loading, error }: { events: PatientTimelineEvent[]; loading: boolean; error: boolean }) { return <section className="patient-dashboard-card timeline-card"><header className="patient-card-header"><h2>진료기록 / 경과</h2></header>{loading ? <div className="panel-empty-state"><strong>진료 경과를 불러오는 중입니다.</strong></div> : error ? <div className="panel-empty-state is-error"><strong>진료 경과를 불러오지 못했습니다.</strong></div> : events.length ? <ol className="clinical-timeline">{events.map((event) => <li key={event.id} className={`is-${event.tone}`}><time>{dateTime(event.at)}</time><div><strong>{event.title}</strong><p>{event.detail}</p></div></li>)}</ol> : <div className="panel-empty-state"><strong>표시할 진료 경과가 없습니다.</strong><span>저장된 평가, 영상, 분석, 협진, 처방, 판독 및 기록이 시간순으로 표시됩니다.</span></div>}</section>; }
function Prescriptions({ items, loading, error, onOpen }: { items: CurrentMedicationItem[]; loading: boolean; error: boolean; onOpen?: () => void }) { return <section className="patient-dashboard-card recent-prescriptions-card"><header className="patient-card-header"><h2>최근 처방</h2></header>{loading ? <div className="panel-empty-state"><strong>처방을 불러오는 중입니다.</strong></div> : error ? <div className="panel-empty-state is-error"><strong>처방을 불러오지 못했습니다.</strong><span>환자 접근 권한과 네트워크 상태를 확인하세요.</span></div> : items.length ? <ul className="recent-prescription-list">{items.slice(0, 3).map((item) => <li key={item.item_id}><strong>{item.medication_name}</strong><span>{item.dose} {item.dose_unit} · 1일 {item.frequency_per_day}회</span></li>)}</ul> : <div className="panel-empty-state"><strong>현재 복용 중인 처방이 없습니다.</strong><span>최종 확정된 활성 처방이 표시됩니다.</span></div>}<button className="patient-panel-link recent-prescriptions-card__open" type="button" onClick={onOpen}>처방 / DUR 열기</button></section>; }

export default function PatientChart({ patient, encounterId, patients = [], onSelectPatient, onNavigate, canViewAIAnalyses = false, canViewConsultations = false, consultationDraft = null, onConsultationDraftConsumed }: Props) {
  const [activeTab, setActiveTab] = useState<"summary" | "clinical">("summary");
  const [patientList, setPatientList] = useState<Patient[]>(patients); const [data, setData] = useState<ChartData>({ studies: [], analyses: [], consultations: [] });
  const [isPermissionModalOpen, setIsPermissionModalOpen] = useState(false);
  const [patientDetail, setPatientDetail] = useState<PatientDetail | null>(null); const [loading, setLoading] = useState(false); const [error, setError] = useState<string | null>(null); const [selectedStudyId, setSelectedStudyId] = useState<string | null>(null); const [analysisResults, setAnalysisResults] = useState<Record<string, AIAnalysisResult>>({}); const [analysisLoading, setAnalysisLoading] = useState(false); const [analysisError, setAnalysisError] = useState<string | null>(null); const clinicalRequestId = useRef(0); const analysisRequestId = useRef(0);
  const [accessDenied, setAccessDenied] = useState(false);
  const [encounter, setEncounter] = useState<EncounterListItem | null>(null); const [encounterLoading, setEncounterLoading] = useState(false); const [encounterError, setEncounterError] = useState<string | null>(null); const encounterRequestId = useRef(0);
  const [latestAssessment, setLatestAssessment] = useState<AssessmentDetailResponse | null>(null); const [vitalLoading, setVitalLoading] = useState(false); const [vitalError, setVitalError] = useState(false); const vitalRequestId = useRef(0);
  const [triageReviewData, setTriageReviewData] = useState<TriageReviewListResponse | null>(null);
  const [triageReviewLoading, setTriageReviewLoading] = useState(false);
  const [triageReviewError, setTriageReviewError] = useState<string | null>(null);
  const [isTriageReviewOpen, setIsTriageReviewOpen] = useState(false);
  const [reviewPriority, setReviewPriority] = useState<TriagePriority | "">("");
  const [reviewReason, setReviewReason] = useState("");
  const [reviewSubmitting, setReviewSubmitting] = useState(false);
  const [currentMedications, setCurrentMedications] = useState<CurrentMedicationItem[]>([]); const [medicationsLoading, setMedicationsLoading] = useState(false); const [medicationsError, setMedicationsError] = useState(false); const medicationRequestId = useRef(0);
  const [timelineEvents, setTimelineEvents] = useState<PatientTimelineEvent[]>([]); const [timelineLoading, setTimelineLoading] = useState(false); const [timelineError, setTimelineError] = useState(false); const timelineRequestId = useRef(0);
  const automaticPatientId = useRef<string | null>(null);
  const currentUser = loadAuthSession()?.user;
  const currentRole = currentUser?.role.code;
  const isNurse =
    currentRole === "NURSE" ||
    currentRole === "MASTER";
  const canRequestConsultation =
    currentRole === "NEUROLOGIST" ||
    currentRole === "MASTER";
  const canViewTriageReviews =
    currentRole === "NEUROLOGIST" &&
    Boolean(
      latestAssessment?.assigned_neurologist?.id &&
      latestAssessment.assigned_neurologist.id === currentUser?.id,
    );
  const canReviewTriage =
    canViewTriageReviews &&
    encounter?.status !== "COMPLETED" &&
    !encounter?.ended_at;

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
    if (!consultationDraft || consultationDraft.patientId !== patient?.id) return;
    setConsultationType(consultationDraft.consultationType);
    setConsultationPriority(consultationDraft.priority);
    setConsultationReason(consultationDraft.reason);
    setConsultationRequestError(null);
    setIsConsultationRequestOpen(true);
    onConsultationDraftConsumed?.();
  }, [consultationDraft, encounterId, onConsultationDraftConsumed, patient?.id]);

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
    setPatientDetail(null); setData({ studies: [], analyses: [], consultations: [] }); setSelectedStudyId(null); setAnalysisResults({}); setAnalysisError(null); setError(null); setAccessDenied(false);
    if (!patient) { setLoading(false); return; }
    setLoading(true);
    const analysesRequest = canViewAIAnalyses ? getAIAnalyses() : Promise.resolve({ count: 0, results: [] as AIAnalysisItem[] });
    const consultationsRequest = canViewConsultations ? getConsultations() : Promise.resolve({ count: 0, results: [] as ConsultationListItem[] });
    void Promise.allSettled([getPatient(patient.id), getImagingStudies({ patientId: patient.id }), analysesRequest, consultationsRequest]).then(([detail, imaging, analyses, consultations]) => {
      if (clinicalRequestId.current !== requestId) return;
      if (detail.status === "rejected" && [403, 404].includes(getApiRequestStatus(detail.reason) ?? 0)) {
        setAccessDenied(true);
        setData({ studies: [], analyses: [], consultations: [] });
        setError("선택한 환자 정보에 접근할 권한이 없거나 더 이상 조회할 수 없습니다.");
        setLoading(false);
        return;
      }
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
    const requestId = ++vitalRequestId.current;
    setLatestAssessment(null);
    setVitalError(false);
    if (!encounterId) {
      setVitalLoading(false);
      return;
    }
    setVitalLoading(true);
    void getAssessmentsByEncounter(encounterId).then((response) => {
      if (vitalRequestId.current !== requestId) return;
      setLatestAssessment(
        latestCompletedAssessment(response.results),
      );
    }).catch(() => {
      if (vitalRequestId.current !== requestId) return;
      setVitalError(true);
    }).finally(() => {
      if (vitalRequestId.current === requestId) setVitalLoading(false);
    });
    return () => { if (vitalRequestId.current === requestId) vitalRequestId.current += 1; };
  }, [encounterId, patient?.id]);

  useEffect(() => {
    let active = true;
    setTriageReviewData(null);
    setTriageReviewError(null);

    if (!latestAssessment?.assessment_id || !canViewTriageReviews) {
      setTriageReviewLoading(false);
      return () => {
        active = false;
      };
    }

    setTriageReviewLoading(true);
    void getTriageReviews(latestAssessment.assessment_id)
      .then((response) => {
        if (active) setTriageReviewData(response);
      })
      .catch(() => {
        if (active) {
          setTriageReviewError("의사 재평가 이력을 불러오지 못했습니다.");
        }
      })
      .finally(() => {
        if (active) setTriageReviewLoading(false);
      });

    return () => {
      active = false;
    };
  }, [canViewTriageReviews, latestAssessment?.assessment_id]);

  useEffect(() => {
    const requestId = ++medicationRequestId.current;
    setCurrentMedications([]);
    setMedicationsError(false);
    if (!patient) {
      setMedicationsLoading(false);
      return;
    }
    setMedicationsLoading(true);
    void getCurrentMedications(patient.id).then((response) => {
      if (medicationRequestId.current === requestId) setCurrentMedications(response.results);
    }).catch(() => {
      if (medicationRequestId.current === requestId) setMedicationsError(true);
    }).finally(() => {
      if (medicationRequestId.current === requestId) setMedicationsLoading(false);
    });
    return () => { if (medicationRequestId.current === requestId) medicationRequestId.current += 1; };
  }, [patient?.id]);

  useEffect(() => {
    const requestId = ++timelineRequestId.current;
    setTimelineEvents([]);
    setTimelineError(false);
    if (!patient) {
      setTimelineLoading(false);
      return;
    }
    setTimelineLoading(true);
    void getPatientTimeline(patient.id).then((response) => {
      if (timelineRequestId.current === requestId) setTimelineEvents(response.results);
    }).catch(() => {
      if (timelineRequestId.current === requestId) setTimelineError(true);
    }).finally(() => {
      if (timelineRequestId.current === requestId) setTimelineLoading(false);
    });
    return () => { if (timelineRequestId.current === requestId) timelineRequestId.current += 1; };
  }, [patient?.id]);

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

  const displayPatient =
    accessDenied
      ? null
      : patientDetail?.id === patient?.id
        ? patientDetail
        : patient;

  const displayAssessment =
    latestAssessment ??
    (
      patientDetail &&
      patientDetail.id === patient?.id
        ? patientDetail.latest_assessment ?? null
        : null
    );
  const studies = useMemo(() => patient ? data.studies.filter((item) => item.patient_id === patient.id).sort((a, b) => (b.study_at ?? "").localeCompare(a.study_at ?? "")) : [], [data.studies, patient]);
  const studyIds = useMemo(() => new Set(studies.map((item) => item.id)), [studies]); const analyses = useMemo(() => data.analyses.filter((item) => studyIds.has(item.study_id)).sort((a, b) => b.requested_at.localeCompare(a.requested_at)), [data.analyses, studyIds]); const consultations = useMemo(() => patient ? data.consultations.filter((item) => item.patient_summary?.id === patient.id).sort((a, b) => b.requested_at.localeCompare(a.requested_at)) : [], [data.consultations, patient]);
  const selectedStudy = studies.find((item) => item.id === selectedStudyId) ?? studies[0] ?? null; const selectedAnalysis = selectedStudy ? analyses.find((item) => item.study_id === selectedStudy.id) ?? null : null; const selectedAnalysisResult = selectedAnalysis ? analysisResults[selectedAnalysis.analysis_id] ?? null : null;
  useEffect(() => { const id = ++analysisRequestId.current; if (!selectedAnalysis || selectedAnalysis.status !== "COMPLETED" || analysisResults[selectedAnalysis.analysis_id]) { setAnalysisLoading(false); return; } setAnalysisLoading(true); setAnalysisError(null); getAIAnalysisResult(selectedAnalysis.analysis_id).then((value) => { if (analysisRequestId.current === id) setAnalysisResults((current) => ({ ...current, [value.analysis_id]: value })); }).catch(() => { if (analysisRequestId.current === id) setAnalysisError("AI 상세 결과를 불러오지 못했습니다."); }).finally(() => { if (analysisRequestId.current === id) setAnalysisLoading(false); }); }, [selectedAnalysis?.analysis_id, selectedAnalysis?.status, analysisResults]);

  function openTriageReview() {
    if (!canReviewTriage || !latestAssessment) return;
    const currentPriority =
      triageReviewData?.effective_priority ??
      latestAssessment.triage_priority ??
      "";
    setReviewPriority(currentPriority);
    setReviewReason("");
    setTriageReviewError(null);
    setIsTriageReviewOpen(true);
  }

  function closeTriageReview() {
    if (reviewSubmitting) return;
    setIsTriageReviewOpen(false);
    setReviewReason("");
    setTriageReviewError(null);
  }

  async function handleTriageReviewSubmit(
    event: FormEvent<HTMLFormElement>,
  ) {
    event.preventDefault();

    if (
      !latestAssessment?.assessment_id ||
      !reviewPriority ||
      !reviewReason.trim() ||
      !canReviewTriage
    ) {
      setTriageReviewError("재평가 우선순위와 사유를 입력해 주세요.");
      return;
    }

    try {
      setReviewSubmitting(true);
      setTriageReviewError(null);

      const response = await createTriageReview(
        latestAssessment.assessment_id,
        {
          priority: reviewPriority,
          reason: reviewReason.trim(),
        },
      );

      setTriageReviewData(response);
      setIsTriageReviewOpen(false);
      setReviewReason("");
    } catch {
      setTriageReviewError("의사 재평가를 저장하지 못했습니다.");
    } finally {
      setReviewSubmitting(false);
    }
  }

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

  function selectPatient(nextPatient: Patient) { setSelectedStudyId(null); setError(null); setAccessDenied(false); setActiveTab("summary"); onSelectPatient?.(nextPatient); }
  return <section className="patient-context-dashboard">
    <div className="patient-workspace">
      <PatientRail selectedId={patient?.id ?? null} patients={patientList.length ? patientList : patients} onSelect={selectPatient} />
      {displayPatient && (
        <PatientHeader
          patient={displayPatient}
          assessment={displayAssessment}
          care={
            encounter
              ? {
                  arrivedAt: encounter.arrived_at,
                  endedAt: encounter.ended_at,
                  encounterStatus: encounter.status,
                  encounterType: encounter.encounter_type,
                }
              : undefined
          }
        />
      )}
      {patient && !accessDenied ? <main className={`patient-context-main${activeTab === "clinical" ? " is-clinical" : ""}`}>
        {activeTab === "summary" && (
          <TriageSummaryBar
            assessment={displayAssessment}
            reviewData={triageReviewData}
            loading={vitalLoading}
            error={vitalError}
            canReview={canReviewTriage && !triageReviewLoading}
            onReview={openTriageReview}
          />
        )}
        <nav className="patient-chart-tabs" aria-label="환자 정보 탭"><button type="button" className={activeTab === "summary" ? "is-active" : ""} onClick={() => setActiveTab("summary")}>요약</button><button type="button" className={activeTab === "clinical" ? "is-active" : ""} onClick={() => setActiveTab("clinical")}>진료정보</button></nav>
        {activeTab === "clinical" && <ClinicalNotesReadOnly patientId={patient.id} encounterId={encounterId} />}
        {encounterLoading ? (
          <div className="patient-encounter-state">
            Encounter 정보를 불러오는 중입니다.
          </div>
        ) : !encounterId ? (
          <div className="patient-encounter-state is-empty">
            {displayAssessment
              ? "현재 진행 중인 진료는 없으며 최근 완료 진료기록을 표시합니다."
              : "현재 진행 중인 Encounter가 없습니다."}
          </div>
        ) : encounterError ? (
          <div className="patient-encounter-state is-empty">
            {encounterError}
          </div>
        ) : null}
        {error && <div className="patient-data-warning">{error}</div>}
        <SummaryCards
          studies={studies}
          consultations={consultations}
          latestAssessment={displayAssessment}
          vitalLoading={vitalLoading}
          vitalError={vitalError}
          onNavigate={onNavigate}
          canRequestConsultation={canRequestConsultation}
          consultationRequestDisabled={consultationRequestDisabled}
          onRequestConsultation={() => {
            setConsultationRequestError(null);
            setIsConsultationRequestOpen(true);
          }}
        />
        <div className="patient-clinical-focus">{loading ? <div className="patient-chart-loading">환자 임상 데이터를 불러오는 중입니다.</div> : <><Viewer studies={studies} selected={selectedStudy} completedAnalysis={selectedAnalysis?.status === "COMPLETED" ? selectedAnalysis : null} onSelect={setSelectedStudyId} onOpen={() => onNavigate?.("imaging")} /><Analysis item={selectedAnalysis} result={selectedAnalysisResult} study={selectedStudy} loading={analysisLoading} error={analysisError} onOpen={() => onNavigate?.("ai-results")} /></>}</div>
      </main> : <main className="patient-context-main patient-context-main--empty"><div className="patient-selection-empty"><strong>{accessDenied ? "환자 정보 접근 권한이 없습니다." : "선택된 환자가 없습니다."}</strong><span>{accessDenied ? "담당 환자 배정 또는 협진 참여 여부를 확인해 주세요." : "왼쪽 환자 목록에서 환자를 선택해 주세요."}</span></div></main>}
    </div>
    <aside className="patient-context-aside"><Prescriptions items={currentMedications} loading={medicationsLoading} error={medicationsError} onOpen={() => isNurse ? setIsPermissionModalOpen(true) : onNavigate?.("prescriptions")} /><Timeline events={patient ? timelineEvents : []} loading={timelineLoading} error={timelineError} /></aside>
    {isTriageReviewOpen && latestAssessment && (
      <div className="triage-review-backdrop" role="presentation">
        <section
          className="triage-review-modal"
          role="dialog"
          aria-modal="true"
          aria-labelledby="triage-review-title"
        >
          <header className="triage-review-modal__header">
            <div>
              <span>PHYSICIAN REASSESSMENT</span>
              <h2 id="triage-review-title">초기평가 우선순위 재평가</h2>
            </div>
            <button
              type="button"
              aria-label="닫기"
              disabled={reviewSubmitting}
              onClick={closeTriageReview}
            >
              ×
            </button>
          </header>

          <form
            className="triage-review-form"
            onSubmit={handleTriageReviewSubmit}
          >
            <div className="triage-review-origin">
              <div>
                <span>간호사 초기분류</span>
                <strong>
                  {triagePriorityLabel(latestAssessment.triage_priority)}
                </strong>
                <small>{latestAssessment.triage_priority ?? "-"}</small>
              </div>

              {triageReviewData?.latest_review && (
                <div>
                  <span>최근 의사 재평가</span>
                  <strong>
                    {triagePriorityLabel(
                      triageReviewData.latest_review.priority,
                    )}
                  </strong>
                  <small>
                    {triageReviewData.latest_review.reviewer.name} ·{" "}
                    {dateTime(triageReviewData.latest_review.created_at)}
                  </small>
                </div>
              )}
            </div>

            {triageReviewData?.reviews.length ? (
              <div className="triage-review-history">
                <span>재평가 이력 {triageReviewData.reviews.length}건</span>
                <ol>
                  {[...triageReviewData.reviews].reverse().map((review) => (
                    <li key={review.review_id}>
                      <div>
                        <strong>{triagePriorityLabel(review.priority)}</strong>
                        <small>
                          {review.reviewer.name} · {dateTime(review.created_at)}
                        </small>
                      </div>
                      <p>{review.reason}</p>
                    </li>
                  ))}
                </ol>
              </div>
            ) : null}

            <label>
              <span>재평가 우선순위 *</span>
              <select
                value={reviewPriority}
                disabled={reviewSubmitting}
                onChange={(event) =>
                  setReviewPriority(
                    event.target.value as TriagePriority | "",
                  )
                }
              >
                <option value="">선택하세요</option>
                <option value="EMERGENCY">응급 (EMERGENCY)</option>
                <option value="URGENT">긴급 (URGENT)</option>
                <option value="NON_EMERGENCY">비응급 (NON_EMERGENCY)</option>
              </select>
            </label>

            <label>
              <span>재평가 사유 *</span>
              <textarea
                value={reviewReason}
                disabled={reviewSubmitting}
                placeholder="현재 상태와 재분류 근거를 기록하세요."
                onChange={(event) => setReviewReason(event.target.value)}
              />
            </label>

            {triageReviewError && (
              <p className="triage-review-error">
                {triageReviewError}
              </p>
            )}

            <footer>
              <button
                type="button"
                disabled={reviewSubmitting}
                onClick={closeTriageReview}
              >
                취소
              </button>
              <button
                type="submit"
                className="is-primary"
                disabled={
                  reviewSubmitting ||
                  !reviewPriority ||
                  !reviewReason.trim()
                }
              >
                {reviewSubmitting ? "저장 중..." : "재평가 저장"}
              </button>
            </footer>
          </form>
        </section>
      </div>
    )}
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
