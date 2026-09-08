import { useCallback, useEffect, useState } from "react";
import { getAIAnalyses, getAIAnalysisResult } from "./api";
import type { AIAnalysisItem, AIAnalysisResult } from "./types";
import "./ai-analysis.css";

const STATUSES = ["", "QUEUED", "PROCESSING", "COMPLETED", "FAILED", "RETRYING", "CANCELLED"];

function formatDate(value: string) {
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? value : date.toLocaleString("ko-KR");
}

export default function AIAnalysisResultsPage() {
  const [items, setItems] = useState<AIAnalysisItem[]>([]);
  const [status, setStatus] = useState("");
  const [selected, setSelected] = useState<AIAnalysisItem | null>(null);
  const [result, setResult] = useState<AIAnalysisResult | null>(null);
  const [loading, setLoading] = useState(true);
  const [detailLoading, setDetailLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true); setError(null);
    try { const response = await getAIAnalyses(status); setItems(response.results); }
    catch { setError("AI 분석 목록을 불러오지 못했습니다."); }
    finally { setLoading(false); }
  }, [status]);

  useEffect(() => { void load(); }, [load]);

  async function selectItem(item: AIAnalysisItem) {
    setSelected(item); setResult(null);
    if (item.status !== "COMPLETED") return;
    setDetailLoading(true);
    try { setResult(await getAIAnalysisResult(item.analysis_id)); }
    catch { setError("선택한 분석 결과를 불러오지 못했습니다."); }
    finally { setDetailLoading(false); }
  }

  return <section className="clinical-page">
    <header className="clinical-page__heading"><h2>AI 분석 결과</h2><p>영상 AI 분석의 진행 상태와 완료 결과를 확인합니다.</p></header>
    <div className="clinical-toolbar"><label>상태<select value={status} onChange={(e) => setStatus(e.target.value)}>{STATUSES.map((value) => <option key={value || "ALL"} value={value}>{value || "전체"}</option>)}</select></label><button type="button" onClick={() => void load()} disabled={loading}>새로고침</button></div>
    <div className="clinical-split">
      <article className="clinical-card clinical-card--table"><div className="clinical-card__title"><h3>분석 목록</h3><span>{items.length} / {items.length ? "조회됨" : "0"}</span></div>
        {loading ? <div className="clinical-state">불러오는 중...</div> : error && !items.length ? <div className="clinical-state clinical-state--error">{error}</div> : !items.length ? <div className="clinical-state">분석 데이터가 없습니다.</div> : <div className="clinical-table-wrap"><table className="clinical-table"><thead><tr><th>분석 유형</th><th>Study</th><th>상태</th><th>단계</th><th>모델</th><th>요청 시각</th></tr></thead><tbody>{items.map((item) => <tr key={item.analysis_id} className={selected?.analysis_id === item.analysis_id ? "is-selected" : ""} onClick={() => void selectItem(item)}><td>{item.analysis_type}</td><td className="clinical-mono">{item.study_id}</td><td><span className={`clinical-badge clinical-badge--${item.status.toLowerCase()}`}>{item.status}</span></td><td>{item.stage}</td><td>{item.model ? `${item.model.code} / ${item.model.version}` : "-"}</td><td>{formatDate(item.requested_at)}</td></tr>)}</tbody></table></div>}
      </article>
      <aside className="clinical-card clinical-detail"><div className="clinical-card__title"><h3>결과 상세</h3></div>{!selected ? <div className="clinical-state">분석 항목을 선택하세요.</div> : detailLoading ? <div className="clinical-state">결과를 불러오는 중...</div> : selected.status !== "COMPLETED" ? <div className="clinical-state">완료된 분석에서 결과를 확인할 수 있습니다.</div> : result ? <dl className="clinical-detail-list"><div><dt>판정</dt><dd>{result.is_positive ? "양성" : "음성"}</dd></div><div><dt>신뢰도</dt><dd>{result.confidence}</dd></div><div><dt>중증도</dt><dd>{result.severity}</dd></div><div><dt>병변 수</dt><dd>{result.lesion_count}</dd></div><div><dt>총 부피</dt><dd>{result.total_volume_ml} mL</dd></div><div><dt>Schema</dt><dd>{result.output_schema_version}</dd></div></dl> : <div className="clinical-state">결과 데이터가 없습니다.</div>}</aside>
    </div>
  </section>;
}
