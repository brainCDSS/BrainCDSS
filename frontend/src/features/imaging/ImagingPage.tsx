import { useCallback, useEffect, useMemo, useState } from "react";
import { requestAIAnalysis } from "../ai-analysis/api";
import type { AIAnalysisItem } from "../ai-analysis/types";
import { getImagingStudies, getImagingStudy, getImagingStudySeries, getStudyAIInputs } from "./api";
import type { AIInputBundle, ImagingSeries, ImagingStudy, ImagingStudyDetail } from "./types";
import "./imaging.css";

const LABELS: Record<string, string> = { HEMORRHAGIC_STROKE_CT: "CT 뇌출혈 병변 분석", ISCHEMIC_STROKE_DWI_ADC: "MRI 허혈성 뇌졸중 분석", CEREBRAL_ANEURYSM_MRA: "MRA 뇌동맥류 분석" };
const MODELS: Record<string, string> = { HEMORRHAGIC_STROKE_CT: "H-N00 · Hemorrhage", ISCHEMIC_STROKE_DWI_ADC: "I-N00 · Ischemia", CEREBRAL_ANEURYSM_MRA: "A-N00 · Aneurysm" };
const modalityOf = (study: ImagingStudy) => study.modality === "MRI" ? "MRI" : study.modality;
const formatDate = (value?: string | null) => value ? new Date(value).toLocaleString("ko-KR") : "—";
const formatSize = (bytes: number) => bytes >= 1048576 ? `${(bytes / 1048576).toFixed(1)} MB` : `${Math.ceil(bytes / 1024)} KB`;

interface ImagingPageProps { onAnalysisStarted?: (analysis: AIAnalysisItem) => void; }

export default function ImagingPage({ onAnalysisStarted }: ImagingPageProps) {
  const [studies, setStudies] = useState<ImagingStudy[]>([]);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [detail, setDetail] = useState<ImagingStudyDetail | null>(null);
  const [, setSeries] = useState<ImagingSeries[]>([]);
  const [bundles, setBundles] = useState<AIInputBundle[]>([]);
  const [analysisType, setAnalysisType] = useState("");
  const [tab, setTab] = useState<"ALL" | "CT" | "MRI" | "MRA">("ALL");
  const [query, setQuery] = useState("");
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const load = useCallback(async () => { setLoading(true); setMessage(null); try { const rows = await getImagingStudies(); setStudies(rows); setSelectedId((current) => current && rows.some((row) => row.id === current) ? current : rows[0]?.id ?? null); } catch { setMessage("검사 목록을 불러오지 못했습니다."); } finally { setLoading(false); } }, []);
  useEffect(() => { void load(); }, [load]);
  useEffect(() => { setMessage(null); if (!selectedId) { setDetail(null); setSeries([]); setBundles([]); return; } let active = true; Promise.all([getImagingStudy(selectedId), getImagingStudySeries(selectedId), getStudyAIInputs(selectedId)]).then(([study, seriesResponse, inputResponse]) => { if (!active) return; setDetail(study); setSeries(seriesResponse.series); setBundles(inputResponse.bundles); setAnalysisType(inputResponse.bundles.find((bundle) => bundle.ready)?.analysis_type ?? ""); }).catch(() => { if (active) setMessage("선택한 검사의 AI 입력 정보를 불러오지 못했습니다."); }); return () => { active = false; }; }, [selectedId]);
  const visible = useMemo(() => studies.filter((study) => { const term = query.trim().toLowerCase(); return (tab === "ALL" || modalityOf(study) === tab) && (!term || [study.patient_name, study.patient_no, study.accession_number, study.modality].some((value) => value?.toLowerCase().includes(term))); }), [studies, tab, query]);
  const selectedBundle = bundles.find((bundle) => bundle.analysis_type === analysisType);
  const patient = detail?.patient;
  const selectedStudy = studies.find((study) => study.id === selectedId);
  const pageSize = 5;
  const totalPages = Math.max(1, Math.ceil(visible.length / pageSize));
  const pagedStudies = visible.slice((Math.min(page, totalPages) - 1) * pageSize, Math.min(page, totalPages) * pageSize);
  async function startAnalysis() { if (!selectedId || !selectedBundle?.ready) { setMessage(selectedBundle?.missing_roles.length ? `필수 입력 ${selectedBundle.missing_roles.join(" + ")} 영상이 필요합니다.` : "분석 가능한 검사와 분석 유형을 선택하세요."); return; } setSubmitting(true); setMessage(null); try { const analysis = await requestAIAnalysis({ study_id: selectedId, series_ids: selectedBundle.inputs.map((input) => input.series_id), analysis_type: analysisType, priority: "NORMAL" }, crypto.randomUUID()); setMessage("AI 분석 요청을 접수했습니다."); onAnalysisStarted?.(analysis); } catch (error) { setMessage(`분석 요청에 실패했습니다. ${error instanceof Error ? error.message : String(error)}`); } finally { setSubmitting(false); } }
  return <section className="ai-start-page ai-start-workspace">
    <header className="ai-start-title"><div><h2>AI 판독 보조 분석</h2><p>검사 영상과 임상 정보를 확인한 후 AI 분석을 요청합니다.</p></div><button type="button" onClick={() => void load()} disabled={loading}>새로고침</button></header>
    <section className="ai-patient-strip"><div><span>환자 ID</span><strong>{patient?.patient_no ?? "—"}</strong></div><div><span>환자명</span><strong>{patient?.name ?? "환자 정보 미연결"}</strong></div><div><span>검사번호</span><strong>{detail?.accession_number ?? "—"}</strong></div><div><span>검사일시</span><strong>{formatDate(detail?.study_datetime)}</strong></div><div><span>상태</span><strong className="is-ready">● 분석 가능</strong></div></section>
    {message && <div className="ai-start-message">{message}</div>}
    <div className="ai-start-grid"><main>
      <section className="ai-start-card ai-study-card"><header><div><h3>▣ 검사 및 영상 선택</h3><span>등록된 GCS NIfTI 검사 중 분석 대상을 선택합니다.</span></div><label className="ai-study-search"><span>⌕</span><input value={query} onChange={(event) => { setQuery(event.target.value); setPage(1); }} placeholder="환자명, 검사번호, 영상유형으로 검색" /></label></header><nav className="ai-modality-tabs">{(["ALL", "MRI", "CT", "MRA"] as const).map((value) => <button type="button" key={value} className={tab === value ? "active" : ""} onClick={() => { setTab(value); setPage(1); }}>{value === "ALL" ? "전체" : value} ({studies.filter((study) => value === "ALL" || modalityOf(study) === value).length})</button>)}</nav><div className="ai-study-table"><div className="head"><span>선택</span><span>환자명</span><span>검사번호</span><span>검사일시</span><span>영상유형</span><span>상태</span></div>{pagedStudies.map((study) => <button type="button" key={study.id} className={selectedId === study.id ? "selected" : ""} onClick={() => setSelectedId(study.id)}><span className="study-radio">{selectedId === study.id ? "◉" : "○"}</span><strong>{study.patient_name ?? study.patient_no ?? "환자 정보 미연결"}</strong><span>{study.accession_number}</span><span>{formatDate(study.study_at)}</span><span>{modalityOf(study)}</span><span className="study-status">● 분석 가능</span></button>)}{!loading && visible.length === 0 && <p className="ai-empty-study">조건에 맞는 검사가 없습니다.</p>}</div>{visible.length > pageSize && <footer className="ai-study-pagination"><button type="button" disabled={page <= 1} onClick={() => setPage((current) => Math.max(1, current - 1))}>‹ 이전</button><span>{Math.min(page, totalPages)} / {totalPages}</span><button type="button" disabled={page >= totalPages} onClick={() => setPage((current) => Math.min(totalPages, current + 1))}>다음 ›</button></footer>}</section>
    </main><aside>
      <section className="ai-start-card ai-settings-card"><header><h3>⚙ AI 분석 설정</h3></header><label>분석 유형<select value={analysisType} onChange={(event) => setAnalysisType(event.target.value)}><option value="">분석 유형 선택</option>{bundles.map((bundle) => <option key={bundle.analysis_type} value={bundle.analysis_type} disabled={!bundle.ready}>{LABELS[bundle.analysis_type] ?? bundle.analysis_type}{bundle.ready ? "" : ` (${bundle.missing_roles.join("+")} 필요)`}</option>)}</select></label><label>AI 모델<div className="ai-model-readout"><input value={MODELS[analysisType] ?? "분석 유형을 선택하세요"} readOnly /><b>자동 선택</b></div><small>선택된 검사 영상 유형에 적합한 모델이 자동으로 설정됩니다.</small></label></section>
      <section className="ai-start-card ai-request-summary"><header><h3>▤ 분석 요청 요약</h3></header><dl><div><dt>선택 영상</dt><dd>{selectedBundle?.inputs.map((input) => input.role).join(" + ") || "—"}</dd></div><div><dt>입력 검증</dt><dd className={selectedBundle?.ready ? "summary-ok" : ""}>{selectedBundle?.ready ? "● 완료" : "확인 필요"}</dd></div><div><dt>모델</dt><dd>{MODELS[analysisType] ?? "—"}</dd></div><div><dt>결과 처리</dt><dd>분석 완료 후 자동 저장</dd></div></dl><button type="button" className="ai-input-details-button ai-input-summary-button" onClick={() => setMessage(`${selectedStudy?.modality === "MRI" ? "MRI" : "분석"} 입력 영상: ${selectedBundle?.inputs.map((input) => `${input.role} (${formatSize(input.size_bytes)})`).join(", ") || "등록된 입력 없음"}`)}>입력 영상 상세</button><button type="button" className="ai-start-submit" disabled={submitting || !selectedBundle?.ready} onClick={() => void startAnalysis()}>{submitting ? "요청 중…" : "▶  AI 분석 요청"}</button></section>
    </aside></div>
  </section>;
}
