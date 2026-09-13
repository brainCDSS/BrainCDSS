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
  patient: Patient | null;
  patients?: Patient[];
  onSelectPatient?: (patient: Patient) => void;
  onNavigate?: (destination: PatientDestination) => void;
  canViewAIAnalyses?: boolean;
  canViewConsultations?: boolean;
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

const PATIENT_RAIL_PAGE_SIZE = 6;

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

function analysisChipLabel(type: string) {
  const normalized = type.toUpperCase();
  if (normalized.includes("ISCHEM")) return "허혈성";
  if (normalized.includes("HEMORRH")) return "출혈성";
  if (normalized.includes("ANEURYSM")) return "뇌동맥류";
  return analysisLabel(type);
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

function PatientRail({ selectedPatientId, patients, studies, analyses, onSelectPatient, onClearSelection }: {
  selectedPatientId: string | null;
  patients: Patient[];
  studies: ImagingStudy[];
  analyses: AIAnalysisItem[];
  onSelectPatient?: (patient: Patient) => void;
  onClearSelection: () => void;
}) {
  const [search, setSearch] = useState("");
  const [page, setPage] = useState(1);
  const filteredPatients = useMemo(() => {
    const keyword = search.trim().toLowerCase();
    return keyword
      ? patients.filter((item) =>
          item.name.toLowerCase().includes(keyword) ||
          item.patient_no.toLowerCase().includes(keyword),
        )
      : patients;
  }, [patients, search]);
  const pageCount = Math.max(1, Math.ceil(filteredPatients.length / PATIENT_RAIL_PAGE_SIZE));
  const currentPage = Math.min(page, pageCount);
  const pagePatients = filteredPatients.slice(
    (currentPage - 1) * PATIENT_RAIL_PAGE_SIZE,
    currentPage * PATIENT_RAIL_PAGE_SIZE,
  );

  useEffect(() => {
    setPage(1);
  }, [search]);

  useEffect(() => {
    if (!selectedPatientId) return;
    const selectedIndex = filteredPatients.findIndex((item) => item.id === selectedPatientId);
    if (selectedIndex >= 0) {
      setPage(Math.floor(selectedIndex / PATIENT_RAIL_PAGE_SIZE) + 1);
    }
  }, [filteredPatients, selectedPatientId]);

  return (
    <aside className="patient-context-rail" aria-label="환자 목록">
      <header className="patient-context-rail__header">
        <div><span>Patient list</span><strong>환자 목록</strong></div>
        <div className="patient-context-rail__tools">
          <small>{patients.length}명</small>
          <button type="button" onClick={onClearSelection} title="환자 선택 해제" aria-label="환자 선택 해제">←</button>
        </div>
      </header>
      <label className="patient-context-search">
        <svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="11" cy="11" r="7" /><path d="m20 20-4-4" /></svg>
        <input type="search" value={search} onChange={(event) => setSearch(event.target.value)} placeholder="이름 또는 등록번호 검색" />
      </label>
      <div className="patient-context-list">
        {pagePatients.map((item) => {
          const patientStudies = studies.filter((study) => study.patient_id === item.id);
          const studyIds = new Set(patientStudies.map((study) => study.id));
          const patientAnalyses = analyses.filter((analysis) => studyIds.has(analysis.study_id));
          return (
            <button
              key={item.id}
              type="button"
              className={item.id === selectedPatientId ? "patient-context-item is-selected" : "patient-context-item"}
              onClick={() => onSelectPatient?.(item)}
              aria-current={item.id === selectedPatientId ? "true" : undefined}
            >
              <span className="patient-context-item__topline"><strong>{item.name}</strong><span className={`patient-mini-status is-${item.status.toLowerCase()}`}>{item.status}</span></span>
              <span className="patient-context-item__demographics">{formatSex(item.sex)} · {formatAge(item)} <i aria-hidden="true" /> {item.patient_no}</span>
              <span className="patient-context-item__meta">{item.status} · 최근 이벤트</span>
              <span className="patient-context-item__signals"><small>{getStudyStatus(patientStudies)}</small><small>{getAnalysisStatus(patientAnalyses)}</small></span>
            </button>
          );
        })}
        {filteredPatients.length === 0 && <div className="patient-context-empty">검색 결과가 없습니다.</div>}
      </div>
      <nav className="patient-context-pagination" aria-label="환자 목록 페이지">
        <button type="button" onClick={() => setPage((value) => Math.max(1, value - 1))} disabled={currentPage === 1} aria-label="이전 페이지">‹</button>
        <span><strong>{currentPage}</strong> / {pageCount}</span>
        <button type="button" onClick={() => setPage((value) => Math.min(pageCount, value + 1))} disabled={currentPage === pageCount} aria-label="다음 페이지">›</button>
      </nav>
    </aside>
  );
}

function PatientHeader({ patient }: { patient: Patient }) {
  return (
    <header className="patient-context-header">
      <div className="patient-context-header__identity">
        <div className="patient-avatar" aria-hidden="true">{patient.name.slice(0, 1)}</div>
        <div>
          <span className="patient-context-eyebrow">Patient context</span>
          <div className="patient-context-title"><h1>{patient.name}</h1><span className={`patient-status is-${patient.status.toLowerCase()}`}>{patient.status}</span></div>
          <div className="patient-context-demographics">
            <div><span>{formatSex(patient.sex)} · {formatAge(patient)}</span><span>{patient.birth_date ?? "생년월일 미등록"}</span><span>{patient.patient_no}</span></div>
          </div>
        </div>
      </div>
      <dl className="patient-context-facts">
        <div><dt>내원일시</dt><dd>API 미연결</dd></div>
        <div><dt>주호소</dt><dd>API 미연결</dd></div>
        <div><dt>의심진단</dt><dd>API 미연결</dd></div>
        <div><dt>진료과 / 담당의</dt><dd>API 미연결</dd></div>
      </dl>
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

function AIAnalysisPanel({ analyses, selectedAnalysisId, result, isLoading, error, onSelectAnalysis }: {
  analyses: AIAnalysisItem[];
  selectedAnalysisId: string | null;
  result: AIAnalysisResult | null;
  isLoading: boolean;
  error: string | null;
  onSelectAnalysis: (analysis: AIAnalysisItem) => void;
}) {
  const current = analyses.find((item) => item.analysis_id === selectedAnalysisId) ?? analyses.find((item) => item.analysis_id === result?.analysis_id) ?? analyses[0] ?? null;
  const findings = result ? Object.entries(result.structured_findings).slice(0, 3) : [];
  return (
    <section className="patient-dashboard-card ai-result-card">
      <header className="patient-card-header"><div><span>Decision support</span><h2>AI 분석 결과</h2></div>{current && <span className={`analysis-status is-${current.status.toLowerCase()}`}>{current.status}</span>}</header>
      {analyses.length > 0 && <div className="analysis-model-strip" aria-label="AI 분석 결과 유형">
        {analyses.map((analysis) => <button key={analysis.analysis_id} type="button" className={analysis.analysis_id === current?.analysis_id ? "is-active" : ""} onClick={() => onSelectAnalysis(analysis)}>{analysisChipLabel(analysis.analysis_type)}</button>)}
      </div>}
      {isLoading && <div className="panel-empty-state">AI 결과를 불러오는 중입니다.</div>}
      {!isLoading && error && <div className="panel-empty-state is-error">{error}</div>}
      {!isLoading && !error && !current && <div className="panel-empty-state"><strong>AI 분석 결과가 없습니다.</strong><span>선택 환자의 영상과 연결된 분석 결과가<br />여기에 표시됩니다.</span></div>}
      {!isLoading && !error && current && !result && <div className="panel-empty-state"><strong>{analysisLabel(current.analysis_type)}</strong><span>현재 상태: {current.status} · 완료된 결과가 아직 없습니다.</span></div>}
      {result && (
        <div className="analysis-result-body">
          <div className="analysis-hero-metric"><div><span>분석 질환</span><strong>{analysisLabel(current?.analysis_type ?? "-")}</strong></div><div className={`risk-orb is-${(result.severity || "unknown").toLowerCase()}`}><strong>{result.confidence == null ? "-" : `${Math.round(result.confidence * 100)}%`}</strong><span>예측 점수</span></div></div>
          <dl className="analysis-metrics"><div><dt>판정</dt><dd>{result.is_positive == null ? "결과 없음" : result.is_positive ? "양성 소견" : "음성 소견"}</dd></div><div><dt>AI 중증도</dt><dd>{result.severity || "-"}</dd></div><div><dt>병변 수</dt><dd>{result.lesion_count == null ? "-" : `${result.lesion_count}개`}</dd></div><div><dt>병변 부피</dt><dd>{result.total_volume_ml == null ? "-" : `${result.total_volume_ml} mL`}</dd></div></dl>
          <div className="analysis-findings"><span>주요 소견</span>{findings.length > 0 ? findings.map(([key, value]) => <div key={key}><strong>{key.replaceAll("_", " ")}</strong><p>{typeof value === "string" || typeof value === "number" ? String(value) : JSON.stringify(value)}</p></div>) : <p>구조화된 주요 소견이 없습니다.</p>}</div>
        </div>
      )}
    </section>
  );
}

function PatientSummaryCards({ studies, analyses, consultations, onNavigate }: {
  studies: ImagingStudy[];
  analyses: AIAnalysisItem[];
  consultations: ConsultationListItem[];
  onNavigate?: (destination: PatientDestination) => void;
}) {
  const latestStudy = studies[0] ?? null;
  const latestAnalysis = analyses[0] ?? null;
  const latestConsultation = consultations[0] ?? null;
  return (
    <section className="patient-summary-grid" aria-label="환자 핵심 요약">
      <article className="patient-summary-card"><header><span>♥</span><h3>Vital Sign</h3></header><div className="summary-empty"><strong>Vital API 미연결</strong><span>환자별 활력징후 데이터가 없습니다.</span></div></article>
      <article className="patient-summary-card"><header><span>◆</span><h3>최근 검사</h3></header>{latestStudy ? <dl><div><dt>검사</dt><dd>{latestStudy.modality}</dd></div><div><dt>시각</dt><dd>{formatDateTime(latestStudy.study_at)}</dd></div><div><dt>상태</dt><dd>{latestStudy.status}</dd></div></dl> : <div className="summary-empty"><strong>검사 없음</strong><span>연결된 영상 검사가 없습니다.</span></div>} {onNavigate && <button type="button" onClick={() => onNavigate("imaging")}>검사 상세 보기</button>}</article>
      <article className="patient-summary-card"><header><span>AI</span><h3>AI 분석 상태</h3></header>{latestAnalysis ? <dl><div><dt>유형</dt><dd>{analysisLabel(latestAnalysis.analysis_type)}</dd></div><div><dt>상태</dt><dd>{latestAnalysis.status}</dd></div><div><dt>요청</dt><dd>{formatDateTime(latestAnalysis.requested_at)}</dd></div></dl> : <div className="summary-empty"><strong>분석 없음</strong><span>연결된 AI 분석이 없습니다.</span></div>} {onNavigate && <button type="button" onClick={() => onNavigate("ai-results")}>AI 결과 보기</button>}</article>
      <article className="patient-summary-card"><header><span>♧</span><h3>협진 상태</h3></header>{latestConsultation ? <dl><div><dt>유형</dt><dd>{latestConsultation.type}</dd></div><div><dt>우선순위</dt><dd>{latestConsultation.priority}</dd></div><div><dt>상태</dt><dd>{latestConsultation.ui_status}</dd></div></dl> : <div className="summary-empty"><strong>협진 없음</strong><span>조회 가능한 협진이 없습니다.</span></div>} {onNavigate && <button type="button" onClick={() => onNavigate("consultations")}>협진 현황 보기</button>}</article>
    </section>
  );
}

function RecentTestsPanel({ studies, onOpenImaging }: { studies: ImagingStudy[]; onOpenImaging?: () => void }) {
  return <section className="patient-dashboard-card recent-tests-card">
    <header className="patient-card-header"><div><span>Recent tests</span><h2>주요 검사 결과</h2></div>{onOpenImaging && <button type="button" onClick={onOpenImaging}>전체보기</button>}</header>
    {studies.length === 0 ? <div className="panel-empty-state"><strong>연결된 검사 결과가 없습니다.</strong><span>현재 API에서 조회된 영상 검사가 없습니다.</span></div> : <div className="recent-test-list">{studies.slice(0, 3).map((study) => <div key={study.id}><strong>{study.modality}</strong><span>{study.series}</span><time>{formatDateTime(study.study_at)}</time><em>{study.status}</em></div>)}</div>}
  </section>;
}

function OrderSoapPanel({ studies, consultations }: { studies: ImagingStudy[]; consultations: ConsultationListItem[] }) {
  const items = [
    ...studies.slice(0, 3).map((study) => ({ id: `order-${study.id}`, label: `${study.modality} 영상 검사`, status: study.status, at: study.study_at })),
    ...consultations.slice(0, 2).map((item) => ({ id: `order-${item.consultation_id}`, label: `${item.type} 협진 요청`, status: item.ui_status, at: item.requested_at })),
  ].sort((a, b) => b.at.localeCompare(a.at)).slice(0, 4);
  return <section className="patient-dashboard-card order-soap-card">
    <header className="patient-card-header"><div><span>Clinical notes</span><h2>오더 이력 / SOAP 요약</h2></div></header>
    {items.length > 0 ? <ul>{items.map((item) => <li key={item.id}><time>{formatDateTime(item.at)}</time><strong>{item.label}</strong><span>{item.status}</span></li>)}</ul> : <div className="panel-empty-state"><strong>최근 오더가 없습니다.</strong><span>영상·협진 API에서 확인되는 항목이 없습니다.</span></div>}
    <div className="soap-placeholder"><strong>SOAP 요약</strong><span>진료기록/SOAP 조회 API 미연결</span></div>
  </section>;
}

function TimelinePanel({ events, onOpenConsultations }: { events: TimelineEvent[]; onOpenConsultations?: () => void }) {
  return (
    <section className="patient-dashboard-card timeline-card">
      <header className="patient-card-header"><div><span>Clinical progress</span><h2>진료기록 / 경과</h2></div>{onOpenConsultations && <button type="button" onClick={onOpenConsultations}>전체보기</button>}</header>
      {events.length === 0 ? <div className="panel-empty-state"><strong>표시할 진료 경과가 없습니다</strong><span>실제 영상·AI·협진 이벤트가 시간순으로 표시됩니다.</span></div> : <ol className="clinical-timeline">{events.slice(0, 7).map((event) => <li key={event.id} className={`is-${event.tone}`}><time>{formatDateTime(event.occurredAt)}</time><div><strong>{event.title}</strong><p>{event.description}</p></div></li>)}</ol>}
    </section>
  );
}

export default function PatientChart({
  patient,
  patients = [],
  onSelectPatient,
  onNavigate,
  canViewAIAnalyses = false,
  canViewConsultations = false,
}: PatientChartProps) {
  const [patientList, setPatientList] = useState<Patient[]>(patients);
  const [data, setData] = useState<DashboardData>({ studies: [], analyses: [], consultations: [] });
  const [selectedStudyId, setSelectedStudyId] = useState<string | null>(null);
  const [selectedAnalysisId, setSelectedAnalysisId] = useState<string | null>(null);
  const [analysisResult, setAnalysisResult] = useState<AIAnalysisResult | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [analysisLoading, setAnalysisLoading] = useState(false);
  const [dataError, setDataError] = useState<string | null>(null);
  const [analysisError, setAnalysisError] = useState<string | null>(null);
  const [hasPatientSelection, setHasPatientSelection] = useState(patient !== null);

  useEffect(() => { if (patients.length > 0) setPatientList(patients); }, [patients]);

  useEffect(() => {
    let active = true;
    async function loadDashboardData() {
      setIsLoading(true);
      const analysisRequest = canViewAIAnalyses
        ? getAIAnalyses()
        : Promise.resolve({ count: 0, results: [] });
      const consultationRequest = canViewConsultations
        ? getConsultations()
        : Promise.resolve({ count: 0, results: [] });
      const [patientResponse, imagingResponse, analysisResponse, consultationResponse] = await Promise.allSettled([
        getPatients(), getImagingStudies(), analysisRequest, consultationRequest,
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
  }, [canViewAIAnalyses, canViewConsultations]);

  const selectedPatient = hasPatientSelection ? patient : null;
  const patientStudies = useMemo(() => patient ? data.studies.filter((study) => study.patient_id === patient.id).sort((a, b) => b.study_at.localeCompare(a.study_at)) : [], [data.studies, patient]);
  const studyIds = useMemo(() => new Set(patientStudies.map((study) => study.id)), [patientStudies]);
  const patientAnalyses = useMemo(() => data.analyses.filter((analysis) => studyIds.has(analysis.study_id)).sort((a, b) => b.requested_at.localeCompare(a.requested_at)), [data.analyses, studyIds]);
  const patientConsultations = useMemo(() => patient ? data.consultations.filter((item) => item.patient_summary.id === patient.id).sort((a, b) => b.requested_at.localeCompare(a.requested_at)) : [], [data.consultations, patient]);
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
      <div className="patient-workspace">
        <PatientRail
          selectedPatientId={selectedPatient?.id ?? null}
          patients={patientList.length > 0 ? patientList : (patients.length > 0 ? patients : (patient ? [patient] : []))}
          studies={data.studies}
          analyses={data.analyses}
          onSelectPatient={(nextPatient) => {
            setHasPatientSelection(true);
            onSelectPatient?.(nextPatient);
          }}
          onClearSelection={() => setHasPatientSelection(false)}
        />
        {selectedPatient ? <main className="patient-context-main">
          <PatientHeader patient={selectedPatient} />
          {dataError && <div className="patient-data-warning" role="status">{dataError}</div>}
          <div className="patient-safety-bar" role="status"><strong>주의 정보</strong><span>알레르기 · 항응고제 · 금기사항 조회 API가 연결되지 않았습니다.</span></div>
          <PatientSummaryCards studies={patientStudies} analyses={patientAnalyses} consultations={patientConsultations} onNavigate={onNavigate} />
          <div className="patient-clinical-focus">
            <BrainImagingPanel studies={patientStudies} selectedStudy={selectedStudy} onSelectStudy={(study) => setSelectedStudyId(study.id)} onOpenImaging={onNavigate ? () => onNavigate("imaging") : undefined} />
            <div className="patient-clinical-stack">
              <AIAnalysisPanel analyses={patientAnalyses} selectedAnalysisId={selectedAnalysisId} result={analysisResult} isLoading={isLoading || analysisLoading} error={analysisError} onSelectAnalysis={(analysis) => setSelectedAnalysisId(analysis.analysis_id)} />
              <RecentTestsPanel studies={patientStudies} onOpenImaging={onNavigate ? () => onNavigate("imaging") : undefined} />
            </div>
          </div>
        </main> : <main className="patient-context-main patient-context-main--empty">
          <div className="patient-selection-empty" role="status">
            <strong>선택된 환자가 없습니다.</strong>
            <span>왼쪽 환자 목록에서 차트를 확인할 환자를 선택하세요.</span>
          </div>
        </main>}
      </div>
      {selectedPatient ? <aside className="patient-context-aside"><TimelinePanel events={timelineEvents} onOpenConsultations={onNavigate ? () => onNavigate("consultations") : undefined} /><OrderSoapPanel studies={patientStudies} consultations={patientConsultations} /></aside> : <aside className="patient-context-aside">
        <section className="patient-dashboard-card timeline-card"><header className="patient-card-header"><div><span>Clinical progress</span><h2>진료기록 / 경과</h2></div></header><div className="panel-empty-state"><strong>선택된 환자가 없습니다.</strong><span>환자를 선택하면 해당 환자의 진료 경과가 표시됩니다.</span></div></section>
        <section className="patient-dashboard-card order-soap-card"><header className="patient-card-header"><div><span>Clinical notes</span><h2>오더 이력 / SOAP 요약</h2></div></header><div className="panel-empty-state"><strong>선택된 환자가 없습니다.</strong></div></section>
      </aside>}
    </section>
  );
}
