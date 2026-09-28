import { useEffect, useState } from "react";
import { createRadiologyReport, finalizeRadiologyReport, getRadiologyReport, submitPreliminaryReport, updateRadiologyReport } from "./api";
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
  const [busy, setBusy] = useState<"load" | "save" | "preliminary" | "finalize" | null>(draft.reportId ? "load" : null);
  const [message, setMessage] = useState<string | null>(null);

  useEffect(() => {
    if (!draft.reportId) return;
    let active = true;
    setBusy("load");
    setMessage(null);
    void getRadiologyReport(draft.reportId)
      .then((existing) => {
        if (!active) return;
        setReport(existing);
        setFindings(existing.findings ?? "");
        setImpression(existing.impression ?? "");
        setRecommendation(existing.recommendation ?? "");
        setCriticalFinding(existing.critical_finding);
        setCriticalLevel(existing.critical_level || "NONE");
      })
      .catch(() => {
        if (active) setMessage("저장된 판독 초안을 불러오지 못했습니다. 권한과 판독문 상태를 확인해 주세요.");
      })
      .finally(() => {
        if (active) setBusy(null);
      });
    return () => { active = false; };
  }, [draft.reportId]);

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
  const statusLabel = report?.status === "FINAL"
    ? "최종 판독"
    : report?.status === "AMENDED"
      ? "정정 판독"
      : report?.status === "PRELIMINARY"
        ? "예비 판독"
        : report?.status === "DRAFT"
          ? "작성 중"
          : "미저장 초안";

  return (
    <section className="clinical-page radiology-report-editor">
      <header className="clinical-page__heading radiology-report-editor__heading">
        <div>
          <h2>판독 작성</h2>
          <p>AI 분석 결과를 참고하여 영상의학과 의료진이 판독문을 작성하고 확정합니다.</p>
        </div>
        <button className="radiology-editor-close" type="button" onClick={onClose}>
          목록으로
        </button>
      </header>

      <article className="clinical-card radiology-ai-summary">
        <div className="radiology-section-heading">
          <div>
            <span className="radiology-section-icon" aria-hidden="true">AI</span>
            <div>
              <h3>AI 분석 연계 정보</h3>
              <p>선택한 영상검사와 AI 분석 결과입니다.</p>
            </div>
          </div>
          <span className="radiology-ai-reference">참고 정보</span>
        </div>
        <dl className="radiology-summary-grid">
          <div><dt>검사 번호</dt><dd>{draft.accessionNumber || "미확인"}</dd></div>
          <div><dt>분석 유형</dt><dd>{draft.analysisType}</dd></div>
          <div className="radiology-summary-grid__finding"><dt>AI 판정</dt><dd>{draft.finding}</dd></div>
          <div><dt>병변 수</dt><dd><strong>{draft.lesionCount ?? "-"}</strong><small>{draft.lesionCount == null ? "미산출" : "개"}</small></dd></div>
          <div><dt>총 병변 부피</dt><dd><strong>{draft.totalVolumeMl == null ? "-" : draft.totalVolumeMl.toFixed(2)}</strong><small>{draft.totalVolumeMl == null ? "미산출" : "mL"}</small></dd></div>
        </dl>
      </article>

      <article className="clinical-card radiology-report-form">
        <div className="radiology-section-heading radiology-report-form__heading">
          <div>
            <span className="radiology-section-icon radiology-section-icon--document" aria-hidden="true">R</span>
            <div>
              <h3>판독문</h3>
              <p>임상적으로 의미 있는 소견과 결론을 명확하게 작성해 주세요.</p>
            </div>
          </div>
          <span className={`radiology-report-status radiology-report-status--${(report?.status ?? "draft").toLowerCase()}`}>
            {statusLabel}
          </span>
        </div>

        <div className="radiology-report-fields">
          <label className="radiology-report-field">
            <span>소견 <em>Findings</em></span>
            <textarea
              value={findings}
              disabled={locked || busy === "load"}
              placeholder="영상에서 확인되는 주요 소견을 입력하세요."
              onChange={(event) => setFindings(event.target.value)}
            />
          </label>
          <label className="radiology-report-field">
            <span>결론 <em>Impression</em></span>
            <textarea
              value={impression}
              disabled={locked || busy === "load"}
              placeholder="핵심 진단 및 임상적 결론을 입력하세요."
              onChange={(event) => setImpression(event.target.value)}
            />
          </label>
          <label className="radiology-report-field">
            <span>권고사항 <em>Recommendation</em></span>
            <textarea
              value={recommendation}
              disabled={locked || busy === "load"}
              placeholder="추가 검사나 추적 관찰 등 권고사항을 입력하세요."
              onChange={(event) => setRecommendation(event.target.value)}
            />
          </label>
        </div>

        <div className={`radiology-critical-panel ${criticalFinding ? "is-active" : ""}`}>
          <label className="radiology-critical-toggle">
            <input
              type="checkbox"
              checked={criticalFinding}
              disabled={locked || busy === "load"}
              onChange={(event) => setCriticalFinding(event.target.checked)}
            />
            <span><strong>Critical finding</strong><small>즉각적인 확인 또는 조치가 필요한 중대 소견</small></span>
          </label>
          {criticalFinding && (
            <label className="radiology-critical-level">
              <span>중요도</span>
              <select value={criticalLevel} disabled={locked || busy === "load"} onChange={(event) => setCriticalLevel(event.target.value)}>
                <option value="URGENT">긴급 (URGENT)</option>
                <option value="CRITICAL">위급 (CRITICAL)</option>
              </select>
            </label>
          )}
        </div>

        {message && <p className="radiology-editor-message" role="status">{message}</p>}

        <div className="clinical-action-bar radiology-editor-actions">
          <span>{locked ? "확정된 판독문은 수정할 수 없습니다." : "소견과 결론 입력 후 최종 확정할 수 있습니다."}</span>
          <div>
            <button className="clinical-action" type="button" disabled={busy !== null || locked} onClick={() => void save()}>
              {busy === "save" ? "저장 중..." : "임시저장"}
            </button>
            {report?.status !== "PRELIMINARY" && <button className="clinical-action radiology-action--preliminary" type="button" disabled={busy !== null || locked || !report || (!findings.trim() && !impression.trim())} onClick={() => void transition("preliminary")}>
              {busy === "preliminary" ? "처리 중..." : "예비판독"}
            </button>}
            <button className="clinical-action radiology-action--primary" type="button" disabled={busy !== null || locked || !report || !findings.trim() || !impression.trim()} onClick={() => void transition("finalize")}>
              {busy === "finalize" ? "확정 중..." : "최종 확정"}
            </button>
          </div>
        </div>
      </article>
    </section>
  );
}
