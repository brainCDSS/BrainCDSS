import { lazy, Suspense, useCallback, useEffect, useState } from "react";
import { cancelAIAnalysis, createAIResultReview, getAIAnalyses, getAIAnalysis, getAIAnalysisResult } from "./api";
import { getImagingStudy } from "../imaging/api";
import type { ImagingStudyDetail } from "../imaging/types";
import type { AIAnalysisItem, AIAnalysisResult } from "./types";
import "./ai-analysis.css";

const NiftiViewer = lazy(() => import("./NiftiViewer"));
type ResultTab = "SUMMARY" | "LESIONS" | "XAI" | "REVIEW";
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
interface Lesion { id?: string | number; volume_ml?: number; representative_slice?: number; prediction_score?: number }

export default function AIAnalysisResultsPage({ initialAnalysisId }: Props) {
  const [items, setItems] = useState<AIAnalysisItem[]>([]);
  const [selected, setSelected] = useState<AIAnalysisItem | null>(null);
  const [result, setResult] = useState<AIAnalysisResult | null>(null);
  const [study, setStudy] = useState<ImagingStudyDetail | null>(null);
  const [patientUnlinked, setPatientUnlinked] = useState(false);
  const [tab, setTab] = useState<ResultTab>("SUMMARY");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [opinion, setOpinion] = useState("");
  const [reviewDecision, setReviewDecision] = useState<"ACCEPT" | "MODIFY" | "REJECT">("ACCEPT");
  const [actionBusy, setActionBusy] = useState(false);
  const [reviewMessage, setReviewMessage] = useState<string | null>(null);
  const [selectedLesion, setSelectedLesion] = useState<number | null>(null);

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
    setResult(null); setStudy(null); setPatientUnlinked(false); setTab("SUMMARY"); setReviewMessage(null); setSelectedLesion(null);
    if (!selected) return () => { active = false; };
    void getImagingStudy(selected.study_id).then((data) => { if (active) { setStudy(data); setPatientUnlinked(!data.patient); } }).catch(() => { if (active) setPatientUnlinked(true); });
    if (selected.status === "COMPLETED") void getAIAnalysisResult(selected.analysis_id).then((data) => { if (active) setResult(data); }).catch(() => { if (active) setError("완료된 분석 결과를 불러오지 못했습니다."); });
    return () => { active = false; };
  }, [selected?.analysis_id, selected?.status]);

  const rawLesions = result?.structured_findings?.lesions;
  const lesions: Lesion[] = Array.isArray(rawLesions) ? rawLesions.filter((item): item is Lesion => typeof item === "object" && item !== null) : [];
  const xaiArtifacts = result?.artifacts.filter((item) => ["ATTENTION_MAP", "SALIENCY_MAP", "UNCERTAINTY_MAP"].includes(item.type)) ?? [];
  const findingText = findingLabel(selected?.analysis_type, result?.is_positive);

  async function saveReview() {
    if (!result || !opinion.trim()) return;
    setActionBusy(true); setReviewMessage(null);
    try { await createAIResultReview(result.result_id, { decision: reviewDecision, comment: opinion.trim() }); setOpinion(""); setResult(await getAIAnalysisResult(result.analysis_id)); setReviewMessage("검토가 저장되었습니다."); }
    catch { setReviewMessage("검토 저장에 실패했습니다."); }
    finally { setActionBusy(false); }
  }

  const patient = study?.patient;
  return <section className="ai-workspace-page clinical-ai-results">
    <header className="ai-workspace-heading compact"><div><h2>AI 분석 결과</h2><p>AI가 생성한 병변 분할과 정량 결과를 검토합니다.</p></div><div className="ai-workspace-filter"><label>분석 선택<select value={selected?.analysis_id ?? ""} onChange={(event) => setSelected(items.find((item) => item.analysis_id === event.target.value) ?? null)} disabled={loading}>{items.map((item) => <option key={item.analysis_id} value={item.analysis_id}>{ANALYSIS[item.analysis_type] ?? item.analysis_type} · {formatDate(item.requested_at)}</option>)}</select></label><button type="button" onClick={() => void load()}>새로고침</button></div></header>
    {error && <div className="ai-page-error">{error}</div>}
    <section className="ai-context-card compact">
      {patient ? <dl><div><dt>환자번호</dt><dd>{patient.patient_no || "미확인"}</dd></div><div><dt>환자명</dt><dd>{patient.name || "미확인"}</dd></div><div><dt>성별 / 나이</dt><dd>{patient.sex || "미확인"} / {patient.estimated_age ?? "미확인"}</dd></div><div><dt>생년월일</dt><dd>{patient.birth_date || "미확인"}</dd></div><div><dt>검사일시</dt><dd>{formatDate(study?.study_datetime)}</dd></div><div><dt>검사번호</dt><dd>{study?.accession_number || "미확인"}</dd></div></dl> : patientUnlinked ? <div className="patient-unlinked">환자 정보 미연결 · 검사 및 분석 결과는 정상 조회되었습니다.</div> : <div className="patient-unlinked">검사 정보를 불러오는 중입니다.</div>}
    </section>

    {selected && !TERMINAL.has(selected.status) && <section className="ai-running-card"><div className="ai-running-spinner"/><div><strong>{STATUS[selected.status] ?? "분석 중"}</strong><span>{selected.stage || "요청 준비"}</span></div><div className="ai-analysis-progress"/></section>}

    <div className="ai-workspace-body">
      <main className="ai-workspace-primary">{selected?.status === "COMPLETED" ? <Suspense fallback={<div className="nifti-viewer__message">뷰어 준비 중</div>}><NiftiViewer key={selected.analysis_id} analysisId={selected.analysis_id} focusSlice={selectedLesion == null ? null : lesions[selectedLesion]?.representative_slice}/></Suspense> : <section className="ai-viewer-card ai-viewer-empty"><strong>{selected ? "분석 결과를 기다리는 중입니다." : "분석을 선택하세요."}</strong></section>}</main>
      <aside className="ai-workspace-secondary clinical-result-panel">
        <nav className="result-tabs">{([['SUMMARY','요약'],['LESIONS','병변'],['XAI','XAI'],['REVIEW','검토']] as Array<[ResultTab,string]>).map(([id,label]) => <button type="button" key={id} className={tab === id ? "is-active" : ""} onClick={() => setTab(id)}>{label}</button>)}</nav>
        <div className="result-tab-body">
          {tab === "SUMMARY" && <section className="clinical-summary">
            <div className="summary-status"><div><span>AI 분석 소견</span><strong>{result ? findingText : selected ? STATUS[selected.status] : "분석 없음"}</strong></div><span className={`ai-status-badge is-${(selected?.status ?? "unknown").toLowerCase()}`}>{selected ? STATUS[selected.status] : "미확인"}</span></div>
            <dl><div><dt>분석 유형</dt><dd>{selected ? ANALYSIS[selected.analysis_type] ?? selected.analysis_type : "미확인"}</dd></div><div><dt>총 병변 부피</dt><dd>{volume(result?.total_volume_ml)}</dd></div><div><dt>예측 점수</dt><dd>{result?.confidence == null ? "미산출" : result.confidence}</dd></div><div><dt>검사일시</dt><dd>{formatDate(study?.study_datetime)}</dd></div><div><dt>분석 완료</dt><dd>{formatDate(selected?.completed_at)}</dd></div><div><dt>모델 버전</dt><dd>{selected?.model ? `${selected.model.code} ${selected.model.version}` : "미확인"}</dd></div></dl>
            {result && <details className="technical-details"><summary>기술 상세</summary><pre>{JSON.stringify(result.structured_findings, null, 2)}</pre></details>}
          </section>}
          {tab === "LESIONS" && <section className="lesion-panel">{lesions.length ? lesions.map((lesion,index) => <button type="button" key={String(lesion.id ?? index)} className={selectedLesion === index ? "is-selected" : ""} disabled={lesion.representative_slice == null} onClick={() => setSelectedLesion(index)}><strong>병변 {index + 1}</strong><span>부피 {volume(lesion.volume_ml)}</span><span>대표 슬라이스 {lesion.representative_slice ?? "미산출"}</span><span>예측 점수 {lesion.prediction_score ?? "미산출"}</span></button>) : <div className="tab-empty"><strong>병변별 데이터 미생성</strong><span>{result?.total_volume_ml == null ? "병변별·총부피 정보가 없습니다." : `현재 결과에는 총부피 ${volume(result.total_volume_ml)}만 있습니다.`}</span></div>}</section>}
          {tab === "XAI" && <section className="xai-panel">{xaiArtifacts.length ? xaiArtifacts.map((artifact) => <div key={artifact.artifact_id ?? artifact.type}><strong>{artifact.type}</strong><span>생성 완료</span></div>) : <div className="tab-empty"><strong>XAI 미생성</strong><span>분할 마스크는 표시 중이지만 XAI 결과로 간주하지 않습니다.</span></div>}</section>}
          {tab === "REVIEW" && <section className="review-panel"><div className="review-state"><span>현재 검토 상태</span><strong>{result?.latest_review?.decision ?? "미검토"}</strong></div><label>검토 결정<select value={reviewDecision} onChange={(e) => setReviewDecision(e.target.value as typeof reviewDecision)}><option value="ACCEPT">수용</option><option value="MODIFY">수정 필요</option><option value="REJECT">거절</option></select></label><label>의료진 소견<textarea value={opinion} onChange={(e) => setOpinion(e.target.value)} placeholder="AI 결과에 대한 소견을 입력하세요." /></label>{reviewMessage && <p>{reviewMessage}</p>}<div className="review-actions"><button type="button" disabled={actionBusy || !result || !opinion.trim()} onClick={() => void saveReview()}>검토 저장</button><button type="button" disabled title="판독 API 미연결">판독 작성</button><button type="button" disabled title="협진 API 미연결">협진 공유</button>{selected?.status === "QUEUED" && <button type="button" onClick={() => void cancelAIAnalysis(selected.analysis_id, "사용자 취소")}>분석 취소</button>}</div></section>}
        </div>
      </aside>
    </div>
  </section>;
}
