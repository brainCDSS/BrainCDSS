// React에서 상태 관리와 화면 최초 실행 시 API 호출을 위해 사용
import { useEffect, useState } from "react";

// GET /api/v1/patients를 호출하는 함수
import { getPatients } from "./api";

// API에서 받아오는 환자 1명의 데이터 타입
import type { Patient } from "./types";

import "./css/patients.css";

export default function Patients() {
  /**
   * API에서 받아온 환자 목록을 저장하는 상태
   *
   * 처음에는 아직 데이터를 받지 않았으므로 빈 배열 []로 시작
   */
  const [patients, setPatients] = useState<Patient[]>([]);

  /**
   * API 요청이 진행 중인지 확인하는 상태
   *
   * 처음 화면이 열릴 때는 API 요청을 해야 하므로 true
   */
  const [isLoading, setIsLoading] = useState(true);

  /**
   * API 호출 실패 시 오류 메시지를 저장하는 상태
   *
   * 오류가 없을 때는 null
   */
  const [error, setError] = useState<string | null>(null);

  /**
   * Patients 화면이 처음 열릴 때 한 번 실행
   *
   * []가 있기 때문에 렌더링될 때마다 실행되는 것이 아니라
   * 최초 1회 실행된다.
   */
  useEffect(() => {
    async function loadPatients() {
      try {
        /**
         * getPatients() 실행
         *
         * 내부적으로:
         * GET /api/v1/patients
         *
         * 현재 VITE_BACKEND_URL이 Postman Mock Server 주소이므로
         * Postman Mock API를 호출한다.
         */
        const response = await getPatients();

        /**
         * API 응답:
         *
         * {
         *   count: 2,
         *   next: null,
         *   previous: null,
         *   results: [...]
         * }
         *
         * 환자 목록은 results 안에 들어 있기 때문에
         * results만 patients 상태에 저장
         */
        setPatients(response.results);
      } catch (err) {
        // 개발자가 브라우저 Console에서 실제 오류를 확인할 수 있도록 출력
        console.error("환자 목록 조회 실패:", err);

        // 화면에 표시할 오류 메시지
        setError("환자 목록을 불러오지 못했습니다.");
      } finally {
        /**
         * 성공하든 실패하든 API 요청은 끝났으므로
         * 로딩 상태를 false로 변경
         */
        setIsLoading(false);
      }
    }

    // 위에서 만든 API 호출 함수 실행
    loadPatients();
  }, []);

  return (
    <section className="patients">
      <div className="patients-heading">
        <div>
          <span className="patients-label">PATIENTS</span>
          <h2>환자 관리</h2>
          <p>환자 정보를 조회하고 진료 업무로 이동합니다.</p>
        </div>
      </div>

      {/* 환자 검색 영역 */}
      <div className="patients-toolbar">
        <input
          type="search"
          placeholder="환자명 또는 환자번호 검색"
          aria-label="환자 검색"
        />

        {/*
          검색 기능은 아직 API와 연결하지 않았으므로
          지금은 disabled 유지
        */}
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
              <th>환자 상태</th>
            </tr>
          </thead>

          <tbody>
            {/* 1. API 호출 중 */}
            {isLoading && (
              <tr>
                <td colSpan={5}>
                  <div className="patients-empty">
                    <strong>환자 데이터를 불러오는 중입니다.</strong>
                  </div>
                </td>
              </tr>
            )}

            {/* 2. API 호출 실패 */}
            {!isLoading && error && (
              <tr>
                <td colSpan={5}>
                  <div className="patients-empty">
                    <strong>환자 목록 조회에 실패했습니다.</strong>
                    <p>{error}</p>
                  </div>
                </td>
              </tr>
            )}

            {/* 3. API 호출 성공 + 환자 데이터가 있는 경우 */}
            {!isLoading &&
              !error &&
              patients.map((patient) => (
                <tr key={patient.id}>
                  {/* 환자번호 */}
                  <td>{patient.patient_no}</td>

                  {/* 환자명 */}
                  <td>{patient.name}</td>

                  {/* 성별 - 값이 없으면 "-" 표시 */}
                  <td>{patient.sex ?? "-"}</td>

                  {/* 생년월일 - 값이 없으면 "-" 표시 */}
                  <td>{patient.birth_date ?? "-"}</td>

                  {/* 환자 상태 */}
                  <td>{patient.status}</td>
                </tr>
              ))}

            {/* 4. API는 성공했지만 환자가 0명인 경우 */}
            {!isLoading && !error && patients.length === 0 && (
              <tr>
                <td colSpan={5}>
                  <div className="patients-empty">
                    <strong>조회된 환자가 없습니다.</strong>
                    <p>조건에 해당하는 환자 데이터가 없습니다.</p>
                  </div>
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </section>
  );
}