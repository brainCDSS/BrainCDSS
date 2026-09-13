import {
  useEffect,
  useMemo,
  useState,
} from "react";
import type {
  FormEvent,
} from "react";

import {
  getStaffAppointments,
} from "../appointments/api";
import type {
  StaffAppointment,
} from "../appointments/types";

import {
  createPatient,
  getPatients,
} from "../patients/api";
import type {
  Patient,
} from "../patients/types";

import {
  createEncounter,
  getAssessmentWorklist,
  startAssessment,
} from "./api";
import type {
  AssessmentWorklistItem,
} from "./types";
import {
  formatMobilePhone,
  limitDateYear,
} from "../../shared/utils/inputFormatters";

import "./css/reception_initial_assessment.css";


/* =========================================================
   Types
   ========================================================= */

type Sex =
  | "M"
  | "F";

type ReceptionVisitMode =
  | "EMERGENCY"
  | "APPOINTMENT"
  | "WALK_IN";

type ReceptionStatus =
  | "REGISTERED"
  | "WAITING"
  | "TRIAGE"
  | "IMAGING"
  | "IN_PROGRESS";

type BusyAction =
  | "SEARCH"
  | "CREATE_PATIENT"
  | "REGISTER_ENCOUNTER"
  | null;


interface ReceptionInitialAssessmentProps {
  onOpenTriage?: (
    assessmentId: string,
    encounterId: string,
  ) => void;
}


interface NewPatientForm {
  name: string;
  birth_date: string;
  sex: Sex | "";
  phone: string;
}


interface ReceptionDraft {
  visitReason: string;
  department: string;
  clinician: string;
  channel: string;
  priority: string;
  memo: string;
}


interface TodayVisitRow {
  key: string;
  encounterId: string;
  assessmentId: string | null;
  patientName: string;
  patientNo: string;
  ageSex: string;
  encounterType: string;
  status: ReceptionStatus;
  registeredAt: string | null;
}


const EMPTY_NEW_PATIENT: NewPatientForm = {
  name: "",
  birth_date: "",
  sex: "",
  phone: "",
};


const EMPTY_RECEPTION_DRAFT: ReceptionDraft = {
  visitReason: "",
  department: "",
  clinician: "",
  channel: "EMERGENCY_ROOM",
  priority: "URGENT",
  memo: "",
};


const PAGE_SIZE = 10;


/* =========================================================
   Helpers
   ========================================================= */

function sexLabel(
  sex: string | null | undefined,
) {
  if (sex === "M") {
    return "M";
  }

  if (sex === "F") {
    return "F";
  }

  return "-";
}


function phoneLabel(
  phone: string | null | undefined,
) {
  if (!phone) {
    return "-";
  }

  const digits =
    phone.replace(/\D/g, "");

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
}


function getTodayDate() {
  const now =
    new Date();

  const localDate =
    new Date(
      now.getTime() -
        now.getTimezoneOffset() *
          60 *
          1000,
    );

  return localDate
    .toISOString()
    .slice(0, 10);
}


function isToday(
  value?: string | null,
) {
  if (!value) {
    return false;
  }

  const date =
    new Date(value);

  if (
    Number.isNaN(
      date.getTime(),
    )
  ) {
    return false;
  }

  const localDate =
    new Date(
      date.getTime() -
        date.getTimezoneOffset() *
          60 *
          1000,
    )
      .toISOString()
      .slice(0, 10);

  return localDate ===
    getTodayDate();
}


function formatTime(
  value?: string | null,
) {
  if (!value) {
    return "-";
  }

  const date =
    new Date(value);

  if (
    Number.isNaN(
      date.getTime(),
    )
  ) {
    return "-";
  }

  return new Intl.DateTimeFormat(
    "ko-KR",
    {
      hour: "2-digit",
      minute: "2-digit",
      hour12: false,
    },
  ).format(date);
}


function formatDateTime(
  value?: string | null,
) {
  if (!value) {
    return "-";
  }

  const date =
    new Date(value);

  if (
    Number.isNaN(
      date.getTime(),
    )
  ) {
    return value;
  }

  return new Intl.DateTimeFormat(
    "ko-KR",
    {
      year: "numeric",
      month: "2-digit",
      day: "2-digit",
      hour: "2-digit",
      minute: "2-digit",
      hour12: false,
    },
  ).format(date);
}


function apiError(
  error: unknown,
  fallback: string,
) {
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
}


function worklistValue(
  summary: Record<string, unknown> | null | undefined,
  keys: string[],
) {
  if (!summary) {
    return null;
  }

  for (const key of keys) {
    const value =
      summary[key];

    if (
      typeof value === "string" ||
      typeof value === "number"
    ) {
      return String(value);
    }
  }

  return null;
}


function worklistPatientName(
  item: AssessmentWorklistItem,
) {
  return (
    worklistValue(
      item.patient_summary,
      [
        "name",
        "patient_name",
      ],
    ) ??
    "환자"
  );
}


function worklistPatientNo(
  item: AssessmentWorklistItem,
) {
  return (
    worklistValue(
      item.patient_summary,
      [
        "patient_no",
        "patient_number",
        "mrn",
      ],
    ) ??
    item.encounter_id
  );
}


function worklistPatientInfo(
  item: AssessmentWorklistItem,
) {
  const age =
    worklistValue(
      item.patient_summary,
      [
        "estimated_age",
        "age",
      ],
    );

  const sex =
    worklistValue(
      item.patient_summary,
      [
        "sex",
        "gender",
      ],
    );

  return [
    age ?? "-",
    sexLabel(sex),
  ].join(" / ");
}


function worklistEncounterType(
  item: AssessmentWorklistItem,
) {
  const value =
    item.encounter_type ??
    worklistValue(
      item.patient_summary,
      [
        "encounter_type",
        "visit_type",
      ],
    );

  if (value === "EMERGENCY") {
    return "응급";
  }

  if (value === "OUTPATIENT") {
    return "예약";
  }

  return "-";
}


function patientAgeNumber(
  patient: Patient,
) {
  if (
    patient.estimated_age !== null &&
    patient.estimated_age !== undefined
  ) {
    return patient.estimated_age;
  }

  if (!patient.birth_date) {
    return null;
  }

  const birth =
    new Date(patient.birth_date);

  const today =
    new Date();

  if (
    Number.isNaN(
      birth.getTime(),
    )
  ) {
    return null;
  }

  let age =
    today.getFullYear() -
    birth.getFullYear();

  const month =
    today.getMonth() -
    birth.getMonth();

  if (
    month < 0 ||
    (
      month === 0 &&
      today.getDate() <
        birth.getDate()
    )
  ) {
    age -= 1;
  }

  return age;
}


function patientAgeSex(
  patient: Patient,
) {
  const age =
    patientAgeNumber(patient);

  return `${age ?? "-"} / ${sexLabel(
    patient.sex,
  )}`;
}


function patientAgeSexLong(
  patient: Patient,
) {
  const age =
    patientAgeNumber(patient);

  return `${age ?? "-"}세 / ${sexLabel(
    patient.sex,
  )}`;
}


function receptionStatusLabel(
  status: ReceptionStatus,
) {
  switch (status) {
    case "REGISTERED":
      return "접수완료";

    case "WAITING":
      return "대기";

    case "TRIAGE":
      return "초기평가";

    case "IMAGING":
      return "검사대기";

    case "IN_PROGRESS":
      return "진료중";

    default:
      return "-";
  }
}


function receptionStatusClass(
  status: ReceptionStatus,
) {
  return status
    .toLowerCase()
    .replaceAll("_", "-");
}


function assessmentStatusToReceptionStatus(
  status: string,
): ReceptionStatus {
  if (status === "COMPLETED") {
    return "WAITING";
  }

  return "TRIAGE";
}


function encounterTypeLabel(
  value: string,
) {
  if (value === "EMERGENCY") {
    return "응급";
  }

  if (value === "OUTPATIENT") {
    return "예약";
  }

  return value || "-";
}


/* =========================================================
   Component
   ========================================================= */

export default function ReceptionInitialAssessment({
  onOpenTriage,
}: ReceptionInitialAssessmentProps) {

  /* =======================================================
     환자 검색
     ======================================================= */

  const [
    query,
    setQuery,
  ] = useState("");

  const [
    results,
    setResults,
  ] = useState<Patient[]>([]);

  const [
    searched,
    setSearched,
  ] = useState(false);

  const [
    selectedPatient,
    setSelectedPatient,
  ] = useState<Patient | null>(
    null,
  );


  /* =======================================================
     신규 환자
     ======================================================= */

  const [
    showCreate,
    setShowCreate,
  ] = useState(false);

  const [
    newPatient,
    setNewPatient,
  ] = useState<NewPatientForm>(
    EMPTY_NEW_PATIENT,
  );


  /* =======================================================
     접수
     ======================================================= */

  const [
    visitMode,
    setVisitMode,
  ] = useState<ReceptionVisitMode>(
    "EMERGENCY",
  );

  const [
    appointments,
    setAppointments,
  ] = useState<
    StaffAppointment[]
  >([]);

  const [
    appointmentId,
    setAppointmentId,
  ] = useState("");

  const [
    appointmentLoading,
    setAppointmentLoading,
  ] = useState(false);

  /*
   * 아래 항목은 목표 UI를 먼저 맞추기 위한 화면 상태입니다.
   * 현재 CreateEncounterRequest 계약에는 포함되지 않으므로
   * registerEncounter()의 payload에는 넣지 않습니다.
   * Backend 계약 확정 후 API 필드와 연결하세요.
   */
  const [
    receptionDraft,
    setReceptionDraft,
  ] = useState<ReceptionDraft>(
    EMPTY_RECEPTION_DRAFT,
  );


  /* =======================================================
     초기평가 Worklist
     -------------------------------------------------------
     주의:
     이 Worklist를 "오늘 내원 환자 전체 목록"으로 간주하지 않습니다.
     현재 API에서 확인 가능한 초기평가 단계 환자만
     오늘 내원 패널의 일부 데이터로 보조 표시합니다.
     ======================================================= */

  const [
    worklist,
    setWorklist,
  ] = useState<
    AssessmentWorklistItem[]
  >([]);

  const [
    worklistLoading,
    setWorklistLoading,
  ] = useState(false);

  const [
    worklistError,
    setWorklistError,
  ] = useState<string | null>(
    null,
  );

  const [
    openingEncounterId,
    setOpeningEncounterId,
  ] = useState<string | null>(
    null,
  );


  /*
   * 현재 세션에서 이 화면을 통해 새로 접수한 환자.
   * GET /encounters 목록 API가 생기기 전까지
   * 화면에서 방금 등록한 건을 즉시 보여주기 위한 로컬 상태입니다.
   */
  const [
    localVisitRows,
    setLocalVisitRows,
  ] = useState<TodayVisitRow[]>(
    [],
  );


  /* =======================================================
     목록 / 페이지
     ======================================================= */

  const [
    page,
    setPage,
  ] = useState(1);


  /* =======================================================
     공통 상태
     ======================================================= */

  const [
    busy,
    setBusy,
  ] = useState<BusyAction>(
    null,
  );

  const [
    error,
    setError,
  ] = useState<string | null>(
    null,
  );

  const [
    info,
    setInfo,
  ] = useState<string | null>(
    null,
  );


  /* =======================================================
     예약
     ======================================================= */

  const selectedAppointment =
    appointments.find(
      (item) =>
        item.appointment_id ===
        appointmentId,
    ) ??
    null;


  useEffect(
    () => {
      if (
        visitMode !==
          "APPOINTMENT" ||
        !selectedPatient
      ) {
        setAppointments(
          [],
        );

        setAppointmentId(
          "",
        );

        return;
      }

      let cancelled =
        false;

      setAppointmentLoading(
        true,
      );

      setAppointmentId(
        "",
      );

      getStaffAppointments({
        status: "CONFIRMED",
        pageSize: 100,
      })
        .then(
          (response) => {
            if (cancelled) {
              return;
            }

            const list =
              response.results ??
              response.appointments ??
              [];

            const patientAppointments =
              list.filter(
                (item) =>
                  (
                    item.patient
                      ?.id ??
                    item.patient_id
                  ) ===
                  selectedPatient.id,
              );

            setAppointments(
              patientAppointments,
            );
          },
        )
        .catch(
          (requestError) => {
            if (cancelled) {
              return;
            }

            setAppointments(
              [],
            );

            setError(
              apiError(
                requestError,
                "확정 예약을 불러오지 못했습니다.",
              ),
            );
          },
        )
        .finally(
          () => {
            if (
              !cancelled
            ) {
              setAppointmentLoading(
                false,
              );
            }
          },
        );

      return () => {
        cancelled =
          true;
      };
    },
    [
      selectedPatient,
      visitMode,
    ],
  );


  useEffect(
    () => {
      if (!selectedAppointment) {
        if (
          visitMode ===
          "APPOINTMENT"
        ) {
          setReceptionDraft(
            (current) => ({
              ...current,
              department: "",
              clinician: "",
              channel: "OUTPATIENT_DESK",
            }),
          );
        }

        return;
      }

      setReceptionDraft(
        (current) => ({
          ...current,
          department:
            selectedAppointment
              .department
              ?.name ??
            current.department,
          clinician:
            selectedAppointment
              .clinician
              ?.name ??
            current.clinician,
          channel: "OUTPATIENT_DESK",
        }),
      );
    },
    [
      selectedAppointment,
      visitMode,
    ],
  );


  /* =======================================================
     Worklist 조회
     ======================================================= */

  async function loadWorklist() {
    setWorklistLoading(
      true,
    );

    setWorklistError(
      null,
    );

    try {
      const response =
        await getAssessmentWorklist();

      setWorklist(
        response.results ??
          [],
      );
    } catch (
      requestError
    ) {
      setWorklist([]);

      setWorklistError(
        apiError(
          requestError,
          "초기평가 단계 환자 정보를 불러오지 못했습니다.",
        ),
      );
    } finally {
      setWorklistLoading(
        false,
      );
    }
  }


  useEffect(
    () => {
      void loadWorklist();
    },
    [],
  );


  /* =======================================================
     오늘 내원 환자 표시 데이터
     ======================================================= */

  const worklistVisitRows =
    useMemo(
      () =>
        worklist
          .filter(
            (item) =>
              isToday(
                item.created_at,
              ),
          )
          .map<TodayVisitRow>(
            (item) => ({
              key:
                `worklist-${item.encounter_id}`,
              encounterId:
                item.encounter_id,
              assessmentId:
                item.assessment_id,
              patientName:
                worklistPatientName(
                  item,
                ),
              patientNo:
                worklistPatientNo(
                  item,
                ),
              ageSex:
                worklistPatientInfo(
                  item,
                ),
              encounterType:
                worklistEncounterType(
                  item,
                ),
              status:
                assessmentStatusToReceptionStatus(
                  item.status,
                ),
              registeredAt:
                item.created_at,
            }),
          ),
      [
        worklist,
      ],
    );


  const todayVisitRows =
    useMemo(
      () => {
        const byEncounter =
          new Map<
            string,
            TodayVisitRow
          >();

        for (
          const item of localVisitRows
        ) {
          byEncounter.set(
            item.encounterId,
            item,
          );
        }

        /*
         * Worklist에 같은 encounter가 있으면
         * 초기평가 단계로 진행된 최신 상태를 우선 표시합니다.
         */
        for (
          const item of worklistVisitRows
        ) {
          const existing =
            byEncounter.get(
              item.encounterId,
            );

          byEncounter.set(
            item.encounterId,
            {
              ...existing,
              ...item,
              patientName:
                item.patientName ===
                "환자"
                  ? existing
                      ?.patientName ??
                    item.patientName
                  : item.patientName,
              patientNo:
                item.patientNo ??
                existing?.patientNo ??
                "-",
              ageSex:
                item.ageSex ===
                "- / -"
                  ? existing
                      ?.ageSex ??
                    item.ageSex
                  : item.ageSex,
              encounterType:
                item.encounterType ===
                "-"
                  ? existing
                      ?.encounterType ??
                    "-"
                  : item.encounterType,
            },
          );
        }

        return Array.from(
          byEncounter.values(),
        ).sort(
          (
            a,
            b,
          ) => {
            const aTime =
              a.registeredAt
                ? new Date(
                    a.registeredAt,
                  ).getTime()
                : 0;

            const bTime =
              b.registeredAt
                ? new Date(
                    b.registeredAt,
                  ).getTime()
                : 0;

            return bTime -
              aTime;
          },
        );
      },
      [
        localVisitRows,
        worklistVisitRows,
      ],
    );


  const totalPages =
    Math.max(
      1,
      Math.ceil(
        todayVisitRows.length /
          PAGE_SIZE,
      ),
    );


  const pagedVisitRows =
    todayVisitRows.slice(
      (page - 1) *
        PAGE_SIZE,
      page *
        PAGE_SIZE,
    );


  useEffect(
    () => {
      if (
        page >
        totalPages
      ) {
        setPage(
          totalPages,
        );
      }
    },
    [
      page,
      totalPages,
    ],
  );


  const countByStatus =
    (
      status:
        ReceptionStatus,
    ) =>
      todayVisitRows.filter(
        (item) =>
          item.status ===
          status,
      ).length;


  /* =======================================================
     환자 검색
     ======================================================= */

  async function searchPatients(
    event: FormEvent,
  ) {
    event.preventDefault();

    const normalizedQuery =
      query.trim();

    if (
      !normalizedQuery ||
      busy !== null
    ) {
      return;
    }

    setBusy(
      "SEARCH",
    );

    setError(
      null,
    );

    setInfo(
      null,
    );

    setSearched(
      true,
    );

    setSelectedPatient(
      null,
    );

    setShowCreate(
      false,
    );

    try {
      const response =
        await getPatients(
          normalizedQuery,
        );

      setResults(
        response.results ??
          [],
      );
    } catch (
      requestError
    ) {
      setResults(
        [],
      );

      setError(
        apiError(
          requestError,
          "환자 검색에 실패했습니다.",
        ),
      );
    } finally {
      setBusy(
        null,
      );
    }
  }


  /* =======================================================
     환자 선택 / 초기화
     ======================================================= */

  function selectPatient(
    patient: Patient,
  ) {
    setSelectedPatient(
      patient,
    );

    setShowCreate(
      false,
    );

    setVisitMode(
      "EMERGENCY",
    );

    setAppointmentId(
      "",
    );

    setReceptionDraft({
      ...EMPTY_RECEPTION_DRAFT,
    });

    setError(
      null,
    );

    setInfo(
      null,
    );
  }


  function resetSelectedPatient() {
    setSelectedPatient(
      null,
    );

    setVisitMode(
      "EMERGENCY",
    );

    setAppointmentId(
      "",
    );

    setReceptionDraft({
      ...EMPTY_RECEPTION_DRAFT,
    });

    setError(
      null,
    );

    setInfo(
      null,
    );
  }


  /* =======================================================
     신규 환자
     ======================================================= */

  function openCreatePatient() {
    setShowCreate(
      true,
    );

    setSelectedPatient(
      null,
    );

    setError(
      null,
    );

    setInfo(
      null,
    );

    setNewPatient({
      ...EMPTY_NEW_PATIENT,
      name:
        query.trim(),
    });
  }


  function closeCreatePatient() {
    setShowCreate(
      false,
    );

    setNewPatient(
      EMPTY_NEW_PATIENT,
    );

    setError(
      null,
    );
  }


  async function registerPatient(
    event: FormEvent,
  ) {
    event.preventDefault();

    if (
      busy !== null
    ) {
      return;
    }

    if (
      !newPatient.name.trim() ||
      !newPatient.birth_date ||
      !newPatient.sex
    ) {
      setError(
        "이름, 생년월일, 성별을 확인해 주세요.",
      );

      return;
    }

    if (
      newPatient.birth_date >
      getTodayDate()
    ) {
      setError(
        "생년월일은 오늘 이후의 날짜를 입력할 수 없습니다.",
      );

      return;
    }

    setBusy(
      "CREATE_PATIENT",
    );

    setError(
      null,
    );

    setInfo(
      null,
    );

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

      setResults(
        [
          patient,
        ],
      );

      setSearched(
        true,
      );

      setShowCreate(
        false,
      );

      setNewPatient(
        EMPTY_NEW_PATIENT,
      );

      setVisitMode(
        "EMERGENCY",
      );

      setReceptionDraft({
        ...EMPTY_RECEPTION_DRAFT,
      });

      setInfo(
        "신규 환자가 등록되었습니다. 접수 정보를 확인해 주세요.",
      );
    } catch (
      requestError
    ) {
      setError(
        apiError(
          requestError,
          "신규 환자를 등록하지 못했습니다.",
        ),
      );
    } finally {
      setBusy(
        null,
      );
    }
  }


  /* =======================================================
     오늘 내원 목록에서 초기평가 열기
     ======================================================= */

  async function openTodayVisit(
    item: TodayVisitRow,
  ) {
    if (
      openingEncounterId !==
        null
    ) {
      return;
    }

    if (
      !onOpenTriage
    ) {
      setError(
        "초기평가 화면 연결 함수를 찾을 수 없습니다.",
      );

      return;
    }

    setOpeningEncounterId(
      item.encounterId,
    );

    setError(
      null,
    );

    try {
      let assessmentId =
        item.assessmentId;

      if (!assessmentId) {
        const response =
          await startAssessment({
            encounter_id:
              item.encounterId,
          });

        assessmentId =
          response.assessment_id;

        setWorklist(
          (current) =>
            current.map(
              (entry) =>
                entry.encounter_id ===
                item.encounterId
                  ? {
                      ...entry,
                      assessment_id:
                        assessmentId,
                      status:
                        response.status,
                    }
                  : entry,
            ),
        );

        setLocalVisitRows(
          (current) =>
            current.map(
              (entry) =>
                entry.encounterId ===
                item.encounterId
                  ? {
                      ...entry,
                      assessmentId,
                      status:
                        assessmentStatusToReceptionStatus(
                          response.status,
                        ),
                    }
                  : entry,
            ),
        );
      }

      onOpenTriage(
        assessmentId,
        item.encounterId,
      );
    } catch (requestError) {
      setError(
        apiError(
          requestError,
          "초기평가를 시작하지 못했습니다.",
        ),
      );
    } finally {
      setOpeningEncounterId(
        null,
      );
    }
  }


  /* =======================================================
     접수 완료
     -------------------------------------------------------
     현재 Backend 계약:
     patient_id
     encounter_type
     appointment_id (OUTPATIENT only)

     화면의 방문 사유 / 진료과 / 담당의 / 접수 채널 /
     우선순위 / 비고는 현재 API payload에 넣지 않습니다.
     ======================================================= */

  async function registerEncounter() {
    if (
      !selectedPatient ||
      busy !== null
    ) {
      return;
    }

    if (
      visitMode ===
        "APPOINTMENT" &&
      !appointmentId
    ) {
      setError(
        "예약 접수는 확정 예약을 선택해 주세요.",
      );

      return;
    }

    if (
      !onOpenTriage
    ) {
      setError(
        "초기평가 화면 연결 함수를 찾을 수 없습니다.",
      );

      return;
    }

    setBusy(
      "REGISTER_ENCOUNTER",
    );

    setError(
      null,
    );

    setInfo(
      null,
    );

    try {
      const encounterType:
        "EMERGENCY" |
        "OUTPATIENT" =
          visitMode ===
          "EMERGENCY"
            ? "EMERGENCY"
            : "OUTPATIENT";

      const created =
        await createEncounter({
          patient_id:
            selectedPatient.id,

          encounter_type:
            encounterType,

          ...(
            visitMode ===
              "APPOINTMENT"
              ? {
                  appointment_id:
                    appointmentId,
                }
              : {}
          ),
        });

      if (
        !created.encounter_id
      ) {
        throw new Error(
          "ENCOUNTER_ID_MISSING",
        );
      }

      /*
       * 화면에서 방금 접수된 환자를 즉시 표시한다.
       * GET /encounters 목록 API가 생기면 이 로컬 보완은 제거 가능.
       */
      setLocalVisitRows(
        (current) => [
          {
            key:
              `local-${created.encounter_id}`,
            encounterId:
              created.encounter_id,
            assessmentId:
              null,
            patientName:
              selectedPatient.name,
            patientNo:
              selectedPatient.patient_no,
            ageSex:
              patientAgeSex(
                selectedPatient,
              ),
            encounterType:
              encounterTypeLabel(
                created.encounter_type ??
                  encounterType,
              ),
            status:
              "REGISTERED",
            registeredAt:
              created.arrived_at ??
              new Date().toISOString(),
          },
          ...current.filter(
            (item) =>
              item.encounterId !==
              created.encounter_id,
          ),
        ],
      );

      /*
       * Backend에서 Encounter 생성과 동시에 Assessment가
       * 만들어지는 경우를 고려해 기존 Worklist를 확인합니다.
       * 이 조회는 왼쪽 전체 내원 목록의 원본 데이터가 아니라,
       * 접수 후 Assessment 연결 확인 용도입니다.
       */
      const latestWorklist =
        await getAssessmentWorklist();

      setWorklist(
        latestWorklist.results ??
          [],
      );

      const existing =
        latestWorklist.results?.find(
          (item) =>
            item.encounter_id ===
              created.encounter_id &&
            Boolean(
              item.assessment_id,
            ),
        );


      let assessmentId =
        existing?.assessment_id ??
        null;

      let encounterId =
        created.encounter_id;


      if (
        !assessmentId
      ) {
        const started =
          await startAssessment({
            encounter_id:
              created.encounter_id,
          });

        assessmentId =
          started.assessment_id;

        encounterId =
          started.encounter_id ??
          created.encounter_id;
      }


      if (
        !assessmentId
      ) {
        throw new Error(
          "ASSESSMENT_ID_MISSING",
        );
      }


      setLocalVisitRows(
        (current) =>
          current.map(
            (item) =>
              item.encounterId ===
              created.encounter_id
                ? {
                    ...item,
                    assessmentId,
                    status:
                      "TRIAGE",
                  }
                : item,
          ),
      );


      onOpenTriage(
        assessmentId,
        encounterId,
      );
    } catch (
      requestError
    ) {
      setError(
        apiError(
          requestError,
          "접수를 완료하지 못했습니다.",
        ),
      );
    } finally {
      setBusy(
        null,
      );
    }
  }


  /* =======================================================
     Render
     ======================================================= */

  return (
    <section className="reception-page">

      {/* ===================================================
          Header
          =================================================== */}

      <header className="reception-heading">

        <div className="reception-heading__title">

          <div className="reception-heading__main-row">

            <h1>
              접수 · 내원관리
            </h1>

            <p>
              내원 환자를 검색하고 접수 후 초기평가로 연결합니다.
            </p>

          </div>

        </div>

      </header>


      {/* ===================================================
          Compact Summary
          =================================================== */}

      <div className="reception-summary-line">

        <span>
          오늘 접수
          <strong>
            {todayVisitRows.length}
          </strong>
        </span>

        <i />

        <span>
          대기
          <strong>
            {countByStatus(
              "WAITING",
            )}
          </strong>
        </span>

        <i />

        <span>
          초기평가
          <strong>
            {countByStatus(
              "TRIAGE",
            )}
          </strong>
        </span>

        <i />

        <span>
          검사대기
          <strong>
            {countByStatus(
              "IMAGING",
            )}
          </strong>
        </span>

        <i />

        <span>
          진료중
          <strong>
            {countByStatus(
              "IN_PROGRESS",
            )}
          </strong>
        </span>

      </div>


      {/* ===================================================
          Message
          =================================================== */}

      {error && (
        <div
          className="reception-message reception-message--error"
          role="alert"
        >
          {error}
        </div>
      )}


      {info && (
        <div
          className="reception-message reception-message--info"
        >
          {info}
        </div>
      )}


      {/* ===================================================
          Main Workspace
          =================================================== */}

      <div className="reception-workspace">


        {/* =================================================
            LEFT
            오늘 내원 환자
            ================================================= */}

        <aside className="reception-panel reception-today-panel">

          <div className="reception-panel__heading">

            <div>

              <strong>
                오늘 내원 환자 ({todayVisitRows.length})
              </strong>

              <span>
                접수부터 진료까지 현재 상태를 확인합니다.
              </span>

            </div>


            <button
              className="reception-icon-button"
              type="button"
              disabled={
                worklistLoading
              }
              onClick={() => {
                void loadWorklist();
              }}
              aria-label="오늘 내원 환자 새로고침"
              title="새로고침"
            >
              ↻
            </button>

          </div>


          <div className="reception-today-table">

            <div className="reception-today-table__head">

              <span>
                상태
              </span>

              <span>
                내원유형
              </span>

              <span>
                환자명
              </span>

              <span>
                나이/성별
              </span>

              <span>
                접수시간
              </span>

            </div>


            <div className="reception-today-table__body">

              {worklistLoading &&
              todayVisitRows.length ===
                0 ? (
                <div className="reception-empty">
                  내원 정보를 불러오고 있습니다.
                </div>
              ) : worklistError &&
                todayVisitRows.length ===
                  0 ? (
                <div className="reception-empty reception-empty--error">
                  {worklistError}
                </div>
              ) : pagedVisitRows.length ===
                0 ? (
                <div className="reception-empty reception-empty--with-note">

                  <strong>
                    표시할 오늘 내원 환자가 없습니다.
                  </strong>

                  <span>
                    오늘 접수된 환자가 이곳에 표시됩니다.
                  </span>

                </div>
              ) : (
                pagedVisitRows.map(
                  (item) => {

                    const statusClass =
                      receptionStatusClass(
                        item.status,
                      );

                    const opening =
                      openingEncounterId ===
                      item.encounterId;

                    return (
                      <button
                        key={
                          item.key
                        }
                        type="button"
                        className={
                          "reception-today-row is-clickable"
                        }
                        disabled={
                          openingEncounterId !==
                          null
                        }
                        onClick={() => {
                          void openTodayVisit(
                            item,
                          );
                        }}
                      >

                        <span className="reception-today-row__status">

                          <i
                            className={
                              `reception-status-dot reception-status-dot--${statusClass}`
                            }
                          />

                          <b
                            className={
                              `reception-status-text reception-status-text--${statusClass}`
                            }
                          >
                            {receptionStatusLabel(
                              item.status,
                            )}
                          </b>

                        </span>

                        <span className="reception-today-row__type">
                          {item.encounterType}
                        </span>

                        <span className="reception-today-row__patient">

                          <strong>
                            {item.patientName}
                          </strong>

                          <small>
                            {item.patientNo}
                          </small>

                        </span>

                        <span>
                          {item.ageSex}
                        </span>

                        <span className="reception-today-row__time">
                          {opening
                            ? "여는 중..."
                            : formatTime(
                                item.registeredAt,
                              )}
                        </span>

                      </button>
                    );
                  },
                )
              )}

            </div>

          </div>


          <footer className="reception-pagination">

            <button
              type="button"
              disabled={
                page <= 1
              }
              onClick={() => {
                setPage(
                  (current) =>
                    Math.max(
                      1,
                      current - 1,
                    ),
                );
              }}
              aria-label="이전 페이지"
            >
              ‹
            </button>


            {Array.from(
              {
                length:
                  totalPages,
              },
              (
                _,
                index,
              ) =>
                index + 1,
            )
              .slice(
                0,
                5,
              )
              .map(
                (pageNumber) => (
                  <button
                    key={
                      pageNumber
                    }
                    type="button"
                    className={
                      page ===
                      pageNumber
                        ? "is-active"
                        : ""
                    }
                    onClick={() => {
                      setPage(
                        pageNumber,
                      );
                    }}
                  >
                    {pageNumber}
                  </button>
                ),
              )}


            <button
              type="button"
              disabled={
                page >=
                totalPages
              }
              onClick={() => {
                setPage(
                  (current) =>
                    Math.min(
                      totalPages,
                      current + 1,
                    ),
                );
              }}
              aria-label="다음 페이지"
            >
              ›
            </button>


            <span className="reception-pagination__size">
              {PAGE_SIZE}개씩 보기
            </span>

          </footer>

        </aside>


        {/* =================================================
            CENTER
            환자 검색
            ================================================= */}

        <main className="reception-panel reception-search-panel">

          <div className="reception-panel__heading">

            <div>

              <strong>
                환자 검색
              </strong>

              <span>
                이름 또는 환자번호로 검색합니다.
              </span>

            </div>

          </div>


          <form
            className="reception-search-form"
            onSubmit={
              searchPatients
            }
          >

            <div className="reception-search-input-wrap">

              <span className="reception-search-input-icon">
                ⌕
              </span>

              <input
                type="search"
                value={query}
                onChange={(
                  event,
                ) => {
                  setQuery(
                    event.target.value,
                  );
                }}
                placeholder="환자명 또는 환자번호"
              />

            </div>


            <button
              type="submit"
              disabled={
                !query.trim() ||
                busy !== null
              }
            >
              {busy ===
              "SEARCH"
                ? "검색 중..."
                : "검색"}
            </button>

          </form>


          {!showCreate && (
            <div className="reception-search-content">

              {!searched ? (
                <div className="reception-search-empty">

                  <div className="reception-search-empty__icon">
                    ⌕
                  </div>

                  <strong>
                    환자를 검색해 주세요.
                  </strong>

                  <span>
                    기존 환자를 먼저 확인한 뒤 접수를 진행합니다.
                  </span>

                </div>
              ) : results.length >
                0 ? (
                <>

                  <div className="reception-result-count">

                    <strong>
                      검색 결과 {results.length}건
                    </strong>

                    <button
                      type="button"
                      className="reception-result-sort"
                    >
                      정확도순⌄
                    </button>

                  </div>


                  <div className="reception-result-list">

                    {results.map(
                      (patient) => {

                        const selected =
                          selectedPatient
                            ?.id ===
                          patient.id;

                        return (
                          <article
                            key={
                              patient.id
                            }
                            className={
                              selected
                                ? "reception-result-card is-selected"
                                : "reception-result-card"
                            }
                          >

                            <div className="reception-result-card__avatar">
                              {patient.name
                                .trim()
                                .charAt(0) ||
                                "P"}
                            </div>


                            <div className="reception-result-card__body">

                              <div className="reception-result-card__top">

                                <div>

                                  <strong>
                                    {patient.name}
                                  </strong>

                                  <span>
                                    {patient.patient_no}
                                  </span>

                                </div>


                                <div className="reception-result-card__last-visit">

                                  <small>
                                    최근 내원
                                  </small>

                                  <span>
                                    -
                                  </span>

                                </div>

                              </div>


                              <div className="reception-result-card__meta">

                                <span>
                                  {patientAgeSexLong(
                                    patient,
                                  )}
                                </span>

                                <span>
                                  {patient.birth_date ??
                                    "-"}
                                </span>

                                <span>
                                  {phoneLabel(
                                    patient.phone,
                                  )}
                                </span>

                              </div>

                            </div>


                            <button
                              type="button"
                              className="reception-result-card__select"
                              onClick={() => {
                                selectPatient(
                                  patient,
                                );
                              }}
                            >
                              {selected
                                ? "선택됨"
                                : "환자 선택"}
                            </button>

                          </article>
                        );
                      },
                    )}

                  </div>


                  <div className="reception-new-patient-area">

                    <div>

                      <strong>
                        검색 결과가 없나요?
                      </strong>

                      <span>
                        신규 환자를 등록하여 접수를 진행할 수 있습니다.
                      </span>

                    </div>


                    <button
                      className="reception-new-patient-link"
                      type="button"
                      onClick={
                        openCreatePatient
                      }
                    >
                      + 신규 환자 등록
                    </button>

                  </div>

                </>
              ) : (
                <div className="reception-search-empty">

                  <div className="reception-search-empty__icon">
                    +
                  </div>

                  <strong>
                    등록된 환자를 찾지 못했습니다.
                  </strong>

                  <span>
                    처음 방문한 환자라면 신규 환자로 등록해 주세요.
                  </span>

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

            </div>
          )}


          {/* ===============================================
              신규 환자 등록
              =============================================== */}

          {showCreate && (
            <form
              className="reception-create-form"
              onSubmit={
                registerPatient
              }
            >

              <div className="reception-create-form__heading">

                <div>

                  <strong>
                    신규 환자 등록
                  </strong>

                  <span>
                    접수에 필요한 기본정보를 입력합니다.
                  </span>

                </div>


                <button
                  className="reception-create-form__back"
                  type="button"
                  onClick={
                    closeCreatePatient
                  }
                >
                  ← {results.length > 0
                    ? "검색 결과로"
                    : "환자 검색으로"}
                </button>

              </div>


              <label>

                <span>
                  이름
                  <em>
                    *
                  </em>
                </span>

                <input
                  required
                  autoFocus
                  value={
                    newPatient.name
                  }
                  onChange={(
                    event,
                  ) => {
                    setNewPatient(
                      (
                        current,
                      ) => ({
                        ...current,
                        name:
                          event.target
                            .value,
                      }),
                    );
                  }}
                  placeholder="환자 이름"
                />

              </label>


              <div className="reception-create-form__row">

                <label>

                  <span>
                    생년월일
                    <em>
                      *
                    </em>
                  </span>

                  <input
                    required
                    type="date"
                    max={
                      getTodayDate()
                    }
                    value={
                      newPatient.birth_date
                    }
                    onChange={(
                      event,
                    ) => {
                      setNewPatient(
                        (
                          current,
                        ) => ({
                          ...current,
                          birth_date:
                            limitDateYear(
                              event.target.value,
                            ),
                        }),
                      );
                    }}
                  />

                </label>


                <label>

                  <span>
                    성별
                    <em>
                      *
                    </em>
                  </span>

                  <select
                    required
                    value={
                      newPatient.sex
                    }
                    onChange={(
                      event,
                    ) => {
                      setNewPatient(
                        (
                          current,
                        ) => ({
                          ...current,
                          sex:
                            event.target
                              .value as Sex,
                        }),
                      );
                    }}
                  >

                    <option value="">
                      선택
                    </option>

                    <option value="M">
                      남
                    </option>

                    <option value="F">
                      여
                    </option>

                  </select>

                </label>

              </div>


              <label>

                <span>
                  전화번호
                </span>

                <input
                  type="tel"
                  inputMode="tel"
                  value={
                    newPatient.phone
                  }
                  onChange={(
                    event,
                  ) => {
                    setNewPatient(
                      (
                        current,
                      ) => ({
                          ...current,
                          phone:
                          formatMobilePhone(
                            event.target.value,
                          ),
                      }),
                    );
                  }}
                  placeholder="010-0000-0000"
                />

              </label>


              <div className="reception-create-form__actions">

                <button
                  className="secondary"
                  type="button"
                  disabled={
                    busy !== null
                  }
                  onClick={
                    closeCreatePatient
                  }
                >
                  취소
                </button>


                <button
                  type="submit"
                  disabled={
                    busy !== null ||
                    !newPatient.name.trim() ||
                    !newPatient.birth_date ||
                    !newPatient.sex
                  }
                >
                  {busy ===
                  "CREATE_PATIENT"
                    ? "등록 중..."
                    : "환자 등록"}
                </button>

              </div>

            </form>
          )}

        </main>


        {/* =================================================
            RIGHT
            선택 환자 정보 및 접수
            ================================================= */}

        <aside className="reception-panel reception-register-panel">

          <div className="reception-panel__heading">

            <div>

              <strong>
                선택 환자 정보 및 접수
              </strong>

              <span>
                환자를 확인하고 이번 내원 정보를 등록합니다.
              </span>

            </div>


            {selectedPatient && (
              <button
                className="reception-reset-button"
                type="button"
                onClick={
                  resetSelectedPatient
                }
              >
                ↻ 초기화
              </button>
            )}

          </div>


          {!selectedPatient ? (
            <div className="reception-selected-empty">

              <div className="reception-selected-empty__icon">
                +
              </div>

              <strong>
                환자를 선택해 주세요.
              </strong>

              <span>
                검색 결과에서 접수할 환자를 선택하면
                이곳에 환자 정보와 접수 양식이 표시됩니다.
              </span>

            </div>
          ) : (
            <div className="reception-register-content">


              {/* ===========================================
                  환자 기본정보
                  =========================================== */}

              <section className="reception-selected-patient">

                <div className="reception-selected-patient__header">

                  <div className="reception-selected-patient__avatar">
                    {selectedPatient.name
                      .trim()
                      .charAt(0) ||
                      "P"}
                  </div>


                  <div className="reception-selected-patient__identity">

                    <div>

                      <strong>
                        {selectedPatient.name}
                      </strong>

                      <span>
                        {patientAgeSexLong(
                          selectedPatient,
                        )}
                      </span>

                    </div>

                    <p>
                      {selectedPatient.patient_no}
                    </p>

                    <p>
                      {selectedPatient.birth_date ??
                        "-"}
                      {" · "}
                      {phoneLabel(
                        selectedPatient.phone,
                      )}
                    </p>

                  </div>

                </div>

              </section>


              {/* ===========================================
                  내원 정보
                  =========================================== */}

              <section className="reception-form-section">

                <div className="reception-form-title">
                  내원 정보
                </div>


                <label className="reception-field-label">
                  내원 유형
                  <em>
                    *
                  </em>
                </label>


                <div className="reception-visit-type">

                  <button
                    type="button"
                    className={
                      visitMode ===
                      "EMERGENCY"
                        ? "is-active"
                        : ""
                    }
                    onClick={() => {
                      setVisitMode(
                        "EMERGENCY",
                      );

                      setReceptionDraft(
                        (current) => ({
                          ...current,
                          channel:
                            "EMERGENCY_ROOM",
                        }),
                      );
                    }}
                  >
                    ● 응급
                  </button>


                  <button
                    type="button"
                    className={
                      visitMode ===
                      "APPOINTMENT"
                        ? "is-active"
                        : ""
                    }
                    onClick={() => {
                      setVisitMode(
                        "APPOINTMENT",
                      );
                    }}
                  >
                    ○ 예약
                  </button>


                  <button
                    type="button"
                    className={
                      visitMode ===
                      "WALK_IN"
                        ? "is-active"
                        : ""
                    }
                    onClick={() => {
                      setVisitMode(
                        "WALK_IN",
                      );

                      setAppointmentId(
                        "",
                      );
                    }}
                    title="예약 없이 외래 Walk-in으로 접수합니다."
                  >
                    ○ 당일
                  </button>

                </div>


                {visitMode ===
                  "APPOINTMENT" && (
                  <label className="reception-field">

                    <span>
                      확정 예약
                      <em>
                        *
                      </em>
                    </span>

                    <select
                      value={
                        appointmentId
                      }
                      disabled={
                        appointmentLoading
                      }
                      onChange={(
                        event,
                      ) => {
                        setAppointmentId(
                          event.target
                            .value,
                        );
                      }}
                    >

                      <option value="">
                        {appointmentLoading
                          ? "예약 조회 중..."
                          : "예약을 선택해 주세요"}
                      </option>

                      {appointments.map(
                        (
                          item,
                        ) => {

                          const startAt =
                            item.start_at ??
                            item.slot
                              ?.start_at ??
                            "-";

                          const department =
                            item.department
                              ?.name ??
                            "";

                          const clinician =
                            item.clinician
                              ?.name ??
                            "";

                          return (
                            <option
                              key={
                                item.appointment_id
                              }
                              value={
                                item.appointment_id
                              }
                            >
                              {formatDateTime(
                                startAt,
                              )}
                              {department
                                ? ` · ${department}`
                                : ""}
                              {clinician
                                ? ` · ${clinician}`
                                : ""}
                            </option>
                          );
                        },
                      )}

                    </select>


                    {!appointmentLoading &&
                      appointments.length ===
                        0 && (
                        <small>
                          연결 가능한 CONFIRMED 예약이 없습니다.
                        </small>
                      )}

                  </label>
                )}


                <label className="reception-field">

                  <span>
                    방문 사유
                    <em>
                      *
                    </em>
                  </span>

                  <textarea
                    value={
                      receptionDraft.visitReason
                    }
                    onChange={(
                      event,
                    ) => {
                      setReceptionDraft(
                        (
                          current,
                        ) => ({
                          ...current,
                          visitReason:
                            event.target
                              .value,
                        }),
                      );
                    }}
                    placeholder="주요 증상 또는 방문 사유를 입력하세요."
                    maxLength={200}
                  />

                  <small className="reception-field__counter">
                    {receptionDraft.visitReason.length}/200
                  </small>

                </label>


                <label className="reception-field">

                  <span>
                    진료과
                    <em>
                      *
                    </em>
                  </span>

                  <select
                    value={
                      receptionDraft.department
                    }
                    onChange={(
                      event,
                    ) => {
                      setReceptionDraft(
                        (
                          current,
                        ) => ({
                          ...current,
                          department:
                            event.target
                              .value,
                          clinician: "",
                        }),
                      );
                    }}
                  >

                    <option value="">
                      진료과 선택
                    </option>

                    <option value="신경과">
                      신경과
                    </option>

                    <option value="신경외과">
                      신경외과
                    </option>

                    <option value="영상의학과">
                      영상의학과
                    </option>

                  </select>

                </label>


                <label className="reception-field">

                  <span>
                    담당의
                    <em>
                      *
                    </em>
                  </span>

                  <select
                    value={
                      receptionDraft.clinician
                    }
                    onChange={(
                      event,
                    ) => {
                      setReceptionDraft(
                        (
                          current,
                        ) => ({
                          ...current,
                          clinician:
                            event.target
                              .value,
                        }),
                      );
                    }}
                  >

                    <option value="">
                      담당 의료진 선택
                    </option>

                    {receptionDraft.clinician && (
                      <option
                        value={
                          receptionDraft.clinician
                        }
                      >
                        {receptionDraft.clinician}
                      </option>
                    )}

                  </select>

                  {!selectedAppointment && (
                    <small>
                      진료과별 담당의 목록 API 연결 후 선택 항목을 채울 수 있습니다.
                    </small>
                  )}

                </label>


                <label className="reception-field">

                  <span>
                    접수 채널
                    <em>
                      *
                    </em>
                  </span>

                  <select
                    value={
                      receptionDraft.channel
                    }
                    onChange={(
                      event,
                    ) => {
                      setReceptionDraft(
                        (
                          current,
                        ) => ({
                          ...current,
                          channel:
                            event.target
                              .value,
                        }),
                      );
                    }}
                  >

                    <option value="EMERGENCY_ROOM">
                      응급실
                    </option>

                    <option value="OUTPATIENT_DESK">
                      외래 접수
                    </option>

                    <option value="APPOINTMENT">
                      예약
                    </option>

                  </select>

                </label>


                <label className="reception-field">

                  <span>
                    우선순위
                    <em>
                      *
                    </em>
                  </span>

                  <select
                    value={
                      receptionDraft.priority
                    }
                    onChange={(
                      event,
                    ) => {
                      setReceptionDraft(
                        (
                          current,
                        ) => ({
                          ...current,
                          priority:
                            event.target
                              .value,
                        }),
                      );
                    }}
                  >

                    <option value="URGENT">
                      높음 (URGENT)
                    </option>

                    <option value="NORMAL">
                      보통 (NORMAL)
                    </option>

                    <option value="EMERGENCY">
                      응급 (EMERGENCY)
                    </option>

                  </select>

                </label>


                <label className="reception-field">

                  <span>
                    비고
                  </span>

                  <textarea
                    value={
                      receptionDraft.memo
                    }
                    onChange={(
                      event,
                    ) => {
                      setReceptionDraft(
                        (
                          current,
                        ) => ({
                          ...current,
                          memo:
                            event.target
                              .value,
                        }),
                      );
                    }}
                    placeholder="추가 메모를 입력하세요. (선택)"
                    maxLength={200}
                  />

                  <small className="reception-field__counter">
                    {receptionDraft.memo.length}/200
                  </small>

                </label>

              </section>


              <footer className="reception-register-actions">

                <span>
                  현재 API에는 환자 · 내원유형 · 예약 ID만 저장됩니다.
                  나머지 접수 항목은 Backend 계약 확정 후 payload에 연결해야 합니다.
                </span>


                <button
                  type="button"
                  disabled={
                    busy !== null ||
                    appointmentLoading ||
                    (
                      visitMode ===
                        "APPOINTMENT" &&
                      !appointmentId
                    )
                  }
                  onClick={() => {
                    void registerEncounter();
                  }}
                >
                  {busy ===
                  "REGISTER_ENCOUNTER"
                    ? "접수 처리 중..."
                    : "접수 완료 · 초기평가로 이동 →"}
                </button>

              </footer>

            </div>
          )}

        </aside>

      </div>

    </section>
  );
}
