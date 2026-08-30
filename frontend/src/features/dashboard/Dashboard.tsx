import "./dashboard.css";

export default function Dashboard() {
  return (
    <section className="dashboard">
      <div className="dashboard-heading">
        <div>
          <span className="dashboard-label">DASHBOARD</span>
          <h2>의료진 대시보드</h2>
          <p>
            승인된 요약 API를 기반으로 주요 업무 정보를 제공합니다.
          </p>
        </div>
      </div>

      <div className="dashboard-placeholder-grid">
        <div className="dashboard-placeholder-card">
          <span>SUMMARY</span>
          <strong>요약 정보</strong>
          <p>승인된 요약 API 연동 예정</p>
        </div>

        <div className="dashboard-placeholder-card">
          <span>WORKFLOW</span>
          <strong>업무 현황</strong>
          <p>승인된 요약 API 연동 예정</p>
        </div>

        <div className="dashboard-placeholder-card">
          <span>ALERT</span>
          <strong>알림 현황</strong>
          <p>승인된 요약 API 연동 예정</p>
        </div>
      </div>

      <div className="dashboard-section">
        <div className="section-header">
          <div>
            <span>WORKLIST</span>
            <h3>업무 목록</h3>
          </div>
        </div>

        <div className="empty-state">
          <strong>업무 데이터 연동 예정</strong>
          <p>
            API 계약 확정 후 역할 및 권한에 따라 필요한 업무 정보를 표시합니다.
          </p>
        </div>
      </div>
    </section>
  );
}