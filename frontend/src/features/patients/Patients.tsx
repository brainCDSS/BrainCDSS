import "./patients.css";

export default function Patients() {
  return (
    <section className="patients">
      <div className="patients-heading">
        <div>
          <span className="patients-label">PATIENTS</span>
          <h2>환자 관리</h2>
          <p>환자 정보를 조회하고 진료 업무로 이동합니다.</p>
        </div>
      </div>

      <div className="patients-toolbar">
        <input
          type="search"
          placeholder="환자명 또는 환자번호 검색"
          aria-label="환자 검색"
        />

        <button type="button" disabled>
          검색
        </button>
      </div>

      <div className="patients-table-wrap">
        <table className="patients-table">
          <thead>
            <tr>
              <th>환자번호</th>
              <th>환자명</th>
              <th>성별</th>
              <th>생년월일</th>
              <th>진료 상태</th>
              <th>담당 의료진</th>
            </tr>
          </thead>

          <tbody>
            <tr>
              <td colSpan={6}>
                <div className="patients-empty">
                  <strong>환자 데이터 연동 예정</strong>
                  <p>
                    승인된 환자 조회 API 연결 후 환자 목록을 표시합니다.
                  </p>
                </div>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </section>
  );
}