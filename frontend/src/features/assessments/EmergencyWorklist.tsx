import { useCallback, useEffect, useState } from "react";

import { getPatient } from "../patients/api";
import type { Patient } from "../patients/types";
import { acknowledgeEmergencyEvent, getEmergencyWorklist } from "./api";
import type { EmergencyWorklistItem, EmergencyWorklistResponse } from "./types";

interface EmergencyWorklistProps {
  onOpenPatient?: (patient: Patient) => void;
}

function formatDateTime(value: string | null): string {
  return value ? new Date(value).toLocaleString("ko-KR") : "-";
}

function patientIdOf(item: EmergencyWorklistItem): string | null {
  return item.patient_summary.patient_id ?? item.patient_summary.id ?? null;
}

function patientDetailOf(item: EmergencyWorklistItem): string {
  const summary = item.patient_summary;
  const age = summary.age ?? summary.estimated_age;
  return [summary.sex ?? null, age == null ? null : `${age}세`]
    .filter(Boolean)
    .join(" · ") || "-";
}

export default function EmergencyWorklist({ onOpenPatient }: EmergencyWorklistProps) {
  const [worklist, setWorklist] = useState<EmergencyWorklistResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [acknowledgingId, setAcknowledgingId] = useState<string | null>(null);
  const [patientOpeningId, setPatientOpeningId] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      setWorklist(await getEmergencyWorklist());
    } catch {
      setError("응급 Worklist를 불러오지 못했습니다.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { void load(); }, [load]);

  async function acknowledge(item: EmergencyWorklistItem) {
    setAcknowledgingId(item.event.id);
    setError(null);
    try {
      await acknowledgeEmergencyEvent(item.event.id);
      await load();
    } catch {
      setError("응급 이벤트 확인 처리에 실패했습니다.");
    } finally {
      setAcknowledgingId(null);
    }
  }

  async function openPatient(item: EmergencyWorklistItem) {
    const patientId = patientIdOf(item);
    if (!patientId || !onOpenPatient) return;
    setPatientOpeningId(patientId);
    setError(null);
    try {
      onOpenPatient(await getPatient(patientId));
    } catch {
      setError("환자 정보를 불러오지 못했습니다.");
    } finally {
      setPatientOpeningId(null);
    }
  }

  return (
    <section className="clinical-page">
      <header className="clinical-page__heading">
        <h2>응급 Worklist</h2>
        <p>초기평가에서 긴급·응급으로 분류되어 현재 사용자에게 배정된 환자입니다.</p>
      </header>

      {error && (
        <div className="clinical-card">
          <div className="clinical-state clinical-state--error">
            <div><p>{error}</p><button className="clinical-action" type="button" onClick={() => void load()}>다시 시도</button></div>
          </div>
        </div>
      )}

      {!error && loading && <div className="clinical-card"><div className="clinical-state">응급 Worklist를 불러오는 중입니다.</div></div>}

      {!error && !loading && worklist && (
        <div className="clinical-card">
          <div className="clinical-card__title"><h3>응급환자 목록</h3><span>총 {worklist.count}건</span></div>
          {worklist.results.length === 0 ? (
            <div className="clinical-state">현재 확인할 응급환자가 없습니다.</div>
          ) : (
            <div className="clinical-table-wrap">
              <table className="clinical-table">
                <thead><tr><th>환자</th><th>환자번호/MRN</th><th>성별/나이</th><th>응급도</th><th>점수</th><th>LKW</th><th>알림 시각</th><th>현재 상태</th><th>확인 여부</th><th>작업</th></tr></thead>
                <tbody>{worklist.results.map((item) => {
                  const patientId = patientIdOf(item);
                  const acknowledged = item.event.status === "ACKNOWLEDGED" || Boolean(item.event.acknowledged_at);
                  return <tr key={item.event.id}>
                    <td>{patientId && onOpenPatient ? <button className="clinical-action" type="button" disabled={patientOpeningId === patientId} onClick={() => void openPatient(item)}>{item.patient_summary.name ?? patientId}</button> : (item.patient_summary.name ?? "-")}</td>
                    <td>{item.patient_summary.patient_no ?? "-"}</td>
                    <td>{patientDetailOf(item)}</td>
                    <td><span className={`clinical-badge clinical-badge--${item.triage_priority.toLowerCase()}`}>{item.triage_priority}</span></td>
                    <td>{item.total_score ?? "-"}</td>
                    <td>{formatDateTime(item.lkw_at)}</td>
                    <td>{formatDateTime(item.event.notified_at)}</td>
                    <td>{item.event.status}</td>
                    <td>{acknowledged ? formatDateTime(item.event.acknowledged_at) : "미확인"}</td>
                    <td>{!acknowledged && <button className="clinical-action" type="button" disabled={acknowledgingId === item.event.id} onClick={() => void acknowledge(item)}>{acknowledgingId === item.event.id ? "처리 중" : "확인"}</button>}</td>
                  </tr>;
                })}</tbody>
              </table>
            </div>
          )}
        </div>
      )}
    </section>
  );
}
