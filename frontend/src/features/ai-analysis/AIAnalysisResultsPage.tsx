import { lazy, Suspense, useCallback, useEffect, useMemo, useState } from "react";
import { cancelAIAnalysis, createAIResultReview, getAIAnalyses, getAIAnalysis, getAIAnalysisResult } from "./api";
import { createViewerSession, getViewerContext } from "../imaging/api";
import type { AIAnalysisItem, AIAnalysisResult } from "./types";
import "./ai-analysis.css";

const NiftiViewer = lazy(() => import("./NiftiViewer"));

const STATUSES = ["", "QUEUED", "PROCESSING", "COMPLETED", "FAILED", "RETRYING", "CANCELLED"];
const STATUS_LABELS: Record<string, string> = { QUEUED: "분석 대기", PROCESSING: "분석 중", COMPLETED: "분석 완료", FAILED: "분석 실패", RETRYING: "재시도 중", CANCELLED: "분석 취소" };
const VIEWER_TOOLS = ["WL/WW", "확대", "이동", "측정", "십자선", "비교", "CINE", "AI 오버레이", "XAI", "초기화"];
const formatDate = (value?: string | null) => { if (!value) return "데이터 없음"; const date = new Date(value); return Number.isNaN(date.getTime()) ? value : date.toLocaleString("ko-KR"); };
const formatValue = (value: unknown) => value === null || value === undefined || value === "" ? "데이터 없음" : typeof value === "object" ? JSON.stringify(value) : String(value);

export default function AIAnalysisResultsPage() {
  const [items, setItems] = useState<AIAnalysisItem[]>([]);
  const [status, setStatus] = useState("");
  const [selected, setSelected] = useState<AIAnalysisItem | null>(null);
  const [result, setResult] = useState<AIAnalysisResult | null>(null);
  const [opinion, setOpinion] = useState("");
  const [loading, setLoading] = useState(true);
  const [detailLoading, setDetailLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [detailError, setDetailError] = useState<string | null>(null);
  const [viewerUrl, setViewerUrl] = useState<string | null>(null);
  const [reviewDecision, setReviewDecision] = useState<"ACCEPT" | "REJECT">("ACCEPT");
  const [actionBusy, setActionBusy] = useState(false);

  const load = useCallback(async () => {
    setLoading(true); setError(null);
    try {
      const response = await getAIAnalyses(status);
      setItems(response.results);
      setSelected((current) => response.results.find((item) => item.analysis_id === current?.analysis_id) ?? response.results[0] ?? null);
    } catch {
      setItems([]); setSelected(null); setResult(null); setError("AI 분석 정보를 불러오지 못했습니다.");
    } finally { setLoading(false); }
  }, [status]);

  useEffect(() => { void load(); }, [load]);
  useEffect(() => {
    setResult(null); setDetailError(null);
    if (!selected || selected.status !== "COMPLETED") return;
    let active = true;
    setDetailLoading(true);
    getAIAnalysisResult(selected.analysis_id).then((response) => { if (active) setResult(response); }).catch(() => { if (active) setDetailError("선택한 AI 분석 결과를 불러오지 못했습니다."); }).finally(() => { if (active) setDetailLoading(false); });
    return () => { active = false; };
  }, [selected]);

  useEffect(() => {
    if (!selected) return;
    let active = true;
    Promise.all([getAIAnalysis(selected.analysis_id), getViewerContext(selected.study_id)])
      .then(([detail, context]) => { if (active) { setSelected((current) => current?.analysis_id === detail.analysis_id ? { ...current, ...detail } : current); const session = context.viewer_session as { viewer_url?: string }; setViewerUrl(session.viewer_url ?? null); } })
      .catch(() => { if (active) setViewerUrl(null); });
    return () => { active = false; };
  }, [selected?.analysis_id, selected?.study_id]);

  async function openViewer() {
    if (!selected) return;
    setActionBusy(true); setDetailError(null);
    try { const session = await createViewerSession(selected.study_id, { purpose: "DIAGNOSIS", include_ai_overlay: true }); const url = session.viewer_url; if (!url) throw new Error("viewer URL missing"); setViewerUrl(url); globalThis.open(url, "_blank", "noopener,noreferrer"); }
    catch { setDetailError("Viewer Session을 발급받지 못했습니다."); }
    finally { setActionBusy(false); }
  }
  async function cancelSelected() {
    if (!selected || selected.status !== "QUEUED") return;
    const reason = globalThis.prompt("분석 취소 사유를 입력해 주세요.")?.trim(); if (!reason) return;
    setActionBusy(true); setDetailError(null);
    try { await cancelAIAnalysis(selected.analysis_id, reason); await load(); } catch { setDetailError("AI 분석 취소에 실패했습니다."); } finally { setActionBusy(false); }
  }
  async function saveReview() {
    if (!result || !opinion.trim()) return;
    setActionBusy(true); setDetailError(null);
    try { await createAIResultReview(result.result_id, { decision: reviewDecision, comment: opinion.trim() }); setOpinion(""); setResult(await getAIAnalysisResult(result.analysis_id)); }
    catch { setDetailError("AI 결과 검토 저장에 실패했습니다."); } finally { setActionBusy(false); }
  }

  const findings = useMemo(() => result ? Object.entries(result.structured_findings) : [], [result]);
  const contextFields = [
    ["환자 ID", "연동 필요"], ["환자명", "연동 필요"], ["성별/나이", "연동 필요"], ["생년월일", "연동 필요"],
    ["검사일시", "연동 필요"], ["진료과", "연동 필요"], ["검사명", "연동 필요"], ["Acc. No.", "연동 필요"], ["응급 환자", "연동 필요"],
  ];

  return <section className="ai-workspace-page">
    <header className="ai-workspace-heading"><div><h2>AI 분석 결과</h2><p>영상 AI 분석의 진행 상황과 완료 결과를 확인합니다.</p></div><div className="ai-workspace-filter"><label>분석 선택<select value={selected?.analysis_id ?? ""} onChange={(event) => setSelected(items.find((item) => item.analysis_id === event.target.value) ?? null)} disabled={loading || items.length === 0}><option value="">분석 데이터 없음</option>{items.map((item) => <option key={item.analysis_id} value={item.analysis_id}>{item.analysis_type} · {formatDate(item.requested_at)}</option>)}</select></label><label>상태<select value={status} onChange={(event) => setStatus(event.target.value)}>{STATUSES.map((value) => <option key={value || "ALL"} value={value}>{value ? STATUS_LABELS[value] ?? value : "전체"}</option>)}</select></label><button type="button" onClick={() => void load()} disabled={loading}>새로고침</button></div></header>
    {error && <div className="ai-page-error" role="alert">{error}</div>}

    <section className="ai-context-card" aria-label="환자 및 검사 Context"><dl>{contextFields.map(([label, value]) => <div key={label}><dt>{label}</dt><dd className="is-unavailable">{value}</dd></div>)}</dl></section>

    <div className="ai-workspace-body">
      <div className="ai-workspace-primary">
        <section className="ai-viewer-card"><header><div><span>MEDICAL IMAGING</span><h3>Brain MRI Viewer</h3></div><button type="button" disabled={!selected || actionBusy} onClick={() => void openViewer()}>{viewerUrl ? "Viewer 열기" : "Viewer Session 발급"}</button></header><div className="ai-viewer-toolbar" aria-label="Viewer 도구">{VIEWER_TOOLS.map((tool) => <button key={tool} type="button" disabled className={tool === "AI 오버레이" ? "is-highlighted" : ""}>{tool}</button>)}</div><div className="ai-viewer-empty"><div className="ai-viewer-empty__icon" aria-hidden="true">◇</div><strong>{viewerUrl ? "Viewer 준비 완료" : "Viewer Session이 필요합니다."}</strong><p>{viewerUrl ? "발급된 보안 Viewer를 새 창에서 열 수 있습니다." : "선택한 Study의 Viewer Context와 Session을 사용합니다."}</p></div></section>
        {selected?.status === "COMPLETED" && <Suspense fallback={<div className="nifti-viewer__message">NIfTI 뷰어를 준비하는 중입니다.</div>}><NiftiViewer analysisId={selected.analysis_id} /></Suspense>}<section className="ai-slices-card"><header><div><h3>주요 슬라이스</h3></div></header><div className="ai-slice-empty">Series / Instance thumbnail 연동 필요</div></section>
      </div>

      <aside className="ai-workspace-secondary">
        <section className="ai-result-card"><header><div><h3>AI 분석 결과</h3></div>{selected && <span className={`ai-status-badge is-${selected.status.toLowerCase()}`}>{STATUS_LABELS[selected.status] ?? selected.status}</span>}</header>
          {!selected ? <div className="ai-panel-state">분석 데이터가 없습니다.</div> : detailLoading ? <div className="ai-panel-state">결과를 불러오는 중...</div> : detailError ? <div className="ai-panel-state is-error">{detailError}</div> : selected.status !== "COMPLETED" ? <div className="ai-panel-state"><strong>완료된 결과가 없습니다.</strong><span>현재 단계: {selected.stage || "데이터 없음"}</span></div> : result ? <><div className="ai-result-highlight"><div><span>AI 판정</span><strong>{result.is_positive ? "양성" : "음성"}</strong></div><div><span>신뢰도</span><strong>{result.confidence}</strong></div></div><dl className="ai-result-metrics"><div><dt>병변 부피</dt><dd>{result.total_volume_ml} mL</dd></div><div><dt>상태</dt><dd>{STATUS_LABELS[selected.status] ?? selected.status}</dd></div><div><dt>요청 시각</dt><dd>{formatDate(selected.requested_at)}</dd></div><div><dt>모달리티</dt><dd>연동 필요</dd></div><div><dt>AI 모델</dt><dd>{selected.model ? `${selected.model.code} / ${selected.model.version}` : "데이터 없음"}</dd></div><div><dt>분석 유형</dt><dd>{selected.analysis_type}</dd></div></dl>{findings.length > 0 && <div className="ai-findings"><h4>Structured findings</h4>{findings.map(([key, value]) => <div key={key}><span>{key}</span><strong>{formatValue(value)}</strong></div>)}</div>}</> : <div className="ai-panel-state">결과 데이터가 없습니다.</div>}
        </section>

        <section className="ai-xai-card"><header><h3>XAI (설명 가능한 AI)</h3></header><div className="ai-xai-shell"><div><span>Segmentation</span><button type="button" disabled aria-label="Segmentation 연동 필요" /></div><div><span>Attention Map</span><button type="button" disabled aria-label="Attention Map 연동 필요" /></div><div><span>Uncertainty</span><button type="button" disabled aria-label="Uncertainty 연동 필요" /></div><label>오버레이 투명도<input type="range" disabled /></label><div className="ai-spectrum" aria-hidden="true" /><p>XAI response field 및 artifact API 연동 필요</p></div></section>

        <section className="ai-opinion-card"><header><h3>AI 결과 검토</h3></header><select value={reviewDecision} onChange={(event) => setReviewDecision(event.target.value as "ACCEPT" | "REJECT")}><option value="ACCEPT">수용</option><option value="REJECT">거절</option></select><textarea value={opinion} onChange={(event) => setOpinion(event.target.value)} placeholder="검토 의견을 작성하세요." aria-label="검토 의견" /><div className="ai-action-row"><button type="button" disabled>분석 영상 저장</button><button type="button" disabled={actionBusy || !result || !opinion.trim()} onClick={() => void saveReview()}>검토 저장</button><button type="button" disabled>협진 요청</button>{selected?.status === "QUEUED" && <button type="button" disabled={actionBusy} onClick={() => void cancelSelected()}>분석 취소</button>}</div><small>AI Review API 연결 · 영상 저장/협진은 필요한 Context ID가 없어 비활성</small></section>
      </aside>
    </div>
  </section>;
}
