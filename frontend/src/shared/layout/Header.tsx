import "./layout.css";

export default function Header() {
  return (
    <header className="header">
      <div>
        <h1>Clinical Decision Support System</h1>
        <p>뇌혈관질환 CDSS</p>
      </div>

      <div className="header-user">
        <div className="notification">알림</div>

        <div className="user-info">
          <strong>의료진</strong>
          <span>Role 연동 예정</span>
        </div>
      </div>
    </header>
  );
}