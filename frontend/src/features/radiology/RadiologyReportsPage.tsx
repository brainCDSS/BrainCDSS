import { useCallback, useEffect, useState } from "react";

import { getRadiologyWorklist } from "./api";
import RadiologyReportEditor from "./RadiologyReportEditor";
import type { RadiologyReportDraft, RadiologyWorkItem } from "./types";
import "./radiology.css";

const STATES = ["", "NO_CURRENT_REPORT", "DRAFT", "PRELIMINARY", "FINAL", "AMENDED"];

interface Props {
  draft?: RadiologyReportDraft | null;
  onDraftConsumed?: () => void;
}

function patientDisplay(item: RadiologyWorkItem) {
  return item.patient?.display || item.patient_name || item.patient_id || "환자 정보 없음";
}

function reportStatus(item: RadiologyWorkItem) {
  return item.report_status || item.status || "NO_CURRENT_REPORT";
}

export default function RadiologyReportsPage({ draft, onDraftConsumed }: Props) {
  const [items, setItems] = useState<RadiologyWorkItem[]>([]);
  const [selected, setSelected] = useState<RadiologyWorkItem | null>(null);
  const [state, setState] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      setItems((await getRadiologyWorklist(state)).results);
    } catch {
      setError("판독 Worklist를 불러오지 못했습니다.");
    } finally {
      setLoading(false);
    }
  }, [state]);

  useEffect(() => {
    void load();
  }, [load]);

  if (draft) return <RadiologyReportEditor draft={draft} onClose={onDraftConsumed} />;

  return (
    <section className="clinical-page">
      <header className="clinical-page__heading">
        <h2>최종 판독</h2>
        <p>영상의학과 판독 대상과 판독문 상태를 확인합니다.</p>
      </header>
      <div className="clinical-toolbar">
        <label>
          판독 상태
          <select value={state} onChange={(event) => setState(event.target.value)}>
            {STATES.map((value) => <option key={value || "ALL"} value={value}>{value || "전체"}</option>)}
          </select>
        </label>
        <button type="button" onClick={() => void load()} disabled={loading}>새로고침</button>
      </div>
      <div className="clinical-split">
        <article className="clinical-card">
          <div className="clinical-card__title"><h3>판독 대상 Worklist</h3><span>{items.length}건</span></div>
          {loading ? <div className="clinical-state">불러오는 중...</div>
            : error && !items.length ? <div className="clinical-state clinical-state--error">{error}</div>
              : !items.length ? <div className="clinical-state">판독 대상이 없습니다.</div>
                : (
                  <div className="clinical-table-wrap">
                    <table className="clinical-table">
                      <thead><tr><th>환자</th><th>Accession</th><th>검사</th><th>우선순위</th><th>AI</th><th>판독 상태</th></tr></thead>
                      <tbody>
                        {items.map((item) => (
                          <tr key={item.study_id} className={selected?.study_id === item.study_id ? "is-selected" : ""} onClick={() => setSelected(item)}>
                            <td>{patientDisplay(item)}</td>
                            <td>{item.accession_number}</td>
                            <td>{item.modality}</td>
                            <td>{item.priority}</td>
                            <td>{item.ai_status}</td>
                            <td><span className={`clinical-badge clinical-badge--${reportStatus(item).toLowerCase()}`}>{reportStatus(item)}</span></td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}
        </article>
        <aside className="clinical-card">
          <div className="clinical-card__title"><h3>판독 내용</h3></div>
          {selected ? (
            <dl className="clinical-detail-list">
              <div><dt>Study</dt><dd>{selected.study_id}</dd></div>
              <div><dt>판독 상태</dt><dd>{reportStatus(selected)}</dd></div>
              <div><dt>AI 상태</dt><dd>{selected.ai_status}</dd></div>
            </dl>
          ) : <div className="clinical-state">판독 대상을 선택하세요.</div>}
          <div className="clinical-state">Worklist 응답에 report_id가 없어 판독문 상세 조회는 연결하지 않았습니다.</div>
          <div className="clinical-action-bar"><button className="clinical-action" type="button" disabled>최종 확정</button></div>
        </aside>
      </div>
    </section>
  );
}
