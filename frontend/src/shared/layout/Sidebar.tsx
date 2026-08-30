import "./layout.css";

const menuItems = [
  "Dashboard",
  "환자 관리",
  "접수 / Triage",
  "검사 / 영상",
  "AI 분석",
  "판독",
  "협진",
  "처방",
  "알림",
];

export default function Sidebar() {
  return (
    <aside className="sidebar">
      <div className="sidebar-brand">
        <div className="brand-mark">B</div>

        <div>
          <strong>Brain CDSS</strong>
          <span>Clinical Decision Support</span>
        </div>
      </div>

      <nav className="sidebar-nav">
        {menuItems.map((item, index) => (
          <button
            key={item}
            type="button"
            className={`sidebar-menu ${index === 0 ? "active" : ""}`}
          >
            {item}
          </button>
        ))}
      </nav>
    </aside>
  );
}