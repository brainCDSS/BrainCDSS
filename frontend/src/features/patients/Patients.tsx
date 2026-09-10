import { useEffect, useMemo, useState } from "react";

import { getPatients } from "./api";
import type { Patient } from "./types";
import PatientChart from "./PatientChart";

import "./css/patients.css";


interface PatientsProps {
  onOpenPatient?: (patient: Patient) => void;
}

export default function Patients({ onOpenPatient }: PatientsProps) {
  const [patients, setPatients] = useState<Patient[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedPatient, setSelectedPatient] = useState<Patient | null>(null);

  /* 검색은 이미 조회된 실제 Patient 응답만 대상으로 하며 API 계약을 바꾸지 않는다. */
  const [searchText, setSearchText] = useState("");
  const [patientNo, setPatientNo] = useState("");
  const [birthDate, setBirthDate] = useState("");
  const [status, setStatus] = useState("");


  useEffect(() => {
    let active = true;

    async function loadPatients() {
      try {
        const response = await getPatients();
        if (active) setPatients(response.results);
      } catch (requestError) {
        console.error("환자 목록 조회 실패:", requestError);
        if (active) setError("환자 목록을 불러오지 못했습니다.");
      } finally {
        if (active) setIsLoading(false);
      }
    }

    void loadPatients();
    return () => { active = false; };
  }, []);


  const filteredPatients = useMemo(() => {
    const keyword = searchText.trim().toLowerCase();
    const normalizedPatientNo = patientNo.trim().toLowerCase();

    return patients.filter((patient) => {
      const matchesKeyword = !keyword ||
        patient.name.toLowerCase().includes(keyword) ||
        patient.patient_no.toLowerCase().includes(keyword);
      const matchesPatientNo = !normalizedPatientNo ||
        patient.patient_no.toLowerCase().includes(normalizedPatientNo);
      const matchesBirthDate = !birthDate || patient.birth_date === birthDate;
      const matchesStatus = !status || patient.status === status;

      return matchesKeyword && matchesPatientNo && matchesBirthDate && matchesStatus;
    });
  }, [birthDate, patientNo, patients, searchText, status]);


  function resetFilters() {
    setSearchText("");
    setPatientNo("");
    setBirthDate("");
    setStatus("");
  }


  if (selectedPatient && !onOpenPatient) {
    return (
      <PatientChart
        patient={selectedPatient}
        patients={filteredPatients.length > 0 ? filteredPatients : patients}
        onSelectPatient={setSelectedPatient}
      />
    );
  }


  return (
    <section className="patients">
      <header className="patients-heading">
        <span className="patients-label">PATIENTS</span>
        <h2>환자 관리</h2>
        <p>환자 목록을 조회하고 선택한 환자의 Patient Chart를 확인합니다.</p>
      </header>

      <section className="patients-search-card" aria-label="환자 검색 및 필터">
        <div className="patients-search-grid">
          <input
            className="patients-search-main"
            type="search"
            value={searchText}
            onChange={(event) => setSearchText(event.target.value)}
            placeholder="이름 또는 환자번호로 검색"
            aria-label="이름 또는 환자번호 검색"
          />
          <input
            type="search"
            value={patientNo}
            onChange={(event) => setPatientNo(event.target.value)}
            placeholder="환자번호"
            aria-label="환자번호 필터"
          />
          <input
            type="date"
            value={birthDate}
            onChange={(event) => setBirthDate(event.target.value)}
            aria-label="생년월일 필터"
          />
          <select
            value={status}
            onChange={(event) => setStatus(event.target.value)}
            aria-label="환자 상태 필터"
          >
            <option value="">전체 상태</option>
            <option value="ACTIVE">ACTIVE</option>
            <option value="TEMP">TEMP</option>
            <option value="MERGED">MERGED</option>
          </select>
          <button type="button" onClick={resetFilters}>초기화</button>
          <button className="is-primary" type="button">검색</button>
        </div>
      </section>

      <section className="patients-list-card">
        <div className="patients-list-header">
          <div>
            <strong>환자 목록</strong>
            <span>
              총 {filteredPatients.length}명 · 환자를 클릭하면 Patient Chart가 열립니다.
            </span>
          </div>
        </div>

        <div className="patients-table-wrap">
          <table className="patients-table">
            <thead>
              <tr>
                <th>환자번호</th>
                <th>이름</th>
                <th>생년월일</th>
                <th>나이</th>
                <th>성별</th>
                <th>연락처</th>
                <th>상태</th>
              </tr>
            </thead>
            <tbody>
              {isLoading && (
                <tr><td colSpan={7}><div className="patients-empty"><strong>환자 데이터를 불러오는 중입니다.</strong></div></td></tr>
              )}
              {!isLoading && error && (
                <tr><td colSpan={7}><div className="patients-empty"><strong>환자 목록 조회에 실패했습니다.</strong><p>{error}</p></div></td></tr>
              )}
              {!isLoading && !error && filteredPatients.map((patient) => (
                <tr key={patient.id} onClick={() => onOpenPatient ? onOpenPatient(patient) : setSelectedPatient(patient)}>
                  <td className="patients-number">{patient.patient_no}</td>
                  <td><strong>{patient.name}</strong></td>
                  <td>{patient.birth_date ?? "-"}</td>
                  <td>{patient.estimated_age !== null ? `${patient.estimated_age}세` : "-"}</td>
                  <td>{patient.sex ?? "-"}</td>
                  <td>{patient.phone ?? "-"}</td>
                  <td><span className={`patients-status is-${patient.status.toLowerCase()}`}>{patient.status}</span></td>
                </tr>
              ))}
              {!isLoading && !error && filteredPatients.length === 0 && (
                <tr><td colSpan={7}><div className="patients-empty"><strong>조회된 환자가 없습니다.</strong><p>검색 조건을 확인해 주세요.</p></div></td></tr>
              )}
            </tbody>
          </table>
        </div>
      </section>
    </section>
  );
}
