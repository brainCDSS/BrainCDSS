import { useCallback, useEffect, useMemo, useState } from "react";
import { requestAIAnalysis } from "../ai-analysis/api";
import type { AIAnalysisItem } from "../ai-analysis/types";
import { getImagingStudies, getImagingStudy, getImagingStudySeries, getStudyAIInputs } from "./api";
import type { AIInputBundle, ImagingSeries, ImagingStudy, ImagingStudyDetail } from "./types";
import "./imaging.css";

const LABELS: Record<string, string> = { HEMORRHAGIC_STROKE_CT: "뇌출혈 병변 분할", ISCHEMIC_STROKE_DWI_ADC: "허혈성 뇌졸중 병변 분할", CEREBRAL_ANEURYSM_MRA: "뇌동맥류 병변 분할" };
const MODELS: Record<string, string> = { HEMORRHAGIC_STROKE_CT: "H-N00 (Hemorrhage)", ISCHEMIC_STROKE_DWI_ADC: "I-N00 (Ischemia)", CEREBRAL_ANEURYSM_MRA: "A-N00 (Aneurysm)" };
const modalityOf = (study: ImagingStudy) => study.modality === "MRI" ? "MRI" : study.modality;
const formatDate = (value?: string | null) => value ? new Date(value).toLocaleString("ko-KR") : "—";
const formatSize = (bytes: number) => bytes >= 1048576 ? `${(bytes / 1048576).toFixed(1)} MB` : `${Math.ceil(bytes / 1024)} KB`;

interface ImagingPageProps {
  onAnalysisStarted?: (analysis: AIAnalysisItem) => void;
}

export default function ImagingPage({ onAnalysisStarted }: ImagingPageProps) {
  const [studies, setStudies] = useState<ImagingStudy[]>([]);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [detail, setDetail] = useState<ImagingStudyDetail | null>(null);
  const [series, setSeries] = useState<ImagingSeries[]>([]);
  const [bundles, setBundles] = useState<AIInputBundle[]>([]);
  const [analysisType, setAnalysisType] = useState("");
  const [tab, setTab] = useState<"ALL" | "CT" | "MRI" | "MRA">("ALL");
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [message, setMessage] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true); setMessage(null);
    try { const rows = await getImagingStudies(); setStudies(rows); setSelectedId((current) => current && rows.some((row) => row.id === current) ? current : rows[0]?.id ?? null); }
    catch { setMessage("영상 목록을 불러오지 못했습니다."); }
    finally { setLoading(false); }
  }, []);

  useEffect(() => { void load(); }, [load]);
  useEffect(() => {
    if (!selectedId) { setDetail(null); setSeries([]); setBundles([]); return; }
    let active = true;
    Promise.all([getImagingStudy(selectedId), getImagingStudySeries(selectedId), getStudyAIInputs(selectedId)])
      .then(([study, seriesResponse, inputResponse]) => { if (!active) return; setDetail(study); setSeries(seriesResponse.series); setBundles(inputResponse.bundles); setAnalysisType(inputResponse.bundles.find((bundle) => bundle.ready)?.analysis_type ?? ""); })
      .catch(() => { if (active) setMessage("선택한 검사의 AI 입력 정보를 불러오지 못했습니다."); });
    return () => { active = false; };
  }, [selectedId]);

  const visible = useMemo(() => studies.filter((study) => tab === "ALL" || modalityOf(study) === tab), [studies, tab]);
  const selectedBundle = bundles.find((bundle) => bundle.analysis_type === analysisType);
  const patient = detail?.patient;

  async function startAnalysis() {
    if (!selectedId) {
      setMessage("분석할 검사를 먼저 선택하세요.");
      return;
    }
    if (!selectedBundle?.ready) {
      const missing = selectedBundle?.missing_roles.join(" + ");
      setMessage(missing ? `필수 입력 ${missing} 영상이 필요합니다.` : "분석 유형과 입력 영상을 확인하세요.");
      return;
    }
    setSubmitting(true); setMessage(null);
    try {
      const analysis = await requestAIAnalysis(
        { study_id: selectedId, series_ids: selectedBundle.inputs.map((input) => input.series_id), analysis_type: analysisType, priority: "NORMAL" },
        crypto.randomUUID(),
      );
      setMessage("AI 분석 요청이 접수되었습니다.");
      onAnalysisStarted?.(analysis);
    }
    catch (error) {
      const reason = error instanceof Error ? error.message : String(error);
      setMessage(`분석 요청에 실패했습니다. ${reason}`);
    }
    finally { setSubmitting(false); }
  }

  return <section className="ai-start-page">
    <header className="ai-start-title"><div><h2>AI 분석 시작</h2><p>검사 영상과 환자 정보를 확인한 후 AI 분석을 요청합니다.</p></div><button onClick={() => void load()} disabled={loading}>새로고침</button></header>
    <section className="ai-patient-strip"><div><span>환자 ID</span><strong>{patient?.patient_no ?? "—"}</strong></div><div><span>환자명</span><strong>{patient?.name ?? "—"}</strong></div><div><span>검사번호</span><strong>{detail?.accession_number ?? "—"}</strong></div><div><span>검사일시</span><strong>{formatDate(detail?.study_datetime)}</strong></div><div><span>상태</span><strong className="is-ready">{detail?.status ?? "—"}</strong></div></section>
    {message && <div className="ai-start-message">{message}</div>}
    <div className="ai-start-grid"><main>
      <section className="ai-start-card"><header><h3>검사 및 영상 선택</h3><span>등록된 GCS NIfTI 검사 중 분석 대상을 선택합니다.</span></header>
        <nav className="ai-modality-tabs">{(["ALL", "MRI", "CT", "MRA"] as const).map((value) => <button key={value} className={tab === value ? "active" : ""} onClick={() => setTab(value)}>{value === "ALL" ? "전체" : value} ({studies.filter((study) => value === "ALL" || modalityOf(study) === value).length})</button>)}</nav>
        <div className="ai-study-list">{visible.map((study) => <button key={study.id} className={selectedId === study.id ? "selected" : ""} onClick={() => setSelectedId(study.id)}><strong>{study.patient_name ?? study.patient_no ?? "환자 정보 없음"}</strong><span>{study.accession_number}</span><span>{formatDate(study.study_at)}</span><span>{study.modality}</span></button>)}</div>
        <div className="ai-series-table"><div className="head"><span>선택</span><span>시리즈</span><span>설명</span><span>파일</span><span>검증 상태</span></div>{series.map((item) => { const input = selectedBundle?.inputs.find((artifact) => artifact.series_id === item.series_id); return <div key={item.series_id}><span><input type="checkbox" checked={Boolean(input)} readOnly /></span><strong>{item.protocol_name || item.series_description || item.modality}</strong><span>{item.series_description || "NIfTI 영상"}</span><span>{input ? formatSize(input.size_bytes) : "미등록"}</span><span className={input ? "valid" : "invalid"}>{input ? "적합" : "AI 입력 없음"}</span></div>; })}</div>
        <footer className="ai-validation-row"><strong>{selectedBundle?.ready ? `필수 입력 ${selectedBundle.inputs.map((input) => input.role).join(" + ")} 확인 완료` : "분석 가능한 입력을 선택하세요"}</strong><span>파일 무결성 확인</span><span>GCS 연결 완료</span></footer>
      </section>
      <section className="ai-start-card clinical-placeholder"><header><h3>임상 정보</h3><span>demo 환자에 연결된 임상 기록이 없어 선택 입력으로 제공합니다.</span></header><div><label>증상 발생 시각<input type="datetime-local" /></label><label>NIHSS 점수<input type="number" min="0" max="42" /></label><label>분석 참고사항<textarea placeholder="분석에 참고할 내용을 입력하세요." /></label></div></section>
    </main><aside>
      <section className="ai-start-card ai-settings-card"><header><h3>AI 분석 설정</h3></header><label>분석 유형<select value={analysisType} onChange={(event) => setAnalysisType(event.target.value)}><option value="">분석 유형 선택</option>{bundles.map((bundle) => <option key={bundle.analysis_type} value={bundle.analysis_type} disabled={!bundle.ready}>{LABELS[bundle.analysis_type] ?? bundle.analysis_type}{bundle.ready ? "" : ` (${bundle.missing_roles.join("+")} 필요)`}</option>)}</select></label><label>모델<input value={MODELS[analysisType] ?? "분석 유형을 선택하세요"} readOnly /></label>
        <div className="ai-output-list"><strong>출력 항목</strong><label><input type="checkbox" checked readOnly /> 병변 분할 NIfTI</label><label><input type="checkbox" checked readOnly /> 병변 부피</label><label><input type="checkbox" checked readOnly /> 결과 JSON</label><label className="disabled"><input type="checkbox" disabled /> Attention Map (모델 출력 필요)</label></div>
        <div className="ai-dicom-disabled"><span>DICOM SEG / SR 저장</span><button disabled>사용 불가</button><small>원본 DICOM UID가 없어 현재 demo에서는 GCS NIfTI 결과만 저장합니다.</small></div>
      </section>
      <section className="ai-start-card ai-request-summary"><header><h3>분석 요청 요약</h3></header><dl><div><dt>선택 영상</dt><dd>{selectedBundle?.inputs.map((input) => input.role).join(" + ") || "—"}</dd></div><div><dt>입력 검증</dt><dd>{selectedBundle?.ready ? "완료" : "확인 필요"}</dd></div><div><dt>모델</dt><dd>{MODELS[analysisType] ?? "—"}</dd></div><div><dt>저장 위치</dt><dd>GCS AI 결과 저장소</dd></div></dl></section>
      <button className="ai-start-submit" disabled={submitting} onClick={() => void startAnalysis()}>{submitting ? "요청 중…" : "AI 분석 시작"}</button>
    </aside></div>
  </section>;
}
