import { useEffect, useState } from "react";
import type { FormEvent } from "react";

import { getStaffAppointments } from "../appointments/api";
import type { StaffAppointment } from "../appointments/types";
import { createPatient, getPatients } from "../patients/api";
import type { Patient } from "../patients/types";
import {
  createEncounter,
  getAssessmentDetail,
  getAssessmentWorklist,
  startAssessment,
  updateAssessment,
} from "./api";
import type {
  AssessmentDetailResponse,
  AssessmentItem,
  EncounterResponse,
} from "./types";

import "./css/reception_initial_assessment.css";


type Step = 1 | 2 | 3 | 4 | 5;
type Sex = "M" | "F" | "U";


interface ReceptionInitialAssessmentProps {
  onOpenTriage?: (
    assessmentId: string,
    encounterId: string,
  ) => void;
}


const STEPS = [
  "환자 검색",
  "환자 확인",
  "접수",
  "초기평가",
  "완료",
];


const sexLabel = (sex: string | null) =>
  sex === "M"
    ? "남"
    : sex === "F"
      ? "여"
      : "미상";


const phoneLabel = (phone: string | null) => {
  if (!phone) {
    return "-";
  }

  const digits = phone.replace(/\D/g, "");

  if (digits.length === 11) {
    return digits.replace(
      /(\d{3})(\d{4})(\d{4})/,
      "$1-$2-$3",
    );
  }

  if (digits.length === 10) {
    return digits.replace(
      /(\d{3})(\d{3})(\d{4})/,
      "$1-$2-$3",
    );
  }

  return phone;
};


const dateTimeLocal = (
  value?: string | null,
) => value ? value.slice(0, 16) : "";


const apiError = (
  error: unknown,
  fallback: string,
) => {
  if (
    error instanceof Error &&
    error.message.includes(":403")
  ) {
    return "현재 계정에는 이 작업 권한이 없습니다.";
  }

  if (
    error instanceof Error &&
    error.message.includes(":409")
  ) {
    return "현재 방문에 이미 진행 중인 접수 또는 초기평가가 있습니다.";
  }

  return fallback;
};


export default function ReceptionInitialAssessment(
  props: ReceptionInitialAssessmentProps,
) {
  void props.onOpenTriage;

  const [step, setStep] = useState<Step>(1);

  const [query, setQuery] = useState("");
  const [results, setResults] = useState<Patient[]>([]);
  const [
    selectedPatient,
    setSelectedPatient,
  ] = useState<Patient | null>(null);

  const [searched, setSearched] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(
    null,
  );

  const [showCreate, setShowCreate] =
    useState(false);

  const [
    newPatient,
    setNewPatient,
  ] = useState<{
    name: string;
    birth_date: string;
    sex: Sex;
    phone: string;
  }>({
    name: "",
    birth_date: "",
    sex: "U",
    phone: "",
  });

  const [
    visitType,
    setVisitType,
  ] = useState<
    "OUTPATIENT" | "EMERGENCY"
  >("EMERGENCY");

  const [
    appointments,
    setAppointments,
  ] = useState<StaffAppointment[]>([]);

  const [
    appointmentId,
    setAppointmentId,
  ] = useState("");

  const [
    encounter,
    setEncounter,
  ] = useState<EncounterResponse | null>(null);

  const [
    assessment,
    setAssessment,
  ] = useState<
    AssessmentDetailResponse | null
  >(null);

  const [
    symptomNote,
    setSymptomNote,
  ] = useState("");

  const [onsetAt, setOnsetAt] = useState("");
  const [lkwAt, setLkwAt] = useState("");

  const [fastFace, setFastFace] =
    useState("");

  const [fastArm, setFastArm] =
    useState("");

  const [bpSys, setBpSys] =
    useState("");

  const [
    heartRate,
    setHeartRate,
  ] = useState("");


  /*
   * 외래 접수인 경우
   * 선택한 환자의 CONFIRMED 예약만 조회
   */
  useEffect(() => {
    if (
      step !== 3 ||
      visitType !== "OUTPATIENT" ||
      !selectedPatient
    ) {
      return;
    }

    setLoading(true);
    setError(null);
    setAppointmentId("");

    getStaffAppointments({
      status: "CONFIRMED",
      pageSize: 100,
    })
      .then((response) => {
        const list =
          response.results ??
          response.appointments ??
          [];

        setAppointments(
          list.filter(
            (item) =>
              (
                item.patient?.id ??
                item.patient_id
              ) === selectedPatient.id,
          ),
        );
      })
      .catch((requestError) => {
        setError(
          apiError(
            requestError,
            "확정 예약을 불러오지 못했습니다.",
          ),
        );
      })
      .finally(() => {
        setLoading(false);
      });
  }, [
    selectedPatient,
    step,
    visitType,
  ]);


  /*
   * 환자 검색
   */
  async function searchPatients(
    event: FormEvent,
  ) {
    event.preventDefault();

    const normalizedQuery =
      query.trim();

    if (!normalizedQuery) {
      return;
    }

    setLoading(true);
    setError(null);
    setSearched(true);
    setSelectedPatient(null);
    setShowCreate(false);

    try {
      const response =
        await getPatients(
          normalizedQuery,
        );

      setResults(
        response.results,
      );
    } catch (requestError) {
      setResults([]);

      setError(
        apiError(
          requestError,
          "환자 검색에 실패했습니다.",
        ),
      );
    } finally {
      setLoading(false);
    }
  }


  /*
   * 신규 환자 등록 화면 열기
   *
   * 검색했던 이름을 신규등록 이름에 자동 입력.
   * 단, input은 readOnly가 아니므로
   * 사용자가 수정할 수 있다.
   */
  function openCreatePatient() {
    setNewPatient(
      (current) => ({
        ...current,
        name: query.trim(),
      }),
    );

    setShowCreate(true);
    setError(null);
  }


  /*
   * 신규 환자 등록 취소
   */
  function closeCreatePatient() {
    setShowCreate(false);

    setNewPatient({
      name: "",
      birth_date: "",
      sex: "U",
      phone: "",
    });
  }


  /*
   * 신규 환자 등록
   *
   * birth_date는 type="date"에서 받은
   * YYYY-MM-DD 값을 그대로 API로 전달한다.
   */
  async function registerPatient(
    event: FormEvent,
  ) {
    event.preventDefault();

    setLoading(true);
    setError(null);

    try {
      const patient =
        await createPatient({
          name:
            newPatient.name.trim(),
          birth_date:
            newPatient.birth_date,
          sex:
            newPatient.sex,
          phone:
            newPatient.phone.trim(),
        });

      setSelectedPatient(
        patient,
      );

      setStep(2);
      setShowCreate(false);

      setNewPatient({
        name: "",
        birth_date: "",
        sex: "U",
        phone: "",
      });
    } catch (requestError) {
      setError(
        apiError(
          requestError,
          "신규 환자를 등록하지 못했습니다.",
        ),
      );
    } finally {
      setLoading(false);
    }
  }


  /*
   * Encounter 생성
   */
  async function registerEncounter() {
    if (
      !selectedPatient ||
      (
        visitType === "OUTPATIENT" &&
        !appointmentId
      )
    ) {
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const created =
        await createEncounter({
          patient_id:
            selectedPatient.id,

          encounter_type:
            visitType,

          ...(visitType ===
          "OUTPATIENT"
            ? {
                appointment_id:
                  appointmentId,
              }
            : {}),
        });

      if (
        !created.encounter_id
      ) {
        throw new Error(
          "ENCOUNTER_ID_MISSING",
        );
      }

      setEncounter(created);

      /*
       * 같은 Encounter에 기존 초기평가가
       * 있는지 확인
       */
      const worklist =
        await getAssessmentWorklist();

      const existing =
        worklist.results.find(
          (item) =>
            item.encounter_id ===
              created.encounter_id &&
            item.assessment_id,
        );

      let detail:
        AssessmentDetailResponse;

      if (
        existing?.assessment_id
      ) {
        detail =
          await getAssessmentDetail(
            existing.assessment_id,
          );
      } else {
        const started =
          await startAssessment({
            encounter_id:
              created.encounter_id,
          });

        detail = {
          assessment_id:
            started.assessment_id,

          encounter_id:
            started.encounter_id,

          status:
            started.status,

          total_score: null,
          triage_priority: null,
          items: [],
        };
      }

      setAssessment(detail);
      hydrateAssessment(detail);
      setStep(4);
    } catch (requestError) {
      setError(
        apiError(
          requestError,
          "접수를 완료하지 못했습니다.",
        ),
      );
    } finally {
      setLoading(false);
    }
  }


  /*
   * 기존 초기평가 값 화면에 복원
   */
  function hydrateAssessment(
    detail:
      AssessmentDetailResponse,
  ) {
    setSymptomNote(
      detail.symptom_note ?? "",
    );

    setOnsetAt(
      dateTimeLocal(
        detail.onset_at,
      ),
    );

    setLkwAt(
      dateTimeLocal(
        detail.lkw_at,
      ),
    );

    const value = (
      code: string,
    ) =>
      detail.items.find(
        (item) =>
          item.item_code === code,
      );

    setFastFace(
      value("FAST_FACE")
        ?.value_text ?? "",
    );

    setFastArm(
      value("FAST_ARM")
        ?.value_text ?? "",
    );

    setBpSys(
      String(
        value("BP_SYS")
          ?.value_numeric ?? "",
      ),
    );

    setHeartRate(
      String(
        value("HEART_RATE")
          ?.value_numeric ?? "",
      ),
    );
  }


  /*
   * 초기평가 임시저장
   */
  async function saveAssessment() {
    if (
      !assessment ||
      assessment.status ===
        "COMPLETED"
    ) {
      return;
    }

    const items:
      AssessmentItem[] = [];

    if (fastFace) {
      items.push({
        item_code:
          "FAST_FACE",
        value_text:
          fastFace,
      });
    }

    if (fastArm) {
      items.push({
        item_code:
          "FAST_ARM",
        value_text:
          fastArm,
      });
    }

    if (bpSys) {
      items.push({
        item_code:
          "BP_SYS",
        value_numeric:
          Number(bpSys),
        unit:
          "mmHg",
      });
    }

    if (heartRate) {
      items.push({
        item_code:
          "HEART_RATE",
        value_numeric:
          Number(heartRate),
        unit:
          "bpm",
      });
    }

    setLoading(true);
    setError(null);

    try {
      const saved =
        await updateAssessment(
          assessment.assessment_id,
          {
            onset_at:
              onsetAt || null,

            lkw_at:
              lkwAt || null,

            symptom_note:
              symptomNote,

            items,
          },
        );

      setAssessment(
        (current) =>
          current
            ? {
                ...current,
                status:
                  saved.status,
                items:
                  saved.items,
              }
            : current,
      );
    } catch (requestError) {
      setError(
        apiError(
          requestError,
          "초기평가를 저장하지 못했습니다.",
        ),
      );
    } finally {
      setLoading(false);
    }
  }


  /*
   * 새 접수 시작
   */
  function reset() {
    setStep(1);

    setQuery("");
    setResults([]);
    setSelectedPatient(null);
    setSearched(false);

    setShowCreate(false);

    setError(null);

    setEncounter(null);
    setAssessment(null);

    setAppointments([]);
    setAppointmentId("");

    setVisitType(
      "EMERGENCY",
    );

    setNewPatient({
      name: "",
      birth_date: "",
      sex: "U",
      phone: "",
    });

    setSymptomNote("");
    setOnsetAt("");
    setLkwAt("");

    setFastFace("");
    setFastArm("");

    setBpSys("");
    setHeartRate("");
  }


  return (
    <section className="reception-initial-assessment">

      <header className="reception-initial-assessment__heading">
        <span>
          RECEPTION · INITIAL ASSESSMENT
        </span>

        <h1>
          접수 · 초기평가
        </h1>

        <p>
          환자 확인부터 접수와
          초기평가까지 한 화면에서
          진행합니다.
        </p>
      </header>


      <ol
        className="reception-flow"
        aria-label="접수 및 초기평가 진행 단계"
      >
        {STEPS.map(
          (label, index) => (
            <li
              key={label}
              className={
                step === index + 1
                  ? "current"
                  : step >
                      index + 1
                    ? "done"
                    : ""
              }
            >
              <span>
                {index + 1}
              </span>

              {label}
            </li>
          ),
        )}
      </ol>


      {error && (
        <div
          className="reception-alert"
          role="alert"
        >
          {error}
        </div>
      )}


      {/* =========================
          STEP 1 환자 검색
      ========================== */}
      {step === 1 && (
        <article className="reception-card">

          <div className="reception-card__header">
            <div>
              <h2>
                환자 검색
              </h2>

              <p>
                환자명 또는 환자번호로
                검색합니다.
              </p>
            </div>
          </div>


          <div className="reception-step-body">

            <form
              className="reception-search-row"
              onSubmit={
                searchPatients
              }
            >
              <label>
                <span>
                  환자명 / 환자번호
                </span>

                <input
                  type="search"
                  value={query}
                  onChange={(
                    event,
                  ) =>
                    setQuery(
                      event.target
                        .value,
                    )
                  }
                  placeholder="환자명 또는 환자번호"
                />
              </label>

              <button
                type="submit"
                disabled={
                  !query.trim() ||
                  loading
                }
              >
                {loading
                  ? "검색 중..."
                  : "검색"}
              </button>
            </form>


            {!searched ? (
              <div className="reception-patient-empty">
                검색어를 입력해 주세요.
              </div>
            ) : loading ? (
              <div className="reception-patient-empty">
                환자를 검색하고 있습니다.
              </div>
            ) : results.length ? (
              <div className="reception-search-layout">

                <div className="reception-patient-list">

                  {results.map(
                    (patient) => (
                      <button
                        key={
                          patient.id
                        }
                        type="button"
                        className={
                          selectedPatient
                            ?.id ===
                          patient.id
                            ? "reception-patient-item is-selected"
                            : "reception-patient-item"
                        }
                        onClick={() =>
                          setSelectedPatient(
                            patient,
                          )
                        }
                      >
                        <span>
                          <strong>
                            {
                              patient.name
                            }
                          </strong>

                          <small>
                            {
                              patient.patient_no
                            }
                          </small>
                        </span>

                        <span>
                          <small>
                            {patient.birth_date ??
                              "-"}{" "}
                            ·{" "}
                            {sexLabel(
                              patient.sex,
                            )}
                          </small>

                          <small>
                            {phoneLabel(
                              patient.phone,
                            )}{" "}
                            ·{" "}
                            {
                              patient.status
                            }
                          </small>
                        </span>
                      </button>
                    ),
                  )}
                </div>

                <PatientContext
                  patient={
                    selectedPatient
                  }
                />
              </div>
            ) : (
              <div className="reception-patient-empty">

                <strong>
                  등록된 환자가 없습니다.
                </strong>

                <button
                  type="button"
                  onClick={
                    openCreatePatient
                  }
                >
                  + 신규 환자 등록
                </button>
              </div>
            )}


            {selectedPatient && (
              <footer className="reception-card__actions">
                <span />

                <button
                  type="button"
                  onClick={() =>
                    setStep(2)
                  }
                >
                  이 환자로 진행
                </button>
              </footer>
            )}
          </div>
        </article>
      )}


      {/* =========================
          신규 환자 등록
      ========================== */}
      {step === 1 &&
        showCreate && (
          <article className="reception-card reception-create-card">

            <div className="reception-card__header">
              <div>
                <h2>
                  신규 환자 등록
                </h2>

                <p>
                  환자번호는 Backend에서
                  자동 생성됩니다.
                </p>
              </div>
            </div>


            <form
              className="reception-create-form"
              onSubmit={
                registerPatient
              }
            >

              <label>
                이름

                <input
                  required
                  value={
                    newPatient.name
                  }
                  onChange={(
                    event,
                  ) =>
                    setNewPatient(
                      (current) => ({
                        ...current,
                        name:
                          event.target
                            .value,
                      }),
                    )
                  }
                />
              </label>


              <label>
                생년월일

                <input
                  required
                  type="date"
                  value={
                    newPatient.birth_date
                  }
                  onChange={(
                    event,
                  ) =>
                    setNewPatient(
                      (current) => ({
                        ...current,
                        birth_date:
                          event.target
                            .value,
                      }),
                    )
                  }
                />
              </label>


              <label>
                성별

                <select
                  value={
                    newPatient.sex
                  }
                  onChange={(
                    event,
                  ) =>
                    setNewPatient(
                      (current) => ({
                        ...current,
                        sex:
                          event.target
                            .value as Sex,
                      }),
                    )
                  }
                >
                  <option value="M">
                    남
                  </option>

                  <option value="F">
                    여
                  </option>

                  <option value="U">
                    미상
                  </option>
                </select>
              </label>


              <label>
                전화번호

                <input
                  inputMode="tel"
                  value={
                    newPatient.phone
                  }
                  onChange={(
                    event,
                  ) =>
                    setNewPatient(
                      (current) => ({
                        ...current,
                        phone:
                          event.target
                            .value,
                      }),
                    )
                  }
                  placeholder="010-0000-0000"
                />
              </label>


              <div>
                <button
                  type="button"
                  onClick={
                    closeCreatePatient
                  }
                >
                  취소
                </button>

                <button
                  type="submit"
                  disabled={loading}
                >
                  {loading
                    ? "등록 중..."
                    : "등록"}
                </button>
              </div>
            </form>
          </article>
        )}


      {/* =========================
          STEP 2 환자 확인
      ========================== */}
      {step === 2 &&
        selectedPatient && (
          <article className="reception-card">

            <div className="reception-card__header">
              <div>
                <h2>
                  환자 확인
                </h2>

                <p>
                  접수할 환자의 기본정보를
                  확인해 주세요.
                </p>
              </div>
            </div>


            <div className="reception-step-body">

              <PatientContext
                patient={
                  selectedPatient
                }
              />

              <footer className="reception-card__actions">

                <button
                  className="secondary"
                  type="button"
                  onClick={() =>
                    setStep(1)
                  }
                >
                  다시 검색
                </button>

                <button
                  type="button"
                  onClick={() =>
                    setStep(3)
                  }
                >
                  접수 진행
                </button>
              </footer>
            </div>
          </article>
        )}


      {/* =========================
          STEP 3 접수
      ========================== */}
      {step === 3 &&
        selectedPatient && (
          <article className="reception-card">

            <div className="reception-card__header">
              <div>
                <h2>
                  접수
                </h2>

                <p>
                  {selectedPatient.name}{" "}
                  환자의 이번 방문을
                  등록합니다.
                </p>
              </div>
            </div>


            <div className="reception-step-body">

              <div className="reception-segments">

                <button
                  type="button"
                  className={
                    visitType ===
                    "OUTPATIENT"
                      ? "is-active"
                      : ""
                  }
                  onClick={() =>
                    setVisitType(
                      "OUTPATIENT",
                    )
                  }
                >
                  외래
                </button>

                <button
                  type="button"
                  className={
                    visitType ===
                    "EMERGENCY"
                      ? "is-active"
                      : ""
                  }
                  onClick={() =>
                    setVisitType(
                      "EMERGENCY",
                    )
                  }
                >
                  응급
                </button>
              </div>


              <p className="reception-hint">
                내원시간은 접수 완료 시
                자동 기록됩니다.
              </p>


              <label className="reception-gap-field">
                진료과

                <select disabled>
                  <option>
                    의료진용 진료과 조회 API 필요
                  </option>
                </select>
              </label>


              {visitType ===
                "OUTPATIENT" && (
                <label className="reception-gap-field">
                  확정 예약

                  <select
                    value={
                      appointmentId
                    }
                    onChange={(
                      event,
                    ) =>
                      setAppointmentId(
                        event.target
                          .value,
                      )
                    }
                  >
                    <option value="">
                      예약 선택
                    </option>

                    {appointments.map(
                      (item) => (
                        <option
                          key={
                            item.appointment_id
                          }
                          value={
                            item.appointment_id
                          }
                        >
                          {item.start_at ??
                            item.slot
                              ?.start_at ??
                            item.appointment_id}
                        </option>
                      ),
                    )}
                  </select>

                  {!loading &&
                    appointments.length ===
                      0 && (
                      <small>
                        연결 가능한
                        CONFIRMED 예약이
                        없습니다.
                      </small>
                    )}
                </label>
              )}


              <footer className="reception-card__actions">

                <button
                  className="secondary"
                  type="button"
                  onClick={() =>
                    setStep(2)
                  }
                >
                  이전
                </button>

                <button
                  type="button"
                  disabled={
                    loading ||
                    (
                      visitType ===
                        "OUTPATIENT" &&
                      !appointmentId
                    )
                  }
                  onClick={() =>
                    void registerEncounter()
                  }
                >
                  {loading
                    ? "처리 중..."
                    : "접수 완료"}
                </button>
              </footer>
            </div>
          </article>
        )}


      {/* =========================
          STEP 4 초기평가
      ========================== */}
      {step === 4 &&
        selectedPatient &&
        encounter &&
        assessment && (
          <article className="reception-card">

            <div className="reception-card__header">
              <div>
                <h2>
                  초기평가
                </h2>

                <p>
                  {encounter.encounter_no}{" "}
                  ·{" "}
                  {assessment.status}
                </p>
              </div>
            </div>


            <fieldset
              className="assessment-form"
              disabled={
                assessment.status ===
                "COMPLETED"
              }
            >

              <label className="wide">
                1. 주호소

                <textarea
                  value={symptomNote}
                  onChange={(
                    event,
                  ) =>
                    setSymptomNote(
                      event.target
                        .value,
                    )
                  }
                />
              </label>


              <section>
                <strong>
                  2. 발병 시각 / LKW
                </strong>

                <div>
                  <label>
                    발병 시각

                    <input
                      type="datetime-local"
                      value={onsetAt}
                      onChange={(
                        event,
                      ) =>
                        setOnsetAt(
                          event.target
                            .value,
                        )
                      }
                    />
                  </label>

                  <label>
                    LKW

                    <input
                      type="datetime-local"
                      value={lkwAt}
                      onChange={(
                        event,
                      ) =>
                        setLkwAt(
                          event.target
                            .value,
                        )
                      }
                    />
                  </label>
                </div>
              </section>


              <section>
                <strong>
                  3. 의식 상태
                </strong>

                <div className="assessment-gap">
                  허용된 의식 상태
                  item_code 확인이
                  필요합니다.
                </div>
              </section>


              <section>
                <strong>
                  4. Vital
                </strong>

                <div className="vital-row">

                  <label>
                    수축기 혈압

                    <input
                      type="number"
                      value={bpSys}
                      onChange={(
                        event,
                      ) =>
                        setBpSys(
                          event.target
                            .value,
                        )
                      }
                    />

                    <small>
                      mmHg
                    </small>
                  </label>


                  <label>
                    이완기 혈압
                    <input disabled />
                  </label>


                  <label>
                    맥박

                    <input
                      type="number"
                      value={
                        heartRate
                      }
                      onChange={(
                        event,
                      ) =>
                        setHeartRate(
                          event.target
                            .value,
                        )
                      }
                    />

                    <small>
                      bpm
                    </small>
                  </label>


                  <label>
                    체온
                    <input disabled />
                  </label>
                </div>
              </section>


              <section>
                <strong>
                  확인된 FAST 항목
                </strong>

                <div>

                  <label>
                    안면 비대칭

                    <select
                      value={fastFace}
                      onChange={(
                        event,
                      ) =>
                        setFastFace(
                          event.target
                            .value,
                        )
                      }
                    >
                      <option value="">
                        미입력
                      </option>

                      <option value="NORMAL">
                        정상
                      </option>

                      <option value="ABNORMAL">
                        이상
                      </option>
                    </select>
                  </label>


                  <label>
                    팔 근력 저하

                    <select
                      value={fastArm}
                      onChange={(
                        event,
                      ) =>
                        setFastArm(
                          event.target
                            .value,
                        )
                      }
                    >
                      <option value="">
                        미입력
                      </option>

                      <option value="NORMAL">
                        정상
                      </option>

                      <option value="ABNORMAL">
                        이상
                      </option>
                    </select>
                  </label>
                </div>
              </section>


              <section>
                <strong>
                  5. 주요 과거력
                </strong>

                <div className="assessment-gap">
                  조회·저장 API 연동이
                  필요합니다.
                </div>
              </section>


              <section>
                <strong>
                  6. 복용약 / 알레르기
                </strong>

                <div className="assessment-gap">
                  현재 환자 정보에서
                  조회할 수 없습니다.
                </div>
              </section>
            </fieldset>


            <footer className="reception-card__actions">

              <span>
                신경과 의료진 목록 API가
                없어 완료 처리는
                비활성화됩니다.
              </span>

              <div>
                <button
                  className="secondary"
                  type="button"
                  disabled={
                    loading ||
                    assessment.status ===
                      "COMPLETED"
                  }
                  onClick={() =>
                    void saveAssessment()
                  }
                >
                  임시저장
                </button>

                <button
                  type="button"
                  disabled
                >
                  초기평가 완료
                </button>
              </div>
            </footer>
          </article>
        )}


      {/* =========================
          STEP 5 완료
      ========================== */}
      {step === 5 &&
        selectedPatient &&
        encounter &&
        assessment && (
          <article className="reception-card reception-complete">

            <strong>
              ✓ 접수 · 초기평가 완료
            </strong>

            <PatientContext
              patient={
                selectedPatient
              }
            />

            <dl>
              <div>
                <dt>
                  Encounter 번호
                </dt>

                <dd>
                  {
                    encounter.encounter_no
                  }
                </dd>
              </div>

              <div>
                <dt>
                  접수 상태
                </dt>

                <dd>
                  {encounter.status}
                </dd>
              </div>

              <div>
                <dt>
                  내원시간
                </dt>

                <dd>
                  {
                    encounter.arrived_at
                  }
                </dd>
              </div>

              <div>
                <dt>
                  초기평가 상태
                </dt>

                <dd>
                  {
                    assessment.status
                  }
                </dd>
              </div>

              {assessment.triage_priority && (
                <div>
                  <dt>
                    Triage Priority
                  </dt>

                  <dd>
                    {
                      assessment.triage_priority
                    }
                  </dd>
                </div>
              )}
            </dl>

            <button
              type="button"
              onClick={reset}
            >
              새 접수 시작
            </button>
          </article>
        )}
    </section>
  );
}


function PatientContext({
  patient,
}: {
  patient: Patient | null;
}) {
  if (!patient) {
    return (
      <div className="reception-patient-empty">
        환자를 선택하면 기본정보가
        표시됩니다.
      </div>
    );
  }

  return (
    <dl className="reception-selected-patient">

      <div>
        <dt>
          이름
        </dt>

        <dd>
          {patient.name}
        </dd>
      </div>

      <div>
        <dt>
          환자번호
        </dt>

        <dd>
          {patient.patient_no}
        </dd>
      </div>

      <div>
        <dt>
          생년월일
        </dt>

        <dd>
          {patient.birth_date ?? "-"}
        </dd>
      </div>

      <div>
        <dt>
          성별
        </dt>

        <dd>
          {sexLabel(patient.sex)}
        </dd>
      </div>

      <div>
        <dt>
          전화번호
        </dt>

        <dd>
          {phoneLabel(patient.phone)}
        </dd>
      </div>

      <div>
        <dt>
          상태
        </dt>

        <dd>
          {patient.status}
        </dd>
      </div>
    </dl>
  );
}