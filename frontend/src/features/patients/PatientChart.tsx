import { useEffect, useMemo, useRef, useState } from "react";

import { getAIAnalyses, getAIAnalysisResult } from "../ai-analysis/api";
import type { AIAnalysisItem, AIAnalysisResult } from "../ai-analysis/types";
import { getConsultations } from "../consultations/api";
import type { ConsultationListItem } from "../consultations/types";
import { getImagingStudies } from "../imaging/api";
import type { ImagingStudy } from "../imaging/types";
import { getPatients } from "./api";
import type { Patient } from "./types";
import "./css/patient_chart.css";

type Destination = "imaging" | "ai-results" | "consultations" | "prescriptions";
interface Props { patient: Patient | null; patients?: Patient[]; onSelectPatient?: (patient: Patient) => void; onNavigate?: (destination: Destination) => void; canViewAIAnalyses?: boolean; canViewConsultations?: boolean }
interface ChartData { studies: ImagingStudy[]; analyses: AIAnalysisItem[]; consultations: ConsultationListItem[] }
interface TimelineEvent { id: string; at: string; title: string; detail: string; tone: "imaging" | "ai" | "consultation" }
const PAGE_SIZE = 6;

function sex(value: string | null) { return value === "M" || value === "MALE" ? "남" : value === "F" || value === "FEMALE" ? "여" : value || "-"; }
function age(patient: Patient) { return patient.estimated_age === null ? "-" : `${patient.estimated_age}세`; }
function dateTime(value?: string | null) { if (!value) return "-"; const date = new Date(value); return Number.isNaN(date.getTime()) ? value : date.toLocaleString("ko-KR", { month: "2-digit", day: "2-digit", hour: "2-digit", minute: "2-digit" }); }
function analysisName(value: string) { const key = value.toUpperCase(); if (key.includes("ISCHEM")) return "허혈성 뇌졸중"; if (key.includes("HEMORRH")) return "출혈성 뇌졸중"; if (key.includes("ANEURYSM")) return "뇌동맥류"; return value; }

function PatientRail({ selectedId, patients, onSelect }: { selectedId: string | null; patients: Patient[]; onSelect?: (patient: Patient) => void }) {
  const [search, setSearch] = useState(""); const [page, setPage] = useState(1);
  const filtered = useMemo(() => { const query = search.trim().toLowerCase(); return query ? patients.filter((item) => item.name.toLowerCase().includes(query) || item.patient_no.toLowerCase().includes(query)) : patients; }, [patients, search]);
  const pages = Math.max(1, Math.ceil(filtered.length / PAGE_SIZE)); const current = Math.min(page, pages); const rows = filtered.slice((current - 1) * PAGE_SIZE, current * PAGE_SIZE);
  useEffect(() => setPage(1), [search]);
  return <aside className="patient-context-rail"><header className="patient-context-rail__header"><div><span>PATIENT LIST</span><strong>환자 목록</strong></div><small>{patients.length}명</small></header><label className="patient-context-search"><span aria-hidden="true">⌕</span><input type="search" value={search} onChange={(event) => setSearch(event.target.value)} placeholder="이름 또는 등록번호 검색" /></label><div className="patient-context-list">{rows.map((item) => <button key={item.id} type="button" className={`patient-context-item${item.id === selectedId ? " is-selected" : ""}`} onClick={() => onSelect?.(item)} aria-current={item.id === selectedId ? "true" : undefined}><span className="patient-context-item__topline"><strong>{item.name}</strong><span className={`patient-mini-status is-${item.status.toLowerCase()}`}>{item.status}</span></span><span className="patient-context-item__demographics">{sex(item.sex)} · {age(item)}</span><span className="patient-context-item__meta">{item.patient_no}<time>-</time></span></button>)}{rows.length === 0 && <div className="patient-context-empty">검색 결과가 없습니다.</div>}</div><nav className="patient-context-pagination"><button type="button" disabled={current === 1} onClick={() => setPage((value) => Math.max(1, value - 1))}>‹</button><span><strong>{current}</strong> / {pages}</span><button type="button" disabled={current === pages} onClick={() => setPage((value) => Math.min(pages, value + 1))}>›</button></nav></aside>;
}

function PatientHeader({ patient }: { patient: Patient }) {
  return <header className="patient-context-header patient-context-header--compact">
    <div className="patient-context-header__identity">
      <div className="patient-avatar" aria-hidden="true">{patient.name.slice(0, 1)}</div>
      <div className="patient-context-profile">
        <div className="patient-context-title">
          <h1>{patient.name}</h1>
          <strong>({sex(patient.sex)} / {age(patient)})</strong>
          <span className={`patient-status is-${patient.status.toLowerCase()}`}>{patient.status}</span>
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
      <div><dt>진료과</dt><dd>-</dd></div>
      <div><dt>담당의</dt><dd>-</dd></div>
      <div><dt>최근 내원</dt><dd>-</dd></div>
      <div><dt>주진단</dt><dd>-</dd></div>
    </dl>
    <button className="patient-context-detail" type="button">상세 정보 <span aria-hidden="true">⌄</span></button>
  </header>;
}

function SummaryCards({ studies, consultations, onNavigate }: { studies: ImagingStudy[]; consultations: ConsultationListItem[]; onNavigate?: (destination: Destination) => void }) {
  const latest = studies[0]; const consultation = consultations[0];
  return <section className="patient-summary-grid"><article className="patient-summary-card"><header><span>♥</span><h3>Vital Sign</h3></header><div className="summary-empty"><strong>Vital API 미연결</strong><span>BP / HR / RR / BT 데이터가 없습니다.</span></div></article><article className="patient-summary-card"><header><span>▣</span><h3>최근 영상검사</h3><small>{latest ? dateTime(latest.study_at) : "-"}</small></header>{latest ? <div className="patient-recent-study-list">{studies.slice(0, 3).map((study) => <div key={study.id}><strong>{study.modality}</strong><span>{study.status}</span><time>{dateTime(study.study_at)}</time></div>)}</div> : <div className="summary-empty"><strong>검사 없음</strong><span>연결된 영상검사가 없습니다.</span></div>}<button type="button" onClick={() => onNavigate?.("imaging")}>검사 상세 보기 ›</button></article><article className="patient-summary-card"><header><span>♧</span><h3>협진 상태</h3><button type="button" onClick={() => onNavigate?.("consultations")}>더보기 ›</button></header>{consultation ? <dl><div><dt>협진 대상</dt><dd>{consultation.type}</dd></div><div><dt>상태</dt><dd>{consultation.ui_status}</dd></div><div><dt>우선순위</dt><dd>{consultation.priority}</dd></div></dl> : <div className="summary-empty"><strong>협진 없음</strong><span>조회 가능한 협진이 없습니다.</span></div>}</article></section>;
}

function Viewer({ studies, selected, onSelect, onOpen }: { studies: ImagingStudy[]; selected: ImagingStudy | null; onSelect: (id: string) => void; onOpen?: () => void }) {
  return <section className="patient-dashboard-card brain-viewer-card"><header className="patient-card-header is-dark"><h2>뇌 영상 Viewer</h2><div className="viewer-series-tabs">{studies.slice(0, 4).map((item) => <button key={item.id} type="button" className={selected?.id === item.id ? "is-active" : ""} onClick={() => onSelect(item.id)}>{item.modality}</button>)}</div></header><div className="brain-viewer-stage">{selected ? <div className="viewer-study-state"><div className="viewer-scan-placeholder"><span /><span /><span /></div><strong>{selected.modality} · {selected.series}</strong><p>실제 영상은 기존 영상 업무 Viewer에서 확인할 수 있습니다.</p><button type="button" onClick={onOpen}>전체화면 보기</button></div> : <div className="viewer-study-state is-empty"><strong>연결된 뇌 영상이 없습니다.</strong></div>}</div></section>;
}

function Analysis({ item, result, loading, error, onOpen }: { item: AIAnalysisItem | null; result: AIAnalysisResult | null; loading: boolean; error: string | null; onOpen?: () => void }) {
  const findings = result ? Object.entries(result.structured_findings).slice(0, 2) : [];
  return <section className="patient-dashboard-card ai-result-card"><header className="patient-card-header"><h2>AI 분석 결과</h2><small>{item ? dateTime(item.requested_at) : "-"}</small></header>{loading ? <div className="panel-empty-state">AI 결과를 불러오는 중입니다.</div> : error ? <div className="panel-empty-state is-error">{error}</div> : !item ? <div className="panel-empty-state"><strong>AI 분석 결과가 없습니다.</strong></div> : !result ? <div className="panel-empty-state"><strong>{analysisName(item.analysis_type)}</strong><span>현재 상태: {item.status}</span></div> : <div className="analysis-result-body"><dl className="analysis-metrics"><div><dt>분석 유형</dt><dd>{analysisName(item.analysis_type)}</dd></div><div><dt>Confidence</dt><dd>{Math.round(result.confidence * 100)}%</dd></div><div><dt>병변 개수</dt><dd>{result.lesion_count}</dd></div><div><dt>병변 총 부피</dt><dd>{result.total_volume_ml} mL</dd></div><div><dt>Severity</dt><dd>{result.severity || "-"}</dd></div><div><dt>추정 위치</dt><dd>{String(result.structured_findings.location ?? "-")}</dd></div></dl><div className="analysis-findings"><span>주요 소견</span>{findings.length ? findings.map(([key, value]) => <p key={key}><strong>{key.replaceAll("_", " ")}</strong> {typeof value === "object" ? JSON.stringify(value) : String(value)}</p>) : <p>구조화된 주요 소견이 없습니다.</p>}</div><button className="patient-panel-link" type="button" onClick={onOpen}>상세 결과 보기 ›</button></div>}</section>;
}

function Timeline({ events }: { events: TimelineEvent[] }) { return <section className="patient-dashboard-card timeline-card"><header className="patient-card-header"><h2>진료기록 / 경과</h2></header>{events.length ? <ol className="clinical-timeline">{events.map((event) => <li key={event.id} className={`is-${event.tone}`}><time>{dateTime(event.at)}</time><div><strong>{event.title}</strong><p>{event.detail}</p></div></li>)}</ol> : <div className="panel-empty-state"><strong>표시할 진료 경과가 없습니다.</strong><span>영상·AI·협진 이벤트가 시간순으로 표시됩니다.</span></div>}</section>; }
function Prescriptions({ onOpen }: { onOpen?: () => void }) { return <section className="patient-dashboard-card recent-prescriptions-card"><header className="patient-card-header"><h2>최근 처방</h2></header><div className="panel-empty-state"><strong>환자별 처방 목록 API 미연결</strong><span>약품명, 용량·투여경로, 횟수, 기간, 상태 데이터가 없습니다.</span></div><button className="patient-panel-link" type="button" onClick={onOpen}>처방 상세 보기 ›</button></section>; }

export default function PatientChart({ patient, patients = [], onSelectPatient, onNavigate, canViewAIAnalyses = false, canViewConsultations = false }: Props) {
  const [patientList, setPatientList] = useState<Patient[]>(patients); const [data, setData] = useState<ChartData>({ studies: [], analyses: [], consultations: [] });
  const [loading, setLoading] = useState(false); const [error, setError] = useState<string | null>(null); const [selectedStudyId, setSelectedStudyId] = useState<string | null>(null); const [analysisResults, setAnalysisResults] = useState<Record<string, AIAnalysisResult>>({}); const [analysisLoading, setAnalysisLoading] = useState(false); const clinicalRequestId = useRef(0); const analysisRequestId = useRef(0);
  const automaticPatientId = useRef<string | null>(null);

  useEffect(() => {
    const id = ++clinicalRequestId.current; setError(null); setLoading(true);
    const analyses = canViewAIAnalyses ? getAIAnalyses() : Promise.resolve({ count: 0, results: [] }); const consultations = canViewConsultations ? getConsultations() : Promise.resolve({ count: 0, results: [] });
    void Promise.allSettled([getPatients(), getImagingStudies(), analyses, consultations]).then(([people, imaging, ai, consult]) => { if (clinicalRequestId.current !== id) return; if (people.status === "fulfilled") setPatientList(people.value.results); setData({ studies: imaging.status === "fulfilled" ? imaging.value : [], analyses: ai.status === "fulfilled" ? ai.value.results : [], consultations: consult.status === "fulfilled" ? consult.value.results : [] }); if ([imaging, ai, consult].some((entry) => entry.status === "rejected")) setError("일부 임상 데이터를 불러오지 못했습니다."); setLoading(false); });
    return () => { if (clinicalRequestId.current === id) clinicalRequestId.current += 1; };
  }, [canViewAIAnalyses, canViewConsultations]);

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

  const studies = useMemo(() => patient ? data.studies.filter((item) => item.patient_id === patient.id).sort((a, b) => b.study_at.localeCompare(a.study_at)) : [], [data.studies, patient]);
  const studyIds = useMemo(() => new Set(studies.map((item) => item.id)), [studies]); const analyses = useMemo(() => data.analyses.filter((item) => studyIds.has(item.study_id)).sort((a, b) => b.requested_at.localeCompare(a.requested_at)), [data.analyses, studyIds]); const consultations = useMemo(() => patient ? data.consultations.filter((item) => item.patient_summary.id === patient.id).sort((a, b) => b.requested_at.localeCompare(a.requested_at)) : [], [data.consultations, patient]);
  const selectedStudy = studies.find((item) => item.id === selectedStudyId) ?? studies[0] ?? null; const selectedAnalysis = analyses[0] ?? null; const selectedAnalysisResult = selectedAnalysis ? analysisResults[selectedAnalysis.analysis_id] ?? null : null;
  useEffect(() => { const id = ++analysisRequestId.current; if (!selectedAnalysis || selectedAnalysis.status !== "COMPLETED" || analysisResults[selectedAnalysis.analysis_id]) { setAnalysisLoading(false); return; } setAnalysisLoading(true); getAIAnalysisResult(selectedAnalysis.analysis_id).then((value) => { if (analysisRequestId.current === id) setAnalysisResults((current) => ({ ...current, [value.analysis_id]: value })); }).catch(() => { if (analysisRequestId.current === id) setError("AI 상세 결과를 불러오지 못했습니다."); }).finally(() => { if (analysisRequestId.current === id) setAnalysisLoading(false); }); }, [selectedAnalysis?.analysis_id, selectedAnalysis?.status, analysisResults]);
  const events = useMemo<TimelineEvent[]>(() => [...studies.map((item) => ({ id: `study-${item.id}`, at: item.study_at, title: `${item.modality} 영상검사`, detail: `${item.series} · ${item.status}`, tone: "imaging" as const })), ...analyses.map((item) => ({ id: `ai-${item.analysis_id}`, at: item.requested_at, title: `${analysisName(item.analysis_type)} AI 분석`, detail: `${item.status} · ${item.stage}`, tone: "ai" as const })), ...consultations.map((item) => ({ id: `consult-${item.consultation_id}`, at: item.requested_at, title: `${item.type} 협진 요청`, detail: `${item.ui_status} · ${item.priority}`, tone: "consultation" as const }))].sort((a, b) => b.at.localeCompare(a.at)), [studies, analyses, consultations]);

  function selectPatient(nextPatient: Patient) { setSelectedStudyId(null); setError(null); onSelectPatient?.(nextPatient); }
  return <section className="patient-context-dashboard">
    <div className="patient-workspace">
      <PatientRail selectedId={patient?.id ?? null} patients={patientList.length ? patientList : patients} onSelect={selectPatient} />
      {patient && <PatientHeader patient={patient} />}
      {patient ? <main className="patient-context-main">
        {error && <div className="patient-data-warning">{error}</div>}
        <SummaryCards studies={studies} consultations={consultations} onNavigate={onNavigate} />
        <div className="patient-clinical-focus">{loading ? <div className="patient-chart-loading">환자 임상 데이터를 불러오는 중입니다.</div> : <><Viewer studies={studies} selected={selectedStudy} onSelect={setSelectedStudyId} onOpen={() => onNavigate?.("imaging")} /><Analysis item={selectedAnalysis} result={selectedAnalysisResult} loading={analysisLoading} error={null} onOpen={() => onNavigate?.("ai-results")} /></>}</div>
      </main> : <main className="patient-context-main patient-context-main--empty"><div className="patient-selection-empty"><strong>선택된 환자가 없습니다.</strong><span>왼쪽 환자 목록에서 환자를 선택해 주세요.</span></div></main>}
    </div>
    <aside className="patient-context-aside"><Timeline events={patient ? events : []} /><Prescriptions onOpen={() => onNavigate?.("prescriptions")} /></aside>
  </section>;
}
