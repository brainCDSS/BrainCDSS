import { useState } from "react";
import { createRadiologyReport, finalizeRadiologyReport, submitPreliminaryReport, updateRadiologyReport } from "./api";
import type { RadiologyReport, RadiologyReportDraft } from "./types";

interface Props { draft: RadiologyReportDraft; onClose?: () => void; }

function aiContext(draft: RadiologyReportDraft) {
  return {
    analysis_id: draft.analysisId,
    analysis_type: draft.analysisType,
    finding: draft.finding,
    lesion_count: draft.lesionCount,
    total_volume_ml: draft.totalVolumeMl,
  };
}

export default function RadiologyReportEditor({ draft, onClose }: Props) {
  const [report, setReport] = useState<RadiologyReport | null>(null);
  const [findings, setFindings] = useState("");
  const [impression, setImpression] = useState("");
  const [recommendation, setRecommendation] = useState("");
  const [criticalFinding, setCriticalFinding] = useState(false);
  const [criticalLevel, setCriticalLevel] = useState("NONE");
  const [busy, setBusy] = useState<"save" | "preliminary" | "finalize" | null>(null);
  const [message, setMessage] = useState<string | null>(null);

  const payload = () => ({
    findings: findings.trim(), impression: impression.trim(), recommendation: recommendation.trim(),
    structured_findings: { ai_context: aiContext(draft) },
    critical_finding: criticalFinding, critical_level: criticalFinding ? criticalLevel : "NONE",
  });

  async function save() {
    setBusy("save"); setMessage(null);
    try {
      const next = report
        ? await updateRadiologyReport(report.report_id, { version: report.version, ...payload() })
        : await createRadiologyReport({ study_id: draft.studyId, referenced_ai_analysis_id: draft.analysisId, ...payload() });
      setReport(next); setMessage("판독 초안이 저장되었습니다.");
      return next;
    } catch { setMessage("판독 초안을 저장하지 못했습니다. 입력값과 권한을 확인해 주세요."); return null; }
    finally { setBusy(null); }
  }

  async function transition(kind: "preliminary" | "finalize") {
    const next = await save();
    if (!next) return;
    setBusy(kind); setMessage(null);
    try {
      const updated = kind === "preliminary"
        ? await submitPreliminaryReport(next.report_id, next.version)
        : await finalizeRadiologyReport(next.report_id, next.version);
      setReport(updated); setMessage(kind === "preliminary" ? "예비판독으로 등록되었습니다." : "최종 판독이 확정되었습니다.");
    } catch { setMessage(kind === "preliminary" ? "예비판독 등록에 실패했습니다." : "최종 판독 확정에 실패했습니다."); }
    finally { setBusy(null); }
  }

  const locked = report?.status === "FINAL" || report?.status === "AMENDED";
  return <section className="clinical-page"><header className="clinical-page__heading"><h2>판독 작성</h2><p>AI 분석은 참고 정보이며 판독문은 영상의학과 의료진이 작성·확정합니다.</p></header><article className="clinical-card"><div className="clinical-card__title"><h3>AI 분석 연계 정보</h3><button type="button" onClick={onClose}>닫기</button></div><dl className="clinical-detail-list"><div><dt>검사 번호</dt><dd>{draft.accessionNumber || "미확인"}</dd></div><div><dt>분석 유형</dt><dd>{draft.analysisType}</dd></div><div><dt>AI 판정</dt><dd>{draft.finding}</dd></div><div><dt>병변 수</dt><dd>{draft.lesionCount ?? "미산출"}</dd></div><div><dt>총 병변 부피</dt><dd>{draft.totalVolumeMl == null ? "미산출" : `${draft.totalVolumeMl.toFixed(2)} mL`}</dd></div></dl></article><article className="clinical-card"><div className="clinical-card__title"><h3>판독문</h3><span>{report?.status ?? "미저장 초안"}</span></div><label>소견<textarea value={findings} disabled={locked} onChange={(event) => setFindings(event.target.value)} /></label><label>결론<textarea value={impression} disabled={locked} onChange={(event) => setImpression(event.target.value)} /></label><label>권고사항<textarea value={recommendation} disabled={locked} onChange={(event) => setRecommendation(event.target.value)} /></label><label><input type="checkbox" checked={criticalFinding} disabled={locked} onChange={(event) => setCriticalFinding(event.target.checked)} /> Critical finding</label>{criticalFinding && <label>Critical level<select value={criticalLevel} disabled={locked} onChange={(event) => setCriticalLevel(event.target.value)}><option value="URGENT">URGENT</option><option value="CRITICAL">CRITICAL</option></select></label>}{message && <p className="clinical-state">{message}</p>}<div className="clinical-action-bar"><button className="clinical-action" type="button" disabled={busy !== null || locked} onClick={() => void save()}>임시저장</button><button className="clinical-action" type="button" disabled={busy !== null || locked || !report || !findings.trim() && !impression.trim()} onClick={() => void transition("preliminary")}>예비판독</button><button className="clinical-action" type="button" disabled={busy !== null || locked || !report || !findings.trim() || !impression.trim()} onClick={() => void transition("finalize")}>최종 확정</button></div></article></section>;
}
