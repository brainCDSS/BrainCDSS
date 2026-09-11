import { useEffect, useState } from "react";
import { getBackendHealth } from "./api";
import { AI_ANALYSIS_STATUS, CORE_SERVICE_STATUS, SYSTEM_ALERTS } from "./data";
import type { ServiceStatusItem } from "./types";
import "./admin.css";

export default function AdminDashboard() {
  const [statuses, setStatuses] = useState(CORE_SERVICE_STATUS);
  useEffect(() => { let live=true; getBackendHealth().then((health)=>{if(live)setStatuses((rows)=>rows.map((row)=>row.service==="Backend"?{...row,status:health.status==="ok"?"정상":"확인 실패",checkedAt:new Date().toLocaleString(),message:`${health.service} 응답`}:row));}).catch(()=>{if(live)setStatuses((rows)=>rows.map((row)=>row.service==="Backend"?{...row,status:"확인 실패",checkedAt:new Date().toLocaleString(),message:"Backend health 응답을 확인하지 못했습니다."}:row));}); return()=>{live=false;}; }, []);
  return <section className="clinical-page admin-page">
    <header className="clinical-page__heading"><h2>Dashboard</h2><p>BrainCDSS 운영 상태를 확인합니다.</p></header>
    <div className="admin-grid">
      <StatusCard rows={statuses} />
      <section className="clinical-card"><div className="clinical-card__title"><h3>AI 분석 현황</h3></div><div className="clinical-table-wrap"><table className="clinical-table"><thead><tr><th>분석 유형</th><th>완료</th><th>실행 중</th><th>실패</th></tr></thead><tbody>{AI_ANALYSIS_STATUS.map((item)=><tr key={item.type}><td>{item.type}</td><td>{item.completed ?? "-"}</td><td>{item.running ?? "-"}</td><td>{item.failed ?? "-"}</td></tr>)}</tbody></table></div></section>
      <section className="clinical-card"><div className="clinical-card__title"><h3>최근 시스템 알림</h3></div><div className="clinical-state">{SYSTEM_ALERTS.length === 0 ? "연결된 시스템 알림 API가 없습니다." : null}</div></section>
      <section className="clinical-card"><div className="clinical-card__title"><h3>최근 감사 로그</h3></div><div className="clinical-state">감사 로그 메뉴에서 조회 사유를 입력해 확인할 수 있습니다.</div></section>
    </div>
  </section>;
}

function StatusCard({ rows }: { rows: ServiceStatusItem[] }) {
  return <section className="clinical-card"><div className="clinical-card__title"><h3>시스템 상태</h3></div><div className="clinical-table-wrap"><table className="clinical-table"><thead><tr><th>서비스</th><th>상태</th><th>최근 업데이트</th></tr></thead><tbody>{rows.map((item)=><tr key={item.service}><td>{item.service}</td><td><span className="clinical-badge">{item.status}</span></td><td>{item.checkedAt}</td></tr>)}</tbody></table></div></section>;
}
