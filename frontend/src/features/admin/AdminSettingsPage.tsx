import "./admin.css";
const sections=[{title:"기관 설정",description:"기관 정보 설정 API가 연결되지 않았습니다."},{title:"공통 설정",description:"공통 시스템 설정 API가 연결되지 않았습니다."},{title:"알림 설정",description:"관리자 알림 정책 설정 API가 연결되지 않았습니다."}];
export default function AdminSettingsPage(){return <section className="clinical-page admin-page"><header className="clinical-page__heading"><h2>설정</h2><p>관리자 설정 영역입니다.</p></header><div className="admin-section-stack">{sections.map(s=><section className="clinical-card admin-setting-section" key={s.title}><h3>{s.title}</h3><p>{s.description}</p></section>)}</div></section>}
