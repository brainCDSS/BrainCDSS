import { lazy, Suspense, useCallback, useEffect, useMemo, useState } from "react";
import { createAIResultReview, getAIAnalyses, getAIAnalysis, getAIAnalysisResult } from "./api";
import { getImagingStudy } from "../imaging/api";
import type { ImagingStudyDetail } from "../imaging/types";
import type { AIAnalysisItem, AIAnalysisResult, NiftiProbe } from "./types";
import "./ai-analysis.css";

const NiftiViewer = lazy(() => import("./NiftiViewer"));
const TERMINAL = new Set(["COMPLETED", "FAILED", "CANCELLED"]);
const STATUS: Record<string, string> = { QUEUED: "분석 대기", PROCESSING: "분석 중", COMPLETED: "분석 완료", FAILED: "분석 실패", RETRYING: "재시도 중", CANCELLED: "분석 취소" };
const ANALYSIS: Record<string, string> = { HEMORRHAGIC_STROKE_CT: "CT 뇌출혈 분석", ISCHEMIC_STROKE_DWI_ADC: "MRI 허혈성 뇌졸중 분석", CEREBRAL_ANEURYSM_MRA: "MRA 뇌동맥류 분석" };
const formatDate = (value?: string | null) => value ? new Date(value).toLocaleString("ko-KR") : "미확인";
const volume = (value?: number | null) => value == null ? "미산출" : `${Number(value).toFixed(2)} mL`;
function findingLabel(type: string | undefined, positive: boolean | null | undefined) {
  if (positive == null) return "검출 결과 미산출";
  const target = type === "HEMORRHAGIC_STROKE_CT" ? "출혈 의심 영역" : type === "ISCHEMIC_STROKE_DWI_ADC" ? "허혈성 병변 의심 영역" : type === "CEREBRAL_ANEURYSM_MRA" ? "뇌동맥류 의심 영역" : "병변 의심 영역";
  return `${target} ${positive ? "검출" : "미검출"}`;
}

interface Props { initialAnalysisId?: string | null }
interface Lesion { id?: string | number; volume_ml?: number; representative_slice?: number; prediction_score?: number; relative_volume_pct?: number; location?: string; description?: string; max_diameter_mm?: number }

export default function AIAnalysisResultsPage({ initialAnalysisId }: Props) {
  const [items, setItems] = useState<AIAnalysisItem[]>([]);
  const [selected, setSelected] = useState<AIAnalysisItem | null>(null);
  const [result, setResult] = useState<AIAnalysisResult | null>(null);
  const [study, setStudy] = useState<ImagingStudyDetail | null>(null);
  const [patientUnlinked, setPatientUnlinked] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [opinion, setOpinion] = useState("");
  const [reviewDecision, setReviewDecision] = useState<"ACCEPT" | "MODIFY" | "REJECT">("ACCEPT");
  const [actionBusy, setActionBusy] = useState(false);
  const [reviewMessage, setReviewMessage] = useState<string | null>(null);
  const [selectedLesion, setSelectedLesion] = useState<number | null>(null);
  const [focusRequest, setFocusRequest] = useState(0);
  const [studyIndex, setStudyIndex] = useState<Record<string, ImagingStudyDetail>>({});
  const [patientQuery, setPatientQuery] = useState("");
  const [listCollapsed, setListCollapsed] = useState(false);
  const [probe, setProbe] = useState<NiftiProbe | null>(null);

  const load = useCallback(async () => {
    setLoading(true); setError(null);
    try {
      const response = await getAIAnalyses();
      setItems(response.results);
      const listed = response.results.find((item) => item.analysis_id === initialAnalysisId);
      if (initialAnalysisId && !listed) {
        try { const detail = await getAIAnalysis(initialAnalysisId); setItems((rows) => [detail, ...rows]); setSelected(detail); }
        catch { setSelected(response.results[0] ?? null); }
      } else setSelected((current) => response.results.find((item) => item.analysis_id === current?.analysis_id) ?? listed ?? response.results[0] ?? null);
    } catch { setError("AI 분석 목록을 불러오지 못했습니다."); setItems([]); setSelected(null); }
    finally { setLoading(false); }
  }, [initialAnalysisId]);

  useEffect(() => { void load(); }, [load]);
  useEffect(() => {
    let active = true;
    const missingStudyIds = [...new Set(items.map((item) => item.study_id))]
      .filter((studyId) => !studyIndex[studyId]);
    if (!missingStudyIds.length) return () => { active = false; };
    void Promise.allSettled(missingStudyIds.map(async (studyId) => {
      const detail = await getImagingStudy(studyId);
      return [studyId, detail] as const;
    })).then((settled) => {
      if (!active) return;
      setStudyIndex((current) => {
        const next = { ...current };
        settled.forEach((entry) => {
          if (entry.status === "fulfilled") next[entry.value[0]] = entry.value[1];
        });
        return next;
      });
    });
    return () => { active = false; };
  }, [items]);
  useEffect(() => {
    if (!selected || TERMINAL.has(selected.status)) return;
    let active = true; let timer: ReturnType<typeof setTimeout>;
    const poll = async () => {
      try {
        const detail = await getAIAnalysis(selected.analysis_id); if (!active) return;
        setSelected(detail); setItems((rows) => rows.map((row) => row.analysis_id === detail.analysis_id ? detail : row));
        if (!TERMINAL.has(detail.status)) timer = setTimeout(poll, 2000);
      } catch { if (active) timer = setTimeout(poll, 4000); }
    };
    timer = setTimeout(poll, 800); return () => { active = false; clearTimeout(timer); };
  }, [selected?.analysis_id, selected?.status]);

  useEffect(() => {
    let active = true;
    setResult(null); setStudy(null); setPatientUnlinked(false); setReviewMessage(null); setSelectedLesion(null); setProbe(null);
    if (!selected) return () => { active = false; };
    void getImagingStudy(selected.study_id).then((data) => { if (active) { setStudy(data); setPatientUnlinked(!data.patient); } }).catch(() => { if (active) setPatientUnlinked(true); });
    if (selected.status === "COMPLETED") void getAIAnalysisResult(selected.analysis_id).then((data) => { if (active) setResult(data); }).catch(() => { if (active) setError("완료된 분석 결과를 불러오지 못했습니다."); });
    return () => { active = false; };
  }, [selected?.analysis_id, selected?.status]);

  const findings = result?.structured_findings as { lesions?: unknown; metrics?: { lesions?: unknown } } | undefined;
  const rawLesions = findings?.lesions ?? findings?.metrics?.lesions;
  const lesions: Lesion[] = Array.isArray(rawLesions) ? rawLesions.filter((item): item is Lesion => typeof item === "object" && item !== null) : [];
  const findingText = findingLabel(selected?.analysis_type, result?.is_positive);
  const largestLesionIndex = useMemo(() => {
    let largest = -1;
    lesions.forEach((lesion, index) => {
      if (lesion.representative_slice == null) return;
      if (largest < 0 || (lesion.volume_ml ?? -1) > (lesions[largest].volume_ml ?? -1)) largest = index;
    });
    return largest;
  }, [lesions]);

  async function saveReview() {
    if (!result || !opinion.trim()) return;
    setActionBusy(true); setReviewMessage(null);
    try { await createAIResultReview(result.result_id, { decision: reviewDecision, comment: opinion.trim() }); setOpinion(""); setResult(await getAIAnalysisResult(result.analysis_id)); setReviewMessage("검토가 저장되었습니다."); }
    catch { setReviewMessage("검토 저장에 실패했습니다."); }
    finally { setActionBusy(false); }
  }

  const patient = study?.patient;
  const normalizedQuery = patientQuery.trim().toLocaleLowerCase("ko-KR");
  const visibleItems = items.filter((item) => {
    if (!normalizedQuery) return true;
    const indexedStudy = studyIndex[item.study_id];
    const indexedPatient = indexedStudy?.patient;
    return [indexedPatient?.name, indexedPatient?.patient_no, indexedStudy?.accession_number, ANALYSIS[item.analysis_type], item.analysis_type]
      .some((value) => String(value ?? "").toLocaleLowerCase("ko-KR").includes(normalizedQuery));
  });
  return <section className="ai-workspace-page clinical-ai-results">
    <header className="ai-workspace-heading compact"><div><h2>AI 분석 결과</h2><p>AI가 생성한 병변 분할과 정량 결과를 검토합니다.</p></div><div className="ai-workspace-filter"><label>분석 선택<select value={selected?.analysis_id ?? ""} onChange={(event) => setSelected(items.find((item) => item.analysis_id === event.target.value) ?? null)} disabled={loading}>{items.map((item) => <option key={item.analysis_id} value={item.analysis_id}>{ANALYSIS[item.analysis_type] ?? item.analysis_type} · {formatDate(item.requested_at)}</option>)}</select></label><button type="button" onClick={() => void load()}>새로고침</button></div></header>
    {error && <div className="ai-page-error">{error}</div>}
    <section className="ai-context-card compact">
      {patient ? <dl><div><dt>환자번호</dt><dd>{patient.patient_no || "미확인"}</dd></div><div><dt>환자명</dt><dd>{patient.name || "미확인"}</dd></div><div><dt>성별 / 나이</dt><dd>{patient.sex || "미확인"} / {patient.estimated_age ?? "미확인"}</dd></div><div><dt>생년월일</dt><dd>{patient.birth_date || "미확인"}</dd></div><div><dt>검사일시</dt><dd>{formatDate(study?.study_datetime)}</dd></div><div><dt>검사번호</dt><dd>{study?.accession_number || "미확인"}</dd></div></dl> : patientUnlinked ? <div className="patient-unlinked">환자 정보 미연결 · 검사 및 분석 결과는 정상 조회되었습니다.</div> : <div className="patient-unlinked">검사 정보를 불러오는 중입니다.</div>}
    </section>

    {selected && !TERMINAL.has(selected.status) && <section className="ai-running-card"><div className="ai-running-spinner"/><div><strong>{STATUS[selected.status] ?? "분석 중"}</strong><span>{selected.stage || "요청 준비"}</span></div><div className="ai-analysis-progress"/></section>}

    <div className={`ai-results-main-layout${listCollapsed ? " is-list-collapsed" : ""}`}>
      <aside className="ai-result-patient-list" aria-label="환자별 AI 분석 결과 목록">
        <header><strong>환자 결과</strong><span>{items.length}</span><button type="button" onClick={() => setListCollapsed(true)} aria-label="환자 결과 목록 접기">‹</button></header>
        <label className="ai-result-patient-search"><span className="sr-only">환자 결과 검색</span><input value={patientQuery} onChange={(event) => setPatientQuery(event.target.value)} placeholder="이름, 환자번호, 검사번호 검색" /></label>
        <div className="ai-result-patient-scroll">
          {visibleItems.map((item) => {
            const indexedStudy = studyIndex[item.study_id];
            const indexedPatient = indexedStudy?.patient;
            return <button type="button" key={item.analysis_id} className={selected?.analysis_id === item.analysis_id ? "is-selected" : ""} onClick={() => setSelected(item)}>
              <span className="patient-result-heading"><strong>{indexedPatient?.name || "환자 정보 미연결"}</strong><em className={`is-${item.status.toLowerCase()}`}>{STATUS[item.status] ?? item.status}</em></span>
              <span>{indexedPatient?.patient_no || indexedStudy?.accession_number || "검사 식별정보 없음"}</span>
              <span>{ANALYSIS[item.analysis_type] ?? item.analysis_type}</span>
              <time>{formatDate(item.requested_at)}</time>
            </button>;
          })}
          {!visibleItems.length && <div className="ai-result-patient-empty">검색 결과가 없습니다.</div>}
        </div>
      </aside>
      {listCollapsed && <button type="button" className="ai-result-list-opener" onClick={() => setListCollapsed(false)}>환자 결과 <span>{items.length}</span> ›</button>}
      <div className="ai-workspace-body">
      <main className="ai-workspace-primary">{selected?.status === "COMPLETED" ? <Suspense fallback={<div className="nifti-viewer__message">뷰어 준비 중</div>}><NiftiViewer key={selected.analysis_id} analysisId={selected.analysis_id} focusSlice={selectedLesion == null ? null : lesions[selectedLesion]?.representative_slice} focusRequest={focusRequest} onProbe={setProbe}/></Suspense> : <section className="ai-viewer-card ai-viewer-empty"><strong>{selected ? "분석 결과를 기다리는 중입니다." : "분석을 선택하세요."}</strong></section>}</main>
      <aside className="ai-workspace-secondary clinical-result-panel clinical-result-overview">
        <div className="result-overview-body">
          <section className="clinical-summary">
            <div className="summary-status"><div><span>AI 분석 소견</span><strong>{result ? findingText : selected ? STATUS[selected.status] : "분석 없음"}</strong></div><span className={`ai-status-badge is-${(selected?.status ?? "unknown").toLowerCase()}`}>{selected ? STATUS[selected.status] : "미확인"}</span></div>
            <dl><div><dt>분석 유형</dt><dd>{selected ? ANALYSIS[selected.analysis_type] ?? selected.analysis_type : "미확인"}</dd></div><div><dt>총 병변 부피</dt><dd>{volume(result?.total_volume_ml)}</dd></div><div><dt>예측 점수</dt><dd>{result?.confidence == null ? "미산출" : result.confidence}</dd></div><div><dt>검사일시</dt><dd>{formatDate(study?.study_datetime)}</dd></div><div><dt>분석 완료</dt><dd>{formatDate(selected?.completed_at)}</dd></div><div><dt>모델 버전</dt><dd>{selected?.model ? `${selected.model.code} ${selected.model.version}` : "미확인"}</dd></div></dl>
          </section>
          <section className="voxel-probe"><header>선택 위치 정보</header>{probe ? <dl><div><dt>Voxel</dt><dd>{probe.voxel.join(", ")}</dd></div><div><dt>슬라이스</dt><dd>{probe.slice}</dd></div><div><dt>{probe.sourceRole}</dt><dd>{probe.sourceValue == null ? "미산출" : probe.sourceRole === "CT" ? `${probe.sourceValue.toFixed(1)} HU` : probe.sourceValue.toFixed(3)}</dd></div>{probe.dwiValue != null && <div><dt>DWI</dt><dd>{probe.dwiValue.toFixed(3)}</dd></div>}{probe.adcValue != null && <div><dt>ADC</dt><dd>{probe.adcValue.toFixed(3)}</dd></div>}<div><dt>AI 병변 가능도</dt><dd>{probe.probability == null ? "미산출" : `${(probe.probability * 100).toFixed(1)} %`}</dd></div><div><dt>AI 분할</dt><dd>{probe.maskValue == null ? "미산출" : probe.maskValue > 0 ? "병변" : "배경"}</dd></div><div><dt>XAI</dt><dd>{probe.xaiValue == null ? "미생성" : probe.xaiValue.toFixed(3)}</dd></div></dl> : <p>영상에서 위치를 클릭하면 AI 분석 값을 확인할 수 있습니다.</p>}</section>
          <section className="lesion-overview">
            <header><div><span>병변 설명</span><strong>{lesions.length ? `병변 ${lesions.length}개` : "병변별 정보 미생성"}</strong></div>{largestLesionIndex >= 0 && <button type="button" onClick={() => { setSelectedLesion(largestLesionIndex); setFocusRequest((current) => current + 1); }}>최대 병변으로 이동</button>}</header>
            {lesions.length ? <div className="lesion-list">{lesions.map((lesion,index) => <button type="button" key={String(lesion.id ?? index)} className={selectedLesion === index ? "is-selected" : ""} disabled={lesion.representative_slice == null} onClick={() => { setSelectedLesion(index); setFocusRequest((current) => current + 1); }}><strong>병변 {index + 1}{index === largestLesionIndex ? " · 최대" : ""}</strong>{lesion.description && <em>{lesion.description}</em>}{lesion.location && <span>위치 {lesion.location}</span>}<span>부피 {volume(lesion.volume_ml)}</span><span>총 병변의 {lesion.relative_volume_pct == null ? "미산출" : `${Number(lesion.relative_volume_pct).toFixed(1)}%`}</span><span>대표 슬라이스 {lesion.representative_slice ?? "미산출"}</span><span>예측 점수 {lesion.prediction_score == null ? "미산출" : lesion.prediction_score}</span>{lesion.max_diameter_mm != null && <span>최대 직경 {Number(lesion.max_diameter_mm).toFixed(1)} mm</span>}</button>)}</div> : <div className="lesion-explanation"><strong>{findingText}</strong><p>{result?.total_volume_ml == null ? "병변의 개수, 위치, 대표 슬라이스 정보가 아직 산출되지 않았습니다." : `AI 분할 결과의 총 병변 부피는 ${volume(result.total_volume_ml)}입니다. 병변별 위치와 대표 슬라이스는 새 분석부터 표시합니다.`}</p><small>빨간 마스크는 AI가 분할한 의심 영역이며, 최종 판단은 의료진 검토가 필요합니다.</small></div>}
          </section>
        </div>
        <section className="review-panel review-panel-embedded"><div className="review-state"><span>검토 상태</span><strong>{result?.latest_review?.decision ?? "미검토"}</strong></div><label>의료진 소견<textarea value={opinion} onChange={(e) => setOpinion(e.target.value)} placeholder="AI 결과에 대한 소견을 입력하세요." /></label><label>검토 결정<select value={reviewDecision} onChange={(e) => setReviewDecision(e.target.value as typeof reviewDecision)}><option value="ACCEPT">수용</option><option value="MODIFY">수정 필요</option><option value="REJECT">거절</option></select></label>{reviewMessage && <p>{reviewMessage}</p>}<div className="review-actions"><button type="button" disabled={actionBusy || !result || !opinion.trim()} onClick={() => void saveReview()}>소견 저장</button><button type="button" disabled title="판독 API 미연결">판독 작성</button><button type="button" disabled title="협진 API 미연결">협진 공유</button></div></section>
      </aside>
      </div>
    </div>
  </section>;
}
