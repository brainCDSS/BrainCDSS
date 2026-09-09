import { useEffect, useMemo, useState } from "react";

import { getAIAnalyses, getAIAnalysisResult } from "../ai-analysis/api";
import type { AIAnalysisItem, AIAnalysisResult } from "../ai-analysis/types";
import { getConsultations } from "../consultations/api";
import type { ConsultationListItem } from "../consultations/types";
import { getImagingStudies } from "../imaging/api";
import type { ImagingStudy } from "../imaging/types";
import { getPatients } from "./api";
import type { Patient } from "./types";

import "./css/patient_chart.css";

type PatientDestination = "imaging" | "ai-results" | "consultations" | "prescriptions";

interface PatientChartProps {
  patient: Patient;
  patients?: Patient[];
  onSelectPatient?: (patient: Patient) => void;
  onBackToList?: () => void;
  onNavigate?: (destination: PatientDestination) => void;
}

interface DashboardData {
  studies: ImagingStudy[];
  analyses: AIAnalysisItem[];
  consultations: ConsultationListItem[];
}

interface TimelineEvent {
  id: string;
  occurredAt: string;
  title: string;
  description: string;
  tone: "imaging" | "ai" | "consultation";
}

const ANALYSIS_LABELS: Record<string, string> = {
  ISCHEMIA: "허혈성 뇌졸중",
  ISCHEMIC_STROKE: "허혈성 뇌졸중",
  HEMORRHAGE: "출혈성 뇌졸중",
  HEMORRHAGIC_STROKE: "출혈성 뇌졸중",
  ANEURYSM: "뇌동맥류",
};

function formatSex(sex: string | null) {
  if (!sex) return "-";
  if (sex === "M" || sex === "MALE") return "남";
  if (sex === "F" || sex === "FEMALE") return "여";
  return sex;
}

function formatAge(patient: Patient) {
  return patient.estimated_age === null ? "-" : `${patient.estimated_age}세`;
}

function formatDateTime(value: string | null | undefined) {
  if (!value) return "-";
  const date = new Date(value);
  return Number.isNaN(date.getTime())
    ? value
    : date.toLocaleString("ko-KR", {
        month: "2-digit",
        day: "2-digit",
        hour: "2-digit",
        minute: "2-digit",
      });
}

function analysisLabel(type: string) {
  return ANALYSIS_LABELS[type.toUpperCase()] ?? type;
}

function getStudyStatus(studies: ImagingStudy[]) {
  if (studies.some((study) => study.status === "REVIEW_REQUIRED")) return "판독 확인 필요";
  if (studies.some((study) => study.status === "QUEUED")) return "검사 대기";
  return studies.length > 0 ? "영상 준비됨" : "영상 없음";
}

function getAnalysisStatus(analyses: AIAnalysisItem[]) {
  if (analyses.some((item) => item.status === "FAILED")) return "분석 실패";
  if (analyses.some((item) => item.status === "PROCESSING")) return "분석 중";
  if (analyses.some((item) => item.status === "QUEUED")) return "분석 대기";
  return analyses.some((item) => item.status === "COMPLETED") ? "분석 완료" : "분석 없음";
}

function PatientRail({ patient, patients, studies, analyses, onSelectPatient }: {
  patient: Patient;
  patients: Patient[];
  studies: ImagingStudy[];
  analyses: AIAnalysisItem[];
  onSelectPatient?: (patient: Patient) => void;
}) {
  const [search, setSearch] = useState("");
  const filteredPatients = useMemo(() => {
    const keyword = search.trim().toLowerCase();
    return keyword
      ? patients.filter((item) =>
          item.name.toLowerCase().includes(keyword) ||
          item.patient_no.toLowerCase().includes(keyword),
        )
      : patients;
  }, [patients, search]);

  return (
    <aside className="patient-context-rail" aria-label="환자 목록">
      <header className="patient-context-rail__header">
        <div><span>Patient list</span><strong>환자 목록</strong></div>
        <small>{patients.length}명</small>
      </header>
      <label className="patient-context-search">
        <svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="11" cy="11" r="7" /><path d="m20 20-4-4" /></svg>
        <input type="search" value={search} onChange={(event) => setSearch(event.target.value)} placeholder="이름 또는 등록번호 검색" />
      </label>
      <div className="patient-context-list">
        {filteredPatients.map((item) => {
          const patientStudies = studies.filter((study) => study.patient_id === item.id);
          const studyIds = new Set(patientStudies.map((study) => study.id));
          const patientAnalyses = analyses.filter((analysis) => studyIds.has(analysis.study_id));
          return (
            <button
              key={item.id}
              type="button"
              className={item.id === patient.id ? "patient-context-item is-selected" : "patient-context-item"}
              onClick={() => onSelectPatient?.(item)}
              aria-current={item.id === patient.id ? "true" : undefined}
            >
              <span className="patient-context-item__topline"><strong>{item.name}</strong><small>{formatSex(item.sex)} · {formatAge(item)}</small></span>
              <span className="patient-context-item__meta"><span>진료과 미연결</span><span className={`patient-mini-status is-${item.status.toLowerCase()}`}>{item.status}</span></span>
              <span className="patient-context-item__signals"><small>{getStudyStatus(patientStudies)}</small><small>{getAnalysisStatus(patientAnalyses)}</small></span>
            </button>
          );
        })}
        {filteredPatients.length === 0 && <div className="patient-context-empty">검색 결과가 없습니다.</div>}
      </div>
    </aside>
  );
}

function PatientHeader({ patient, onNavigate }: { patient: Patient; onNavigate?: (destination: PatientDestination) => void }) {
  return (
    <header className="patient-context-header">
      <div className="patient-context-header__identity">
        <div className="patient-avatar" aria-hidden="true">{patient.name.slice(0, 1)}</div>
        <div>
          <span className="patient-context-eyebrow">Patient context</span>
          <div className="patient-context-title"><h1>{patient.name}</h1><span className={`patient-status is-${patient.status.toLowerCase()}`}>{patient.status}</span></div>
          <div className="patient-context-demographics">
            <span>{formatSex(patient.sex)} · {formatAge(patient)}</span><span>{patient.patient_no}</span><span>진료과 미연결</span><span>내원일 미연결</span>
          </div>
        </div>
      </div>
      {onNavigate && (
        <div className="patient-quick-actions" aria-label="환자 빠른 작업">
          <button type="button" onClick={() => onNavigate("imaging")}>영상 보기</button>
          <button type="button" onClick={() => onNavigate("ai-results")}>AI 결과</button>
          <button type="button" onClick={() => onNavigate("consultations")}>협진</button>
          <button type="button" onClick={() => onNavigate("prescriptions")}>처방</button>
        </div>
      )}
    </header>
  );
}

function BrainImagingPanel({ studies, selectedStudy, onSelectStudy, onOpenImaging }: {
  studies: ImagingStudy[];
  selectedStudy: ImagingStudy | null;
  onSelectStudy: (study: ImagingStudy) => void;
  onOpenImaging?: () => void;
}) {
  return (
    <section className="patient-dashboard-card brain-viewer-card">
      <header className="patient-card-header is-dark">
        <div><span>Neuro imaging</span><h2>뇌 영상 Viewer</h2></div>
        <div className="viewer-series-tabs" aria-label="영상 시리즈">
          {studies.slice(0, 5).map((study) => <button key={study.id} type="button" className={selectedStudy?.id === study.id ? "is-active" : ""} onClick={() => onSelectStudy(study)}>{study.modality}</button>)}
        </div>
      </header>
      <div className="brain-viewer-stage">
        <div className="viewer-toolbar" aria-label="영상 뷰어 도구 상태">
          {['Slice', 'Zoom', 'W/L', 'Pan', 'Overlay'].map((tool) => <button key={tool} type="button" disabled title="현재 상세 영상 Viewer API가 없습니다.">{tool}</button>)}
        </div>
        {selectedStudy ? (
          <div className="viewer-study-state">
            <div className="viewer-scan-placeholder" aria-hidden="true"><span /><span /><span /></div>
            <strong>{selectedStudy.modality} · {selectedStudy.series}</strong>
            <p>Study metadata는 연결되었습니다. 픽셀 영상은 기존 영상 업무 화면에서 확인하세요.</p>
            {onOpenImaging && <button type="button" onClick={onOpenImaging}>영상 업무에서 열기</button>}
          </div>
        ) : (
          <div className="viewer-study-state is-empty"><div className="viewer-empty-icon" aria-hidden="true">◇</div><strong>연결된 뇌 영상이 없습니다</strong><p>이 환자와 매칭되는 영상 Study가 조회되면 여기에 표시됩니다.</p></div>
        )}
        {selectedStudy && <div className="viewer-overlay-info"><span>{selectedStudy.source}</span><span>{formatDateTime(selectedStudy.study_at)}</span><span>{selectedStudy.status}</span></div>}
      </div>
    </section>
  );
}

function AIAnalysisPanel({ analyses, result, isLoading, error, onSelectAnalysis }: {
  analyses: AIAnalysisItem[];
  result: AIAnalysisResult | null;
  isLoading: boolean;
  error: string | null;
  onSelectAnalysis: (analysis: AIAnalysisItem) => void;
}) {
  const current = analyses.find((item) => item.analysis_id === result?.analysis_id) ?? analyses[0] ?? null;
  const findings = result ? Object.entries(result.structured_findings).slice(0, 3) : [];
  return (
    <section className="patient-dashboard-card ai-result-card">
      <header className="patient-card-header"><div><span>Decision support</span><h2>AI 분석 결과</h2></div>{current && <span className={`analysis-status is-${current.status.toLowerCase()}`}>{current.status}</span>}</header>
      <div className="analysis-model-strip" aria-label="뇌질환 분석 모델">
        {["ISCHEMIA", "HEMORRHAGE", "ANEURYSM"].map((type) => {
          const analysis = analyses.find((item) => item.analysis_type.toUpperCase().includes(type));
          return <button key={type} type="button" disabled={!analysis} className={analysis?.analysis_id === current?.analysis_id ? "is-active" : ""} onClick={() => analysis && onSelectAnalysis(analysis)}><span>{analysisLabel(type)}</span><small>{analysis?.status ?? "결과 없음"}</small></button>;
        })}
      </div>
      {isLoading && <div className="panel-empty-state">AI 결과를 불러오는 중입니다.</div>}
      {!isLoading && error && <div className="panel-empty-state is-error">{error}</div>}
      {!isLoading && !error && !current && <div className="panel-empty-state"><strong>AI 분석 결과가 없습니다</strong><span>선택 환자의 영상과 연결된 분석만 표시합니다.</span></div>}
      {!isLoading && !error && current && !result && <div className="panel-empty-state"><strong>{analysisLabel(current.analysis_type)}</strong><span>현재 상태: {current.status} · 완료된 결과가 아직 없습니다.</span></div>}
      {result && (
        <div className="analysis-result-body">
          <div className="analysis-hero-metric"><div><span>분석 질환</span><strong>{analysisLabel(current?.analysis_type ?? "-")}</strong></div><div className={`risk-orb is-${result.severity.toLowerCase()}`}><strong>{Math.round(result.confidence * 100)}%</strong><span>Confidence</span></div></div>
          <dl className="analysis-metrics"><div><dt>판정</dt><dd>{result.is_positive ? "양성 소견" : "음성 소견"}</dd></div><div><dt>위험도</dt><dd>{result.severity || "-"}</dd></div><div><dt>병변 수</dt><dd>{result.lesion_count}개</dd></div><div><dt>병변 부피</dt><dd>{result.total_volume_ml} mL</dd></div></dl>
          <div className="analysis-findings"><span>주요 소견</span>{findings.length > 0 ? findings.map(([key, value]) => <div key={key}><strong>{key.replaceAll("_", " ")}</strong><p>{typeof value === "string" || typeof value === "number" ? String(value) : JSON.stringify(value)}</p></div>) : <p>구조화된 주요 소견이 없습니다.</p>}</div>
        </div>
      )}
    </section>
  );
}

function SummaryCards({ patient, studies, consultations, onNavigate }: {
  patient: Patient;
  studies: ImagingStudy[];
  consultations: ConsultationListItem[];
  onNavigate?: (destination: PatientDestination) => void;
}) {
  const latestStudy = studies[0];
  const latestConsultation = consultations[0];
  return (
    <section className="patient-summary-grid" aria-label="환자 요약">
      <article className="patient-summary-card"><header><span>01</span><h3>기본정보</h3></header><dl><div><dt>생년월일</dt><dd>{patient.birth_date ?? "-"}</dd></div><div><dt>연락처</dt><dd>{patient.phone ?? "-"}</dd></div><div><dt>환자 ID</dt><dd className="is-code">{patient.id}</dd></div></dl></article>
      <article className="patient-summary-card"><header><span>02</span><h3>Vital</h3></header><div className="summary-empty"><strong>연결된 Vital 없음</strong><small>환자별 활력징후 조회 API가 없습니다.</small></div></article>
      <article className="patient-summary-card"><header><span>03</span><h3>주요 검사</h3></header>{latestStudy ? <dl><div><dt>최근 영상</dt><dd>{latestStudy.modality}</dd></div><div><dt>시리즈</dt><dd>{latestStudy.series}</dd></div><div><dt>상태</dt><dd>{latestStudy.status}</dd></div></dl> : <div className="summary-empty"><strong>연결된 검사 없음</strong></div>}{onNavigate && <button type="button" onClick={() => onNavigate("imaging")}>전체보기</button>}</article>
      <article className="patient-summary-card"><header><span>04</span><h3>협진</h3></header>{latestConsultation ? <dl><div><dt>유형</dt><dd>{latestConsultation.type}</dd></div><div><dt>우선순위</dt><dd>{latestConsultation.priority}</dd></div><div><dt>상태</dt><dd>{latestConsultation.status}</dd></div></dl> : <div className="summary-empty"><strong>진행 중 협진 없음</strong></div>}{onNavigate && <button type="button" onClick={() => onNavigate("consultations")}>전체보기</button>}</article>
    </section>
  );
}

function SchedulePanel() {
  const today = new Date();
  const firstDay = new Date(today.getFullYear(), today.getMonth(), 1).getDay();
  const lastDate = new Date(today.getFullYear(), today.getMonth() + 1, 0).getDate();
  const cells = Array.from({ length: firstDay + lastDate }, (_, index) => index < firstDay ? null : index - firstDay + 1);
  return (
    <section className="patient-dashboard-card schedule-card">
      <header className="patient-card-header"><div><span>Schedule</span><h2>달력 / 일정</h2></div><strong>{today.getFullYear()}. {String(today.getMonth() + 1).padStart(2, "0")}</strong></header>
      <div className="mini-calendar">{["일", "월", "화", "수", "목", "금", "토"].map((day) => <span key={day} className="mini-calendar__weekday">{day}</span>)}{cells.map((date, index) => <span key={`${date ?? "blank"}-${index}`} className={date === today.getDate() ? "is-today" : ""}>{date}</span>)}</div>
      <div className="schedule-empty"><strong>연결된 환자 일정이 없습니다</strong><span>예약·진료 일정 API가 연결되면 오늘 일정이 표시됩니다.</span></div>
    </section>
  );
}

function TimelinePanel({ events, onOpenConsultations }: { events: TimelineEvent[]; onOpenConsultations?: () => void }) {
  return (
    <section className="patient-dashboard-card timeline-card">
      <header className="patient-card-header"><div><span>Clinical progress</span><h2>진료기록 / 경과</h2></div>{onOpenConsultations && <button type="button" onClick={onOpenConsultations}>전체보기</button>}</header>
      {events.length === 0 ? <div className="panel-empty-state"><strong>표시할 진료 경과가 없습니다</strong><span>실제 영상·AI·협진 이벤트가 시간순으로 표시됩니다.</span></div> : <ol className="clinical-timeline">{events.slice(0, 7).map((event) => <li key={event.id} className={`is-${event.tone}`}><time>{formatDateTime(event.occurredAt)}</time><div><strong>{event.title}</strong><p>{event.description}</p></div></li>)}</ol>}
    </section>
  );
}

export default function PatientChart({ patient, patients = [], onSelectPatient, onBackToList, onNavigate }: PatientChartProps) {
  const [patientList, setPatientList] = useState<Patient[]>(patients);
  const [data, setData] = useState<DashboardData>({ studies: [], analyses: [], consultations: [] });
  const [selectedStudyId, setSelectedStudyId] = useState<string | null>(null);
  const [selectedAnalysisId, setSelectedAnalysisId] = useState<string | null>(null);
  const [analysisResult, setAnalysisResult] = useState<AIAnalysisResult | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [analysisLoading, setAnalysisLoading] = useState(false);
  const [dataError, setDataError] = useState<string | null>(null);
  const [analysisError, setAnalysisError] = useState<string | null>(null);

  useEffect(() => { if (patients.length > 0) setPatientList(patients); }, [patients]);

  useEffect(() => {
    let active = true;
    async function loadDashboardData() {
      setIsLoading(true);
      const [patientResponse, imagingResponse, analysisResponse, consultationResponse] = await Promise.allSettled([
        getPatients(), getImagingStudies(), getAIAnalyses(), getConsultations(),
      ]);
      if (!active) return;
      if (patientResponse.status === "fulfilled") setPatientList(patientResponse.value.results);
      setData({
        studies: imagingResponse.status === "fulfilled" ? imagingResponse.value : [],
        analyses: analysisResponse.status === "fulfilled" ? analysisResponse.value.results : [],
        consultations: consultationResponse.status === "fulfilled" ? consultationResponse.value.results : [],
      });
      if ([imagingResponse, analysisResponse, consultationResponse].some((response) => response.status === "rejected")) setDataError("일부 임상 데이터를 불러오지 못했습니다.");
      setIsLoading(false);
    }
    void loadDashboardData();
    return () => { active = false; };
  }, []);

  const patientStudies = useMemo(() => data.studies.filter((study) => study.patient_id === patient.id).sort((a, b) => b.study_at.localeCompare(a.study_at)), [data.studies, patient.id]);
  const studyIds = useMemo(() => new Set(patientStudies.map((study) => study.id)), [patientStudies]);
  const patientAnalyses = useMemo(() => data.analyses.filter((analysis) => studyIds.has(analysis.study_id)).sort((a, b) => b.requested_at.localeCompare(a.requested_at)), [data.analyses, studyIds]);
  const patientConsultations = useMemo(() => data.consultations.filter((item) => item.patient_summary.id === patient.id).sort((a, b) => b.requested_at.localeCompare(a.requested_at)), [data.consultations, patient.id]);
  const selectedStudy = patientStudies.find((study) => study.id === selectedStudyId) ?? patientStudies[0] ?? null;
  const selectedAnalysis = patientAnalyses.find((analysis) => analysis.analysis_id === selectedAnalysisId) ?? patientAnalyses[0] ?? null;

  useEffect(() => {
    let active = true;
    setAnalysisResult(null);
    setAnalysisError(null);
    if (!selectedAnalysis || selectedAnalysis.status !== "COMPLETED") {
      setAnalysisLoading(false);
      return;
    }
    setAnalysisLoading(true);
    getAIAnalysisResult(selectedAnalysis.analysis_id)
      .then((result) => { if (active) setAnalysisResult(result); })
      .catch(() => { if (active) setAnalysisError("완료된 AI 상세 결과를 불러오지 못했습니다."); })
      .finally(() => { if (active) setAnalysisLoading(false); });
    return () => { active = false; };
  }, [selectedAnalysis?.analysis_id, selectedAnalysis?.status]);

  const timelineEvents = useMemo<TimelineEvent[]>(() => [
    ...patientStudies.map((study) => ({ id: `study-${study.id}`, occurredAt: study.study_at, title: `${study.modality} 영상 검사`, description: `${study.series} · ${study.status}`, tone: "imaging" as const })),
    ...patientAnalyses.map((analysis) => ({ id: `analysis-${analysis.analysis_id}`, occurredAt: analysis.requested_at, title: `${analysisLabel(analysis.analysis_type)} AI 분석`, description: `${analysis.status} · ${analysis.stage}`, tone: "ai" as const })),
    ...patientConsultations.map((consultation) => ({ id: `consultation-${consultation.consultation_id}`, occurredAt: consultation.requested_at, title: `${consultation.type} 협진`, description: `${consultation.status} · ${consultation.ui_status}`, tone: "consultation" as const })),
  ].sort((a, b) => b.occurredAt.localeCompare(a.occurredAt)), [patientAnalyses, patientConsultations, patientStudies]);

  return (
    <section className="patient-context-dashboard">
      <PatientRail patient={patient} patients={patientList.length > 0 ? patientList : (patients.length > 0 ? patients : [patient])} studies={data.studies} analyses={data.analyses} onSelectPatient={onSelectPatient} />
      <main className="patient-context-main">
        <PatientHeader patient={patient} onNavigate={onNavigate} />
        {dataError && <div className="patient-data-warning" role="status">{dataError}</div>}
        <div className="patient-clinical-focus">
          <BrainImagingPanel studies={patientStudies} selectedStudy={selectedStudy} onSelectStudy={(study) => setSelectedStudyId(study.id)} onOpenImaging={onNavigate ? () => onNavigate("imaging") : undefined} />
          <AIAnalysisPanel analyses={patientAnalyses} result={analysisResult} isLoading={isLoading || analysisLoading} error={analysisError} onSelectAnalysis={(analysis) => setSelectedAnalysisId(analysis.analysis_id)} />
        </div>
        <SummaryCards patient={patient} studies={patientStudies} consultations={patientConsultations} onNavigate={onNavigate} />
        {onBackToList && <button className="patient-back-link" type="button" onClick={onBackToList}>환자 목록 전체보기</button>}
      </main>
      <aside className="patient-context-aside"><SchedulePanel /><TimelinePanel events={timelineEvents} onOpenConsultations={onNavigate ? () => onNavigate("consultations") : undefined} /></aside>
    </section>
  );
}
