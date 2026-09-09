import { useState } from "react";
import type { FormEvent } from "react";

import AssessmentWorklist from "./AssessmentWorklist";
import { getPatients } from "../patients/api";
import type { Patient } from "../patients/types";

import "./css/reception_initial_assessment.css";


interface ReceptionInitialAssessmentProps {
  onOpenTriage?: (
    assessmentId: string,
    encounterId: string,
  ) => void;
}


/**
 * 접수 · 초기평가 통합 진입 화면
 *
 * Encounter API의 request/response schema가 확정되기 전이므로 이 화면은
 * 접수에 필요한 정보 구조만 보여준다. 환자 검색과 접수 완료는 API 계약이
 * 확정된 뒤 연결하며, 아래 초기평가 대기목록의 기존 Triage 흐름은 유지한다.
 */
export default function ReceptionInitialAssessment({
  onOpenTriage,
}: ReceptionInitialAssessmentProps) {
  const [patientQuery, setPatientQuery] = useState("");
  const [patientResults, setPatientResults] = useState<Patient[]>([]);
  const [selectedPatient, setSelectedPatient] = useState<Patient | null>(null);
  const [isSearchingPatients, setIsSearchingPatients] = useState(false);
  const [patientSearchError, setPatientSearchError] = useState<string | null>(null);
  const [hasSearchedPatients, setHasSearchedPatients] = useState(false);
  const [visitType, setVisitType] = useState("");
  const [department, setDepartment] = useState("");
  const [arrivedAt, setArrivedAt] = useState("");


  /**
   * Swagger에 명시된 GET /api/v1/patients?search=...만 호출한다.
   * 검색 결과는 기존 Patient 타입의 확정 필드만 사용한다.
   */
  async function handlePatientSearch(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();

    const normalizedQuery = patientQuery.trim();

    if (!normalizedQuery || isSearchingPatients) {
      return;
    }

    setIsSearchingPatients(true);
    setPatientSearchError(null);
    setHasSearchedPatients(true);

    try {
      const response = await getPatients(normalizedQuery);
      setPatientResults(response.results);
      setSelectedPatient(null);
    } catch (error) {
      console.error("접수 환자 검색 실패:", error);
      setPatientResults([]);
      setSelectedPatient(null);
      setPatientSearchError("환자 검색 결과를 불러오지 못했습니다.");
    } finally {
      setIsSearchingPatients(false);
    }
  }


  return (
    <section className="reception-initial-assessment">
      <header className="reception-initial-assessment__heading">
        <span>RECEPTION · INITIAL ASSESSMENT</span>
        <h1>접수 · 초기평가</h1>
        <p>
          환자 접수 정보를 준비하고 초기평가 대기 환자의 Triage 업무를
          이어서 진행합니다.
        </p>
      </header>


      {/* 전체 업무 순서를 한눈에 확인하는 읽기 전용 단계 표시 */}
      <ol className="reception-flow" aria-label="접수 및 초기평가 진행 단계">
        <li className="current"><span>1</span>환자 선택</li>
        <li><span>2</span>접수 정보</li>
        <li><span>3</span>Encounter 생성</li>
        <li><span>4</span>초기평가</li>
        <li><span>5</span>Triage 완료</li>
      </ol>


      {/*
        Encounter 접수 UI
        POST /api/v1/encounters의 구체 schema가 확정되기 전까지 화면 입력값을
        API payload로 변환하거나 전송하지 않는다.
      */}
      <article className="reception-card">
        <div className="reception-card__header">
          <div>
            <h2>환자 접수</h2>
            <p>환자를 확인한 뒤 방문 정보를 입력합니다.</p>
          </div>

          <span className="reception-card__status">API 연결 대기</span>
        </div>


        <div className="reception-card__body">
          <section className="reception-patient-search">
            <div className="reception-section-title">
              <strong>환자 검색 · 선택</strong>
              <span>환자번호 또는 환자명으로 대상 환자를 찾습니다.</span>
            </div>

            <form className="reception-search-row" onSubmit={handlePatientSearch}>
              <label>
                <span>환자 검색</span>
                <input
                  type="search"
                  value={patientQuery}
                  onChange={(event) => setPatientQuery(event.target.value)}
                  placeholder="환자번호 또는 환자명"
                />
              </label>

              <button
                type="submit"
                disabled={!patientQuery.trim() || isSearchingPatients}
              >
                {isSearchingPatients ? "검색 중..." : "검색"}
              </button>
            </form>

            <div className="reception-patient-results" aria-live="polite">
              {patientSearchError ? (
                <div className="reception-patient-empty is-error">
                  <strong>환자 검색에 실패했습니다.</strong>
                  <p>{patientSearchError}</p>
                </div>
              ) : !hasSearchedPatients ? (
                <div className="reception-patient-empty">
                  <strong>환자를 검색해 주세요.</strong>
                  <p>환자번호 또는 환자명으로 검색할 수 있습니다.</p>
                </div>
              ) : patientResults.length === 0 ? (
                <div className="reception-patient-empty">
                  <strong>검색 결과가 없습니다.</strong>
                  <p>검색어를 확인한 뒤 다시 시도해 주세요.</p>
                </div>
              ) : (
                <div className="reception-patient-list">
                  {patientResults.map((patient) => (
                    <button
                      key={patient.id}
                      type="button"
                      className={
                        selectedPatient?.id === patient.id
                          ? "reception-patient-item is-selected"
                          : "reception-patient-item"
                      }
                      onClick={() => setSelectedPatient(patient)}
                    >
                      <span>
                        <strong>{patient.name}</strong>
                        <small>{patient.patient_no}</small>
                      </span>
                      <span>
                        <small>{patient.birth_date ?? "생년월일 미등록"}</small>
                        <small>{patient.sex ?? "성별 미등록"}</small>
                      </span>
                    </button>
                  ))}
                </div>
              )}
            </div>

            {/* 선택한 Patient 객체와 UUID는 selectedPatient 상태에 함께 보관한다. */}
            <dl className="reception-selected-patient" aria-label="선택 환자 기본정보">
              <div><dt>환자 UUID</dt><dd>{selectedPatient?.id ?? "-"}</dd></div>
              <div><dt>환자번호</dt><dd>{selectedPatient?.patient_no ?? "-"}</dd></div>
              <div><dt>성명</dt><dd>{selectedPatient?.name ?? "-"}</dd></div>
              <div><dt>생년월일</dt><dd>{selectedPatient?.birth_date ?? "-"}</dd></div>
              <div><dt>추정 나이</dt><dd>{selectedPatient?.estimated_age ?? "-"}</dd></div>
              <div><dt>성별</dt><dd>{selectedPatient?.sex ?? "-"}</dd></div>
              <div><dt>연락처</dt><dd>{selectedPatient?.phone ?? "-"}</dd></div>
              <div><dt>상태</dt><dd>{selectedPatient?.status ?? "-"}</dd></div>
            </dl>
          </section>


          <section className="reception-information">
            <div className="reception-section-title">
              <strong>접수 정보</strong>
              <span>방문 유형, 진료과와 실제 내원시간을 확인합니다.</span>
            </div>

            <div className="reception-form-grid">
              <label>
                <span>방문 유형</span>
                <select
                  value={visitType}
                  onChange={(event) => setVisitType(event.target.value)}
                  disabled
                >
                  <option value="">Swagger enum 확인 필요</option>
                </select>
              </label>

              <label>
                <span>진료과</span>
                <select
                  value={department}
                  onChange={(event) => setDepartment(event.target.value)}
                  disabled
                >
                  <option value="">진료과 API 연결 필요</option>
                </select>
              </label>

              <label>
                <span>내원시간</span>
                <input
                  type="datetime-local"
                  value={arrivedAt}
                  onChange={(event) => setArrivedAt(event.target.value)}
                />
              </label>
            </div>
          </section>
        </div>


        <footer className="reception-card__actions">
          <p>
            Encounter schema 확정 후 선택 환자와 접수 정보를 전송할 수 있습니다.
          </p>
          <button type="button" disabled>
            접수 완료
          </button>
        </footer>
      </article>


      {/* 기존 AssessmentWorklist와 Triage 진입 callback은 그대로 재사용한다. */}
      <section className="reception-assessment-worklist">
        <div className="reception-assessment-worklist__heading">
          <div>
            <span>AFTER RECEPTION</span>
            <h2>접수 후 초기평가</h2>
            <p>
              접수가 완료되어 Encounter가 생성된 환자는 아래 대기목록에서
              초기평가를 시작합니다.
            </p>
          </div>

          <div className="reception-next-step" aria-label="다음 업무 흐름">
            초기평가 시작 → Triage 입력 → 결과 확인
          </div>
        </div>

        <AssessmentWorklist onOpenTriage={onOpenTriage} />
      </section>
    </section>
  );
}
