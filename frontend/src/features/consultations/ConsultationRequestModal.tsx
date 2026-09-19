import {
  useEffect,
  useState,
} from "react";

import type {
  FormEvent,
} from "react";

import {
  getClinicians,
} from "../assessments/api";

import type {
  Clinician,
} from "../assessments/types";

import {
  getActiveHospitals,
  getHospitalDetail,
} from "../appointments/api";

import {
  loadAuthSession,
} from "../auth/session";

import {
  getActiveEncounter,
} from "../medication-safety/api";

import type {
  EncounterListItem,
} from "../medication-safety/types";

import {
  getPatients,
} from "../patients/api";

import type {
  Patient,
} from "../patients/types";

import {
  createConsultation,
} from "./api";

import type {
  ConsultationPriority,
  ConsultationType,
} from "./types";

import "./css/consultation_request_modal.css";


interface ConsultationRequestModalProps {
  open: boolean;
  onClose: () => void;
  onCreated: () => void;
}


function matchesConsultationDepartment(
  consultationType: ConsultationType,
  code: string,
  name: string,
): boolean {
  const normalizedCode =
    code.trim().toUpperCase();

  const normalizedName =
    name.trim().toLowerCase();

  if (consultationType === "RADIOLOGY") {
    return (
      [
        "RADIOLOGY",
        "FT-RAD",
        "LOCAL_CHAT_RADIOLOGY",
      ].includes(normalizedCode) ||
      normalizedName.includes("영상의학") ||
      normalizedName.includes("radiology")
    );
  }

  return (
    [
      "NEUROSURGERY",
      "FT-NS",
      "LOCAL_CHAT_NEUROSURGERY",
    ].includes(normalizedCode) ||
    normalizedName.includes("신경외과") ||
    normalizedName.includes("neurosurgery")
  );
}


export default function ConsultationRequestModal({
  open,
  onClose,
  onCreated,
}: ConsultationRequestModalProps) {

  const currentUser =
    loadAuthSession()?.user;

  const [
    patientSearch,
    setPatientSearch,
  ] = useState("");

  const [
    patients,
    setPatients,
  ] = useState<Patient[]>([]);

  const [
    patientsLoading,
    setPatientsLoading,
  ] = useState(false);

  const [
    patientsError,
    setPatientsError,
  ] = useState<string | null>(null);

  const [
    selectedPatient,
    setSelectedPatient,
  ] = useState<Patient | null>(null);

  const [
    activeEncounter,
    setActiveEncounter,
  ] = useState<EncounterListItem | null>(null);

  const [
    encounterLoading,
    setEncounterLoading,
  ] = useState(false);

  const [
    encounterError,
    setEncounterError,
  ] = useState<string | null>(null);

  const [
    consultationType,
    setConsultationType,
  ] = useState<ConsultationType>(
    "RADIOLOGY",
  );

  const [
    selectedClinicianId,
    setSelectedClinicianId,
  ] = useState("");

  const [
    clinicians,
    setClinicians,
  ] = useState<Clinician[]>([]);

  const [
    cliniciansLoading,
    setCliniciansLoading,
  ] = useState(false);

  const [
    cliniciansError,
    setCliniciansError,
  ] = useState<string | null>(null);

  const [
    priority,
    setPriority,
  ] = useState<ConsultationPriority>(
    "ROUTINE",
  );

  const [
    reason,
    setReason,
  ] = useState("");

  const [
    submitting,
    setSubmitting,
  ] = useState(false);

  const [
    requestError,
    setRequestError,
  ] = useState<string | null>(null);


  async function loadPatients(
    search = patientSearch,
  ) {
    try {
      setPatientsLoading(true);
      setPatientsError(null);

      const response =
        await getPatients(
          search.trim() || undefined,
          1,
          "mine",
        );

      setPatients(response.results);
    } catch {
      setPatients([]);
      setPatientsError(
        "환자 목록을 불러오지 못했습니다.",
      );
    } finally {
      setPatientsLoading(false);
    }
  }


  useEffect(() => {
    if (!open) {
      return;
    }

    setPatientSearch("");
    setPatients([]);
    setSelectedPatient(null);
    setActiveEncounter(null);
    setEncounterError(null);

    setConsultationType("RADIOLOGY");
    setSelectedClinicianId("");
    setPriority("ROUTINE");
    setReason("");
    setRequestError(null);

    void loadPatients("");
  }, [open]);


  useEffect(() => {
    if (!open) {
      return;
    }

    let active = true;

    setSelectedClinicianId("");
    setClinicians([]);
    setCliniciansLoading(true);
    setCliniciansError(null);

    async function loadClinicians() {
      try {
        const activeHospitals =
          await getActiveHospitals();

        const hospitalIds =
          Array.from(
            new Set(
              [
                currentUser?.hospital?.id,
                ...activeHospitals.results.map(
                  (hospital) => hospital.id,
                ),
              ].filter(
                (id): id is string =>
                  Boolean(id),
              ),
            ),
          );

        const hospitals =
          await Promise.all(
            hospitalIds.map(
              getHospitalDetail,
            ),
          );

        const departments =
          hospitals
            .flatMap(
              (hospital) =>
                hospital.departments,
            )
            .filter(
              (item) =>
                matchesConsultationDepartment(
                  consultationType,
                  item.code,
                  item.name,
                ),
            );

        if (departments.length === 0) {
          if (active) {
            setClinicians([]);
            setCliniciansError(
              "선택한 협진 진료과를 찾을 수 없습니다.",
            );
          }

          return;
        }

        const responses =
          await Promise.all(
            departments.map(
              (department) =>
                getClinicians(
                  department.id,
                ),
            ),
          );

        const clinicianMap =
          new Map<string, Clinician>();

        responses.forEach(
          (response) => {
            response.clinicians
              .filter(
                (clinician) =>
                  clinician.is_active,
              )
              .forEach(
                (clinician) => {
                  clinicianMap.set(
                    clinician.user_id,
                    clinician,
                  );
                },
              );
          },
        );

        if (active) {
          setClinicians(
            Array.from(
              clinicianMap.values(),
            ),
          );

          if (
            clinicianMap.size === 0
          ) {
            setCliniciansError(
              "선택한 협진 진료과에 활성 의료진이 없습니다.",
            );
          }
        }
      } catch {
        if (active) {
          setClinicians([]);
          setCliniciansError(
            "협진 의료진을 불러오지 못했습니다.",
          );
        }
      } finally {
        if (active) {
          setCliniciansLoading(false);
        }
      }
    }

    void loadClinicians();

    return () => {
      active = false;
    };
  }, [
    open,
    consultationType,
    currentUser?.hospital?.id,
  ]);


  async function selectPatient(
    patient: Patient,
  ) {
    setSelectedPatient(patient);
    setActiveEncounter(null);
    setEncounterError(null);
    setRequestError(null);

    try {
      setEncounterLoading(true);

      const encounter =
        await getActiveEncounter(
          patient.id,
        );

      setActiveEncounter(encounter);

      if (!encounter) {
        setEncounterError(
          "현재 진행 중인 Encounter가 없습니다.",
        );
      }
    } catch {
      setEncounterError(
        "환자의 Encounter를 확인하지 못했습니다.",
      );
    } finally {
      setEncounterLoading(false);
    }
  }


  function closeModal() {
    if (submitting) {
      return;
    }

    onClose();
  }


  async function submitRequest(
    event: FormEvent<HTMLFormElement>,
  ) {
    event.preventDefault();

    const encounterId =
      activeEncounter?.encounter_id ??
      activeEncounter?.id ??
      "";

    if (!selectedPatient) {
      setRequestError(
        "협진을 요청할 환자를 선택해 주세요.",
      );

      return;
    }

    if (!encounterId) {
      setRequestError(
        "선택한 환자의 활성 Encounter가 없습니다.",
      );

      return;
    }

    if (!selectedClinicianId) {
      setRequestError(
        "협진 의료진을 선택해 주세요.",
      );

      return;
    }

    const trimmedReason =
      reason.trim();

    if (!trimmedReason) {
      setRequestError(
        "협진 요청 사유를 입력해 주세요.",
      );

      return;
    }

    try {
      setSubmitting(true);
      setRequestError(null);

      await createConsultation({
        encounter_id: encounterId,
        consultation_type:
          consultationType,
        assigned_to_id:
          selectedClinicianId,
        priority,
        reason: trimmedReason,
      });

      onCreated();
      onClose();
    } catch (error) {
      const duplicate =
        error instanceof Error &&
        error.message.includes(
          "CONSULTATION_ACTIVE_DUPLICATE",
        );

      setRequestError(
        duplicate
          ? "이미 동일 의료진에게 진행 중인 협진이 있습니다."
          : "협진 요청을 보내지 못했습니다.",
      );
    } finally {
      setSubmitting(false);
    }
  }


  if (!open) {
    return null;
  }


  const encounterId =
    activeEncounter?.encounter_id ??
    activeEncounter?.id ??
    null;


  return (
    <div
      className="consultation-list-request-backdrop"
      role="presentation"
    >
      <section
        className="consultation-list-request-modal"
        role="dialog"
        aria-modal="true"
        aria-labelledby="consultation-list-request-title"
      >

        <header className="consultation-list-request-modal__header">

          <div>
            <span>CONSULTATION REQUEST</span>

            <h2 id="consultation-list-request-title">
              협진 요청
            </h2>
          </div>

          <button
            type="button"
            aria-label="닫기"
            disabled={submitting}
            onClick={closeModal}
          >
            ×
          </button>

        </header>


        <form
          className="consultation-list-request-form"
          onSubmit={submitRequest}
        >

          <section className="consultation-list-request-section">

            <div className="consultation-list-request-section__title">
              <strong>1. 환자 선택</strong>
              <span>
                이름 또는 등록번호로 환자를 검색하세요.
              </span>
            </div>

            <div className="consultation-list-request-search">

              <input
                type="search"
                value={patientSearch}
                placeholder="환자 이름 또는 등록번호"
                disabled={submitting}
                onChange={(event) =>
                  setPatientSearch(
                    event.target.value,
                  )
                }
                onKeyDown={(event) => {
                  if (
                    event.key === "Enter"
                  ) {
                    event.preventDefault();
                    void loadPatients();
                  }
                }}
              />

              <button
                type="button"
                disabled={
                  patientsLoading ||
                  submitting
                }
                onClick={() =>
                  void loadPatients()
                }
              >
                {patientsLoading
                  ? "검색 중"
                  : "검색"}
              </button>

            </div>


            {patientsError && (
              <p className="consultation-list-request-error">
                {patientsError}
              </p>
            )}


            <div className="consultation-list-request-patients">

              {!patientsLoading &&
                patients.map(
                  (patient) => (
                    <button
                      type="button"
                      key={patient.id}
                      className={
                        selectedPatient?.id ===
                        patient.id
                          ? "is-selected"
                          : ""
                      }
                      disabled={submitting}
                      onClick={() =>
                        void selectPatient(
                          patient,
                        )
                      }
                    >
                      <strong>
                        {patient.name}
                      </strong>

                      <span>
                        {patient.patient_no}
                      </span>

                      <small>
                        {patient.birth_date ||
                          "생년월일 -"}
                      </small>
                    </button>
                  ),
                )}

              {!patientsLoading &&
                patients.length === 0 &&
                !patientsError && (
                  <div className="consultation-list-request-empty">
                    조회 가능한 환자가 없습니다.
                  </div>
                )}

            </div>


            {selectedPatient && (
              <div className="consultation-list-request-selected">

                <div>
                  <span>
                    선택 환자
                  </span>

                  <strong>
                    {selectedPatient.name}
                  </strong>

                  <small>
                    {selectedPatient.patient_no}
                  </small>
                </div>

                <div>
                  <span>
                    활성 Encounter
                  </span>

                  {encounterLoading ? (
                    <strong>
                      확인 중...
                    </strong>
                  ) : encounterId &&
                    activeEncounter ? (
                    <>
                      <strong>
                        {activeEncounter.encounter_no}
                      </strong>

                      <small>
                        {activeEncounter.status}
                      </small>
                    </>
                  ) : (
                    <strong className="is-error">
                      없음
                    </strong>
                  )}
                </div>

              </div>
            )}


            {encounterError && (
              <p className="consultation-list-request-error">
                {encounterError}
              </p>
            )}

          </section>


          <section className="consultation-list-request-section">

            <div className="consultation-list-request-section__title">
              <strong>2. 협진 정보</strong>
              <span>
                협진 대상과 요청 내용을 입력하세요.
              </span>
            </div>


            <div className="consultation-list-request-grid">

              <label>
                <span>
                  협진 대상 *
                </span>

                <select
                  value={consultationType}
                  disabled={submitting}
                  onChange={(event) =>
                    setConsultationType(
                      event.target
                        .value as ConsultationType,
                    )
                  }
                >
                  <option value="RADIOLOGY">
                    영상의학과
                  </option>

                  <option value="NEUROSURGERY">
                    신경외과
                  </option>
                </select>
              </label>


              <label>
                <span>
                  협진 의료진 *
                </span>

                <select
                  value={selectedClinicianId}
                  disabled={
                    submitting ||
                    cliniciansLoading
                  }
                  onChange={(event) =>
                    setSelectedClinicianId(
                      event.target.value,
                    )
                  }
                >
                  <option value="">
                    {cliniciansLoading
                      ? "의료진을 불러오는 중..."
                      : "의료진을 선택하세요"}
                  </option>

                  {!cliniciansLoading &&
                    clinicians.map(
                      (clinician) => (
                        <option
                          key={clinician.id}
                          value={
                            clinician.user_id
                          }
                        >
                          {clinician.name}
                        </option>
                      ),
                    )}
                </select>
              </label>


              <label>
                <span>
                  우선순위 *
                </span>

                <select
                  value={priority}
                  disabled={submitting}
                  onChange={(event) =>
                    setPriority(
                      event.target
                        .value as ConsultationPriority,
                    )
                  }
                >
                  <option value="ROUTINE">
                    일반
                  </option>

                  <option value="URGENT">
                    응급
                  </option>

                  <option value="STAT">
                    긴급
                  </option>
                </select>
              </label>

            </div>


            {cliniciansError && (
              <p className="consultation-list-request-error">
                {cliniciansError}
              </p>
            )}


            <label className="consultation-list-request-reason">

              <span>
                요청 사유 *
              </span>

              <textarea
                value={reason}
                maxLength={2000}
                disabled={submitting}
                placeholder="협진이 필요한 사유를 입력하세요."
                onChange={(event) =>
                  setReason(
                    event.target.value,
                  )
                }
              />

            </label>

          </section>


          {requestError && (
            <p
              className="consultation-list-request-error consultation-list-request-error--submit"
              role="alert"
            >
              {requestError}
            </p>
          )}


          <footer className="consultation-list-request-actions">

            <button
              type="button"
              disabled={submitting}
              onClick={closeModal}
            >
              취소
            </button>

            <button
              type="submit"
              className="is-primary"
              disabled={
                submitting ||
                !selectedPatient ||
                !encounterId ||
                !selectedClinicianId ||
                !reason.trim()
              }
            >
              {submitting
                ? "요청 중..."
                : "협진 요청"}
            </button>

          </footer>

        </form>

      </section>
    </div>
  );
}
