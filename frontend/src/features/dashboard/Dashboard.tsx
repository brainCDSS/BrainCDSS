import "./dashboard.css";

/**
 * Dashboard 상단 요약 카드
 *
 * 지금은 Dashboard API를 아직 연결하지 않았기 때문에
 * 실제 숫자를 임의로 넣지 않고 "—"로 표시한다.
 *
 * 추후 Mock API / 실제 API 연결 시
 * value 부분에 API 응답값을 넣으면 된다.
 */
const summaryCards = [
  {
    key: "emergency",
    label: "긴급·응급 환자",
    value: "—",
    description: "응급 Worklist",
    icon: "!",
    tone: "critical",
  },
  {
    key: "consultation",
    label: "대기 중 협진",
    value: "—",
    description: "협진 요청",
    icon: "C",
    tone: "primary",
  },
  {
    key: "ai",
    label: "AI 분석 완료",
    value: "—",
    description: "분석 완료",
    icon: "AI",
    tone: "primary",
  },
  {
    key: "appointment",
    label: "오늘 예약",
    value: "—",
    description: "오늘 일정",
    icon: "D",
    tone: "primary",
  },
  {
    key: "notification",
    label: "미읽음 알림",
    value: "—",
    description: "확인 필요",
    icon: "N",
    tone: "warning",
  },
];

/**
 * 검사 / AI 처리 현황
 *
 * 지금은 실제 처리 개수를 임의 생성하지 않는다.
 * API 연결 이후 completed / total 값을 받아 표시할 예정이다.
 */
const processItems = [
  {
    key: "imaging",
    label: "영상검사 Order",
    value: "연동 예정",
  },
  {
    key: "ai",
    label: "AI 분석",
    value: "연동 예정",
  },
  {
    key: "report",
    label: "영상의학과 판독",
    value: "연동 예정",
  },
];

/**
 * 빠른 진입 버튼
 *
 * 현재는 버튼 UI만 구현한다.
 * Routing 연결 후 각 화면으로 이동시킬 예정이다.
 */
const quickActions = [
  {
    key: "patient",
    label: "환자 검색",
    icon: "P",
  },
  {
    key: "imaging",
    label: "영상검사 Order",
    icon: "I",
  },
  {
    key: "consultation",
    label: "협진 요청",
    icon: "C",
  },
  {
    key: "prescription",
    label: "처방 작성",
    icon: "Rx",
  },
];

export default function Dashboard() {
  return (
    <section className="dashboard">
      {/* =====================================================
          Dashboard 제목 영역
          ===================================================== */}
      <div className="dashboard-heading">
        <div>
          <span className="dashboard-label">
            CLINICAL DASHBOARD
          </span>

          <h2>메인 대시보드</h2>

          <p>
            환자, 검사, AI 분석, 협진 및 주요 알림 현황을
            한 화면에서 확인합니다.
          </p>
        </div>

        {/* 추후 현재 날짜 / 새로고침 기능 연결 가능 */}
        <div className="dashboard-heading-actions">
          <button
            type="button"
            className="dashboard-refresh-button"
          >
            새로고침
          </button>
        </div>
      </div>

      {/* =====================================================
          상단 Summary 카드

          5개 카드가 한 줄에 표시된다.
          카드 개수 / 폭은 dashboard.css의
          .dashboard-summary-grid에서 조절한다.
          ===================================================== */}
      <div className="dashboard-summary-grid">
        {summaryCards.map((card) => (
          <article
            key={card.key}
            className={`summary-card summary-card-${card.tone}`}
          >
            <div
              className={`summary-card-icon summary-card-icon-${card.tone}`}
            >
              {card.icon}
            </div>

            <div className="summary-card-content">
              <span>{card.label}</span>

              <div className="summary-card-value">
                {card.value}
              </div>

              <small>{card.description}</small>
            </div>
          </article>
        ))}
      </div>

      {/* =====================================================
          Dashboard 본문

          왼쪽 큰 영역 : Worklist
          오른쪽 영역   : 검사/AI 현황 + 오늘 일정

          폭 비율은 dashboard.css의
          .dashboard-main-grid에서 조절한다.
          ===================================================== */}
      <div className="dashboard-main-grid">
        {/* ===================================================
            왼쪽: 우선순위 Worklist
            =================================================== */}
        <section className="dashboard-panel worklist-panel">
          <div className="dashboard-panel-header">
            <div>
              <span className="panel-label">WORKLIST</span>
              <h3>긴급·응급 Worklist</h3>
            </div>

            <button
              type="button"
              className="panel-link-button"
            >
              전체 보기
            </button>
          </div>

          {/* 추후 응급 Worklist API 결과를 여기에 출력 */}
          <div className="worklist-table-wrapper">
            <table className="worklist-table">
              <thead>
                <tr>
                  <th>우선순위</th>
                  <th>환자</th>
                  <th>상태 / 주요 이슈</th>
                  <th>위험도</th>
                  <th>등록시간</th>
                </tr>
              </thead>

              <tbody>
                <tr>
                  <td
                    colSpan={5}
                    className="dashboard-empty-cell"
                  >
                    <strong>Worklist 데이터 연동 예정</strong>
                    <span>
                      응급 Worklist API 연결 후 환자 목록을
                      표시합니다.
                    </span>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </section>

        {/* ===================================================
            오른쪽 상단: 검사 / AI 처리 현황
            =================================================== */}
        <div className="dashboard-right-column">
          <section className="dashboard-panel">
            <div className="dashboard-panel-header">
              <div>
                <span className="panel-label">
                  PROCESS
                </span>

                <h3>검사 / AI 처리 현황</h3>
              </div>

              <button
                type="button"
                className="panel-link-button"
              >
                상세 보기
              </button>
            </div>

            <div className="process-list">
              {processItems.map((item) => (
                <div
                  key={item.key}
                  className="process-item"
                >
                  <div className="process-item-top">
                    <strong>{item.label}</strong>
                    <span>{item.value}</span>
                  </div>

                  {/*
                    API 연결 전이라 Progress는 0%로 둔다.

                    추후 style={{ width: `${progress}%` }}
                    형태로 실제 처리율을 넣을 수 있다.
                  */}
                  <div className="process-track">
                    <div
                      className="process-bar"
                      style={{ width: "0%" }}
                    />
                  </div>
                </div>
              ))}
            </div>
          </section>

          {/* =================================================
              오른쪽 하단: 오늘 일정
              ================================================= */}
          <section className="dashboard-panel">
            <div className="dashboard-panel-header">
              <div>
                <span className="panel-label">
                  SCHEDULE
                </span>

                <h3>오늘 일정 / 예약</h3>
              </div>

              <button
                type="button"
                className="panel-link-button"
              >
                전체 보기
              </button>
            </div>

            <div className="dashboard-empty-state">
              <strong>오늘 일정 연동 예정</strong>

              <p>
                의료진 예약 API 연결 후 오늘 일정을
                표시합니다.
              </p>
            </div>
          </section>
        </div>
      </div>

      {/* =====================================================
          Dashboard 하단

          왼쪽 : 최근 알림
          오른쪽 : 빠른 진입
          ===================================================== */}
      <div className="dashboard-bottom-grid">
        {/* 최근 알림 */}
        <section className="dashboard-panel">
          <div className="dashboard-panel-header">
            <div>
              <span className="panel-label">
                NOTIFICATION
              </span>

              <h3>최근 알림</h3>
            </div>

            <button
              type="button"
              className="panel-link-button"
            >
              전체 보기
            </button>
          </div>

          <div className="dashboard-empty-state">
            <strong>최근 알림 연동 예정</strong>

            <p>
              알림 API 연결 후 최근 알림을 표시합니다.
            </p>
          </div>
        </section>

        {/* 빠른 진입 */}
        <section className="dashboard-panel">
          <div className="dashboard-panel-header">
            <div>
              <span className="panel-label">
                QUICK ACTION
              </span>

              <h3>빠른 진입</h3>
            </div>
          </div>

          <div className="quick-action-grid">
            {quickActions.map((action) => (
              <button
                key={action.key}
                type="button"
                className="quick-action-button"
              >
                <span className="quick-action-icon">
                  {action.icon}
                </span>

                <span>{action.label}</span>
              </button>
            ))}
          </div>
        </section>
      </div>
    </section>
  );
}