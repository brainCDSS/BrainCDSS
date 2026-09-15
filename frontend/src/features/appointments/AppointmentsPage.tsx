import {
  useCallback,
  useEffect,
  useMemo,
  useState,
} from "react";

import type { LoginUser } from "../auth/types";
import {
  getClinicians,
} from "../assessments/api";
import type {
  Clinician,
} from "../assessments/types";

import {
  acceptAppointment,
  completeAppointment,
  correctAppointment,
  getAppointmentDetail,
  getAppointmentRequests,
  getActiveHospitals,
  getClinicianSchedule,
  getHospitalDetail,
  getStaffAppointments,
  rejectAppointment,
  saveClinicianSchedule,
} from "./api";

import type {
  ScheduleRule,
  StaffAppointment,
} from "./types";

import "./appointments.css";


type PageTab =
  | "appointments"
  | "schedule"
  | "requests"
  | "manage";


interface AppointmentSummaryCounts {
  requested: number | null;
  confirmed: number | null;
  inProgress: number | null;
  completed: number | null;
}


const APPOINTMENTS_PER_PAGE = 5;
const CALENDAR_START_HOUR = 8;
const CALENDAR_END_HOUR = 18;
const CALENDAR_SLOT_MINUTES = 30;


/* =========================================================
 * 예약 상태
 * ======================================================= */

const STATUS_OPTIONS = [
  "",
  "REQUESTED",
  "CONFIRMED",
  "IN_PROGRESS",
  "COMPLETED",
  "CANCELLED",
  "REJECTED",
];


const STATUS_LABELS: Record<string, string> = {
  REQUESTED: "승인 대기",
  CONFIRMED: "예약 확정",
  IN_PROGRESS: "진료 중",
  COMPLETED: "진료 완료",
  CANCELLED: "예약 취소",
  REJECTED: "예약 거절",
};


function statusLabel(status?: string) {
  if (!status) {
    return "-";
  }

  return STATUS_LABELS[status] ?? status;
}


function requestTypeLabel(requestType?: string | null) {
  if (!requestType) {
    return "-";
  }

  if (requestType === "NEW") {
    return "초진";
  }

  if (requestType === "RESCHEDULE") {
    return "예약 변경";
  }

  return requestType;
}


const WEEKDAYS = [
  "월",
  "화",
  "수",
  "목",
  "금",
  "토",
  "일",
];


/* =========================================================
 * 날짜 / 예약 Utility
 * ======================================================= */

function todayValue() {
  const now = new Date();

  return [
    now.getFullYear(),
    String(now.getMonth() + 1).padStart(2, "0"),
    String(now.getDate()).padStart(2, "0"),
  ].join("-");
}


function dateValue(value: Date) {
  return [
    value.getFullYear(),
    String(value.getMonth() + 1).padStart(2, "0"),
    String(value.getDate()).padStart(2, "0"),
  ].join("-");
}


function addDays(value: string, days: number) {
  const date = new Date(`${value}T12:00:00`);
  date.setDate(date.getDate() + days);
  return dateValue(date);
}


function startOfWeek(value: string) {
  const date = new Date(`${value}T12:00:00`);
  const day = date.getDay();
  date.setDate(date.getDate() - (day === 0 ? 6 : day - 1));
  return dateValue(date);
}


function minutesFromMidnight(value: string) {
  const [hour, minute] = value.split(":").map(Number);
  return hour * 60 + minute;
}


function appointmentId(
  item: StaffAppointment & {
    id?: string;
  },
) {
  return (
    item.appointment_id ||
    item.id ||
    ""
  );
}


function appointmentStart(
  item: StaffAppointment,
) {
  const requestItem =
    item as StaffAppointment & {
      current_slot?: {
        start_at?: string | null;
      } | null;
    };

  return (
    item.start_at ??
    item.slot?.start_at ??
    item.requested_slot?.start_at ??
    requestItem.current_slot?.start_at ??
    null
  );
}


function formatTime(
  value?: string | null,
) {
  if (!value) {
    return "-";
  }

  const date = new Date(value);

  if (Number.isNaN(date.getTime())) {
    return value;
  }

  return date.toLocaleTimeString(
    "ko-KR",
    {
      hour: "2-digit",
      minute: "2-digit",
      hour12: false,
    },
  );
}


function formatDateTime(
  value?: string | null,
) {
  if (!value) {
    return "-";
  }

  const date = new Date(value);

  if (Number.isNaN(date.getTime())) {
    return value;
  }

  return date.toLocaleString(
    "ko-KR",
  );
}


function normalize(
  items: Array<
    StaffAppointment & {
      id?: string;
    }
  >,
) {
  return items
    .map((item) => ({
      ...item,
      appointment_id:
        appointmentId(item),
    }))
    .filter(
      (item) =>
        item.appointment_id,
    );
}


type StaffAppointmentsApiResponse =
  Awaited<
    ReturnType<
      typeof getStaffAppointments
    >
  >;


function appointmentCount(
  response: StaffAppointmentsApiResponse,
) {
  if (typeof response.count === "number") {
    return response.count;
  }

  return (
    response.results ??
    response.appointments ??
    []
  ).length;
}


function patientSupplement(
  item: StaffAppointment,
) {
  const patient =
    item.patient as
      | (
          NonNullable<
            StaffAppointment["patient"]
          > & {
            sex?: string | null;
            gender?: string | null;
            birth_date?: string | null;
            age?: number | null;
          }
        )
      | undefined;

  if (!patient) {
    return "";
  }

  const values: string[] = [];

  const sex =
    patient.sex ??
    patient.gender;

  if (sex) {
    const normalized =
      String(sex).toUpperCase();

    values.push(
      normalized === "M"
        ? "남"
        : normalized === "F"
          ? "여"
          : String(sex),
    );
  }

  let age =
    patient.age ?? null;

  if (
    age === null &&
    patient.birth_date
  ) {
    const birth =
      new Date(
        patient.birth_date,
      );

    if (
      !Number.isNaN(
        birth.getTime(),
      )
    ) {
      const now =
        new Date();

      age =
        now.getFullYear() -
        birth.getFullYear();

      const beforeBirthday =
        now.getMonth() <
          birth.getMonth() ||
        (
          now.getMonth() ===
            birth.getMonth() &&
          now.getDate() <
            birth.getDate()
        );

      if (beforeBirthday) {
        age -= 1;
      }
    }
  }

  if (age !== null) {
    values.push(
      `${age}세`,
    );
  }

  if (patient.birth_date) {
    values.push(
      patient.birth_date.replaceAll(
        "-",
        ".",
      ),
    );
  }

  return values.join("  |  ");
}


function appointmentRequestReason(
  item: StaffAppointment,
) {
  const extended =
    item as StaffAppointment & {
      request_reason?: string | null;
      reason?: string | null;
      memo?: string | null;
      note?: string | null;
    };

  return (
    extended.request_reason ??
    extended.reason ??
    extended.memo ??
    extended.note ??
    null
  );
}


function hasPendingAppointmentRequest(
  item: StaffAppointment,
) {
  return (
    item.status === "REQUESTED" ||
    Boolean(
      item.requested_slot_id ||
        item.requested_slot,
    )
  );
}


/* =========================================================
 * 예약 상태 정정
 * ---------------------------------------------------------
 * [API 정합성 확인 필요]
 *
 * 프론트 1차 범위는 간호사가 잘못 승인/거절한 예약을
 * 다시 승인 대기(REQUESTED) 상태로 돌리는 경우만 준비한다.
 * 최종 허용 전이는 백엔드 계약에서 반드시 검증한다.
 * ======================================================= */

function correctionTargetStatus(
  item: StaffAppointment,
) {
  if (
    item.status === "CONFIRMED" ||
    item.status === "REJECTED"
  ) {
    return "REQUESTED";
  }

  return null;
}


function can(
  user: LoginUser,
  permission: string,
) {
  return user.permissions.includes(
    permission,
  );
}


function WeeklyScheduleCalendar({
  weekStart,
  onWeekChange,
  schedule,
  appointments,
}: {
  weekStart: string;
  onWeekChange: (value: string) => void;
  schedule: ScheduleRule[];
  appointments: StaffAppointment[];
}) {
  const dates = Array.from(
    { length: 7 },
    (_, index) => addDays(weekStart, index),
  );
  const slots = Array.from(
    {
      length:
        ((CALENDAR_END_HOUR - CALENDAR_START_HOUR) * 60) /
          CALENDAR_SLOT_MINUTES +
        1,
    },
    (_, index) => {
      const minutes =
        CALENDAR_START_HOUR * 60 + index * CALENDAR_SLOT_MINUTES;
      return `${String(Math.floor(minutes / 60)).padStart(2, "0")}:${String(
        minutes % 60,
      ).padStart(2, "0")}`;
    },
  );
  const calendarMinutes =
    (CALENDAR_END_HOUR - CALENDAR_START_HOUR) * 60;
  const today = todayValue();

  return (
    <section className="weekly-schedule-card">
      <header className="weekly-schedule-heading">
        <div>
          <h3>내 진료 스케줄</h3>
          <p>확정된 진료 스케줄과 예약 환자를 주간 단위로 확인합니다.</p>
        </div>
        <div className="weekly-schedule-navigation">
          <button type="button" onClick={() => onWeekChange(addDays(weekStart, -7))}>
            이전 주
          </button>
          <strong>
            {weekStart.replaceAll("-", ".")} ~ {addDays(weekStart, 6).replaceAll("-", ".")}
          </strong>
          <button type="button" onClick={() => onWeekChange(addDays(weekStart, 7))}>
            다음 주
          </button>
          <button type="button" onClick={() => onWeekChange(startOfWeek(todayValue()))}>
            오늘
          </button>
        </div>
      </header>

      <div className="weekly-calendar-scroll">
        <div className="weekly-calendar">
          <div className="weekly-calendar-corner">시간</div>
          {dates.map((day, index) => (
            <div
              className={`weekly-calendar-day${day === today ? " is-today" : ""}${index === 6 ? " is-sunday" : ""}`}
              key={day}
            >
              {`${WEEKDAYS[index]} ${Number(day.slice(5, 7))}.${Number(day.slice(8, 10))}`}
            </div>
          ))}

          <div className="weekly-calendar-times">
            {slots.map((slot) => <span key={slot}>{slot}</span>)}
          </div>

          {dates.map((day, dayIndex) => {
            const rules = schedule.filter(
              (rule) =>
                rule.is_active &&
                rule.weekday === dayIndex &&
                rule.effective_from <= day &&
                (!rule.effective_to || rule.effective_to >= day),
            );
            const dayAppointments = appointments.filter((item) => {
              const start = appointmentStart(item);
              return start ? dateValue(new Date(start)) === day : false;
            });

            return (
              <div className="weekly-calendar-column" key={day}>
                {slots.slice(0, -1).map((slot) => (
                  <span className="weekly-calendar-line" key={slot} />
                ))}
                {rules.map((rule) => {
                  const start = Math.max(
                    minutesFromMidnight(rule.start_time),
                    CALENDAR_START_HOUR * 60,
                  );
                  const end = Math.min(
                    minutesFromMidnight(rule.end_time),
                    CALENDAR_END_HOUR * 60,
                  );
                  return end > start ? (
                    <span
                      className="weekly-calendar-availability"
                      key={rule.id ?? `${rule.weekday}-${rule.start_time}`}
                      style={{
                        top: `${((start - CALENDAR_START_HOUR * 60) / calendarMinutes) * 100}%`,
                        height: `${((end - start) / calendarMinutes) * 100}%`,
                      }}
                    />
                  ) : null;
                })}
                {dayAppointments.map((item) => {
                  const startValue = appointmentStart(item);
                  if (!startValue) return null;
                  const startDate = new Date(startValue);
                  const start = startDate.getHours() * 60 + startDate.getMinutes();
                  const endValue = item.end_at ?? item.slot?.end_at;
                  const endDate = endValue ? new Date(endValue) : null;
                  const end = endDate && !Number.isNaN(endDate.getTime())
                    ? endDate.getHours() * 60 + endDate.getMinutes()
                    : start + CALENDAR_SLOT_MINUTES;
                  const supplement = patientSupplement(item);

                  return (
                    <article
                      className={`weekly-appointment is-${item.status.toLowerCase()}`}
                      key={appointmentId(item)}
                      style={{
                        top: `${((start - CALENDAR_START_HOUR * 60) / calendarMinutes) * 100}%`,
                        height: `${Math.max(((end - start) / calendarMinutes) * 100, 5)}%`,
                      }}
                    >
                      <strong>{item.patient?.name ?? "환자명 미제공"}</strong>
                      {supplement && <span>{supplement}</span>}
                      <span>{requestTypeLabel(item.request_type)}</span>
                    </article>
                  );
                })}
              </div>
            );
          })}

          {schedule.filter((rule) => rule.is_active).length === 0 &&
            appointments.length === 0 && (
              <div className="weekly-calendar-empty">
                등록된 스케줄이 없습니다.
              </div>
            )}
        </div>
      </div>
    </section>
  );
}


/* =========================================================
 * Component
 * ======================================================= */

export default function AppointmentsPage({
  currentUser,
}: {
  currentUser: LoginUser;
}) {
  const [
    activeTab,
    setActiveTab,
  ] = useState<PageTab>(
    "appointments",
  );

  const [
    date,
    setDate,
  ] = useState(
    todayValue(),
  );

  const [
    status,
    setStatus,
  ] = useState("");

  const [
    search,
    setSearch,
  ] = useState("");

  const [
    clinicianId,
    setClinicianId,
  ] = useState("");

  const [
    clinicians,
    setClinicians,
  ] = useState<Clinician[]>([]);

  const [
    appointments,
    setAppointments,
  ] = useState<
    StaffAppointment[]
  >([]);

  const [
    requests,
    setRequests,
  ] = useState<
    StaffAppointment[]
  >([]);

  const [
    selected,
    setSelected,
  ] = useState<
    StaffAppointment | null
  >(null);

  const [
    schedule,
    setSchedule,
  ] = useState<
    ScheduleRule[]
  >([]);

  const [weekStart, setWeekStart] = useState(
    () => startOfWeek(todayValue()),
  );

  const [
    weeklyAppointments,
    setWeeklyAppointments,
  ] = useState<StaffAppointment[]>([]);

  const [
    draftRule,
    setDraftRule,
  ] = useState<ScheduleRule>({
    weekday: 0,
    start_time: "09:00",
    end_time: "17:00",
    slot_minutes: 30,
    effective_from:
      todayValue(),
    effective_to: null,
    is_active: true,
  });

  const [
    loading,
    setLoading,
  ] = useState(false);

  const [
    error,
    setError,
  ] = useState<
    string | null
  >(null);

  const [
    actionError,
    setActionError,
  ] = useState<
    string | null
  >(null);

  const [
    page,
    setPage,
  ] = useState(1);

  const [
    totalCount,
    setTotalCount,
  ] = useState(0);

  const [
    usesApiPagination,
    setUsesApiPagination,
  ] = useState(false);

  const [
    hasNextPage,
    setHasNextPage,
  ] = useState(false);

  const [
    hasPreviousPage,
    setHasPreviousPage,
  ] = useState(false);

  const [
    summaryCounts,
    setSummaryCounts,
  ] = useState<AppointmentSummaryCounts>({
    requested: null,
    confirmed: null,
    inProgress: null,
    completed: null,
  });

  const [
    summaryLoading,
    setSummaryLoading,
  ] = useState(false);

  const [
    rejectTarget,
    setRejectTarget,
  ] = useState<StaffAppointment | null>(
    null,
  );

  const [
    rejectReason,
    setRejectReason,
  ] = useState("");

  const [
    rejectSubmitting,
    setRejectSubmitting,
  ] = useState(false);

  const [
    rejectError,
    setRejectError,
  ] = useState<string | null>(null);

  const [
    correctionTarget,
    setCorrectionTarget,
  ] = useState<StaffAppointment | null>(
    null,
  );

  const [
    correctionReason,
    setCorrectionReason,
  ] = useState("");

  const [
    correctionSubmitting,
    setCorrectionSubmitting,
  ] = useState(false);

  const [
    correctionError,
    setCorrectionError,
  ] = useState<string | null>(null);


  /* =========================================================
   * 권한
   * ======================================================= */

  const role =
    currentUser.role.code;

  const isDoctor =
    role === "NEUROLOGIST" ||
    role === "NEUROSURGEON";

  const isNurse =
    role === "NURSE";

  const isAdmin =
    role === "SYSTEM_ADMIN";

  const mayReadStaff =
    can(
      currentUser,
      "appointment.read.staff",
    );

  const mayManageSchedule =
    can(
      currentUser,
      "schedule.manage",
    );


  /* =========================================================
   * 예약 목록 조회
   * ======================================================= */

  const loadAppointments =
    useCallback(
      async () => {
        if (!mayReadStaff) {
          return;
        }

        setLoading(true);
        setError(null);

        try {
          if (status === "REQUESTED") {
            const response =
              await getAppointmentRequests({
                date,
                clinicianId:
                  clinicianId ||
                  undefined,
                page,
                pageSize:
                  APPOINTMENTS_PER_PAGE,
              });

            const items =
              normalize(
                response.results ??
                  [],
              );

            setAppointments(
              items,
            );

            setUsesApiPagination(
              true,
            );

            setTotalCount(
              response.count ??
                items.length,
            );

            setHasNextPage(
              response.next != null,
            );

            setHasPreviousPage(
              response.previous != null,
            );

            return;
          }

          const response =
            await getStaffAppointments(
              {
                date,
                clinicianId:
                  clinicianId ||
                  undefined,
                status:
                  status ||
                  undefined,
                page,
                pageSize:
                  APPOINTMENTS_PER_PAGE,
              },
            );

          const apiPaginated =
            Array.isArray(
              response.results,
            );

          const items =
            normalize(
              response.results ??
                response.appointments ??
                [],
            );

          setAppointments(
            items,
          );

          setUsesApiPagination(
            apiPaginated,
          );

          setTotalCount(
            apiPaginated
              ? response.count ??
                  items.length
              : items.length,
          );

          setHasNextPage(
            apiPaginated &&
              response.next !=
                null,
          );

          setHasPreviousPage(
            apiPaginated &&
              response.previous !=
                null,
          );
        } catch {
          setError(
            status === "REQUESTED"
              ? "승인 대기 예약 목록을 불러오지 못했습니다."
              : "예약 일정을 불러오지 못했습니다. 현재 계정의 역할과 권한을 확인해 주세요.",
          );
        } finally {
          setLoading(false);
        }
      },
      [
        clinicianId,
        date,
        mayReadStaff,
        page,
        status,
      ],
    );


  useEffect(() => {
    void loadAppointments();
  }, [loadAppointments]);


  /* =========================================================
   * 의료진 목록
   * ======================================================= */

  useEffect(() => {
    let active = true;

    const loadClinicians = async () => {
      try {
        const hospitalIds = currentUser.hospital?.id
          ? [currentUser.hospital.id]
          : (await getActiveHospitals()).results.map(
              (hospital) => hospital.id,
            );
        const hospitals = await Promise.all(
          hospitalIds.map(getHospitalDetail),
        );
        const departmentIds = hospitals.flatMap(
          (hospital) => hospital.departments.map(
            (department) => department.id,
          ),
        );
        const responses = await Promise.all(
          departmentIds.map(getClinicians),
        );
        const values = new Map<string, Clinician>();
        responses.forEach((response) => {
          response.clinicians.forEach((clinician) => {
            if (clinician.is_active) {
              values.set(clinician.id, clinician);
            }
          });
        });
        if (active) {
          const nextClinicians = [...values.values()].sort(
            (left, right) =>
              left.name.localeCompare(right.name, "ko"),
          );

          setClinicians(nextClinicians);
          setClinicianId((currentClinicianId) => {
            if (isDoctor) {
              return nextClinicians.find(
                (clinician) =>
                  clinician.user_id === currentUser.id,
              )?.id ?? "";
            }

            if (
              currentClinicianId &&
              nextClinicians.some(
                (clinician) =>
                  clinician.id === currentClinicianId,
              )
            ) {
              return currentClinicianId;
            }

            return nextClinicians[0]?.id ?? "";
          });
        }
      } catch {
        if (active) {
          setClinicians([]);
        }
      }
    };

    void loadClinicians();
    return () => {
      active = false;
    };
  }, [currentUser.hospital?.id, currentUser.id, isDoctor]);

  const clinicianOptions = useMemo(
    () => clinicians.map(
      (clinician) => [clinician.id, clinician.name] as const,
    ),
    [clinicians],
  );


  /* =========================================================
   * 검색
   * ======================================================= */

  const visibleAppointments =
    useMemo(() => {
      const keyword =
        search
          .trim()
          .toLowerCase();

      if (!keyword) {
        return appointments;
      }

      return appointments.filter(
        (item) =>
          `${
            item.patient
              ?.name ?? ""
          } ${
            item.patient
              ?.patient_no ??
            ""
          } ${
            item.patient_id ??
            ""
          }`
            .toLowerCase()
            .includes(
              keyword,
            ),
      );
    }, [
      appointments,
      search,
    ]);


  /* =========================================================
   * Pagination
   * ======================================================= */

  const pagedAppointments =
    useMemo(() => {
      if (
        usesApiPagination
      ) {
        return visibleAppointments;
      }

      const start =
        (page - 1) *
        APPOINTMENTS_PER_PAGE;

      return visibleAppointments.slice(
        start,
        start +
          APPOINTMENTS_PER_PAGE,
      );
    }, [
      page,
      usesApiPagination,
      visibleAppointments,
    ]);


  const visibleTotal =
    usesApiPagination
      ? totalCount
      : visibleAppointments.length;


  const pageCount =
    Math.max(
      1,
      Math.ceil(
        visibleTotal /
          APPOINTMENTS_PER_PAGE,
      ),
    );


  useEffect(() => {
    setPage(1);
  }, [
    search,
    status,
    date,
    clinicianId,
  ]);


  /* =========================================================
   * 오늘 예약 상태 요약
   * ---------------------------------------------------------
   * 목록의 현재 status / page와 분리해서 조회한다.
   * ======================================================= */

  const loadSummaryCounts =
    useCallback(
      async () => {
        if (!mayReadStaff) {
          setSummaryCounts({
            requested: null,
            confirmed: null,
            inProgress: null,
            completed: null,
          });
          return;
        }

        setSummaryLoading(true);

        try {
          const [
            requestedResponse,
            confirmedResponse,
            inProgressResponse,
            completedResponse,
          ] = await Promise.all([
            getAppointmentRequests({
              date,
              clinicianId:
                clinicianId ||
                undefined,
              page: 1,
              pageSize: 1,
            }),

            getStaffAppointments({
              date,
              clinicianId:
                clinicianId ||
                undefined,
              status: "CONFIRMED",
              page: 1,
              pageSize: 1,
            }),

            getStaffAppointments({
              date,
              clinicianId:
                clinicianId ||
                undefined,
              status: "IN_PROGRESS",
              page: 1,
              pageSize: 1,
            }),

            getStaffAppointments({
              date,
              clinicianId:
                clinicianId ||
                undefined,
              status: "COMPLETED",
              page: 1,
              pageSize: 1,
            }),
          ]);

          setSummaryCounts({
            requested:
              requestedResponse.count ??
              requestedResponse.results.length,

            confirmed:
              appointmentCount(
                confirmedResponse,
              ),

            inProgress:
              appointmentCount(
                inProgressResponse,
              ),

            completed:
              appointmentCount(
                completedResponse,
              ),
          });
        } catch {
          setSummaryCounts({
            requested: null,
            confirmed: null,
            inProgress: null,
            completed: null,
          });
        } finally {
          setSummaryLoading(false);
        }
      },
      [
        clinicianId,
        date,
        mayReadStaff,
      ],
    );


  useEffect(() => {
    void loadSummaryCounts();
  }, [loadSummaryCounts]);


  /* =========================================================
   * 예약 상세
   * ======================================================= */

  async function selectAppointment(
    item: StaffAppointment,
  ) {
    setActionError(null);

    try {
      const detail =
        await getAppointmentDetail(
          item.appointment_id,
        );

      setSelected({
        ...detail,
        appointment_id:
          appointmentId(
            detail,
          ),
      });
    } catch {
      setSelected(item);

      setActionError(
        "예약 상세를 불러오지 못했습니다.",
      );
    }
  }


  /* =========================================================
   * 진료 완료
   * ======================================================= */

  async function handleComplete() {
    if (
      !selected ||
      !isDoctor ||
      !can(
        currentUser,
        "appointment.complete",
      )
    ) {
      return;
    }

    setActionError(null);

    try {
      await completeAppointment(
        selected.appointment_id,
      );

      await Promise.all([
        loadAppointments(),
        loadSummaryCounts(),
      ]);

      setSelected(null);
    } catch {
      setActionError(
        "완료 처리에 실패했습니다.",
      );
    }
  }


  /* =========================================================
   * 예약 요청
   * ======================================================= */

  const loadRequests =
    useCallback(
      async () => {
        if (
          !isNurse ||
          !mayReadStaff
        ) {
          return;
        }

        setLoading(true);
        setError(null);

        try {
          const response =
            await getAppointmentRequests(
              {
                date,
                clinicianId:
                  clinicianId ||
                  undefined,
              },
            );

          setRequests(
            normalize(
              response.results,
            ),
          );
        } catch {
          setError(
            "예약 요청을 불러오지 못했습니다.",
          );
        } finally {
          setLoading(false);
        }
      },
      [
        clinicianId,
        date,
        isNurse,
        mayReadStaff,
      ],
    );


  useEffect(() => {
    if (activeTab !== "requests") {
      return;
    }

    void loadRequests();
  }, [
    activeTab,
    loadRequests,
  ]);


  function openRejectModal(
    item: StaffAppointment,
  ) {
    setActionError(null);
    setRejectError(null);
    setRejectReason("");
    setRejectTarget(item);
  }


  function closeRejectModal() {
    if (rejectSubmitting) {
      return;
    }

    setRejectTarget(null);
    setRejectReason("");
    setRejectError(null);
  }


  async function processRequest(
    item: StaffAppointment,
    action:
      | "accept"
      | "reject",
  ) {
    if (!isNurse) {
      return;
    }

    setActionError(null);

    if (action === "reject") {
      openRejectModal(item);
      return;
    }

    try {
      await acceptAppointment(
        item.appointment_id,
      );

      await Promise.all([
        loadRequests(),
        loadAppointments(),
        loadSummaryCounts(),
      ]);

      setSelected(null);
    } catch {
      setActionError(
        "예약 승인에 실패했습니다.",
      );
    }
  }


  async function submitReject() {
    if (!rejectTarget || !isNurse) {
      return;
    }

    const reason =
      rejectReason.trim();

    if (!reason) {
      setRejectError(
        "거절 사유를 입력해 주세요.",
      );
      return;
    }

    setRejectSubmitting(true);
    setRejectError(null);
    setActionError(null);

    try {
      await rejectAppointment(
        rejectTarget.appointment_id,
        reason,
      );

      await Promise.all([
        loadRequests(),
        loadAppointments(),
        loadSummaryCounts(),
      ]);

      if (
        selected?.appointment_id ===
        rejectTarget.appointment_id
      ) {
        setSelected(null);
      }

      setRejectTarget(null);
      setRejectReason("");
    } catch {
      setRejectError(
        "예약 거절 처리에 실패했습니다.",
      );
    } finally {
      setRejectSubmitting(false);
    }
  }


  /* =========================================================
   * 예약 상태 정정
   * ======================================================= */

  function openCorrectionModal(
    item: StaffAppointment,
  ) {
    if (
      !isNurse ||
      !correctionTargetStatus(item)
    ) {
      return;
    }

    setActionError(null);
    setCorrectionError(null);
    setCorrectionReason("");
    setCorrectionTarget(item);
  }


  function closeCorrectionModal() {
    if (correctionSubmitting) {
      return;
    }

    setCorrectionTarget(null);
    setCorrectionReason("");
    setCorrectionError(null);
  }


  async function submitCorrection() {
    if (
      !correctionTarget ||
      !isNurse
    ) {
      return;
    }

    const targetStatus =
      correctionTargetStatus(
        correctionTarget,
      );

    if (!targetStatus) {
      setCorrectionError(
        "현재 상태는 정정 대상으로 처리할 수 없습니다.",
      );
      return;
    }

    const reason =
      correctionReason.trim();

    if (!reason) {
      setCorrectionError(
        "상태 정정 사유를 입력해 주세요.",
      );
      return;
    }

    setCorrectionSubmitting(true);
    setCorrectionError(null);
    setActionError(null);

    try {
      await correctAppointment(
        correctionTarget.appointment_id,
        {
          target_status: targetStatus,
          reason,
        },
      );

      await Promise.all([
        loadRequests(),
        loadAppointments(),
        loadSummaryCounts(),
      ]);

      if (
        selected?.appointment_id ===
        correctionTarget.appointment_id
      ) {
        setSelected(null);
      }

      setCorrectionTarget(null);
      setCorrectionReason("");
    } catch {
      setCorrectionError(
        "예약 상태 정정에 실패했습니다.",
      );
    } finally {
      setCorrectionSubmitting(false);
    }
  }


  /* =========================================================
   * 스케줄
   * ======================================================= */

  const loadSchedule = useCallback(async () => {
    if (!clinicianId) {
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const scheduleFrom =
        activeTab === "manage" ? weekStart : date;
      const scheduleTo =
        activeTab === "manage" ? addDays(weekStart, 6) : date;
      const response =
        await getClinicianSchedule(
          clinicianId,
          scheduleFrom,
          scheduleTo,
        );

      setSchedule(
        (
          response.rules ??
          response.results ??
          []
        ).filter(
          (rule) =>
            (
              !rule.clinician_id ||
              rule.clinician_id === clinicianId
            ) &&
            (!isDoctor || rule.is_active),
        ),
      );
    } catch {
      setError(
        "의료진 스케줄을 불러오지 못했습니다.",
      );
    } finally {
      setLoading(false);
    }
  }, [activeTab, clinicianId, date, isDoctor, weekStart]);


  useEffect(() => {
    if (
      clinicianId &&
      (
        activeTab === "schedule" ||
        activeTab === "manage"
      )
    ) {
      void loadSchedule();
    }
  }, [activeTab, clinicianId, loadSchedule]);


  useEffect(() => {
    if (activeTab !== "manage" || !clinicianId) {
      return;
    }

    let active = true;

    const loadWeeklyAppointments = async () => {
      try {
        const response = await getStaffAppointments({
          from: weekStart,
          to: addDays(weekStart, 6),
          clinicianId,
          page: 1,
          pageSize: 100,
        });
        const items = normalize(
          response.results ?? response.appointments ?? [],
        ).filter((item) =>
          ["CONFIRMED", "IN_PROGRESS", "COMPLETED"].includes(
            item.status,
          ),
        );

        if (active) {
          setWeeklyAppointments(items);
        }
      } catch {
        if (active) {
          setWeeklyAppointments([]);
        }
      }
    };

    void loadWeeklyAppointments();
    return () => {
      active = false;
    };
  }, [activeTab, clinicianId, weekStart]);


  async function saveSchedule() {
    if (
      !clinicianId ||
      !mayManageSchedule
    ) {
      return;
    }

    setActionError(null);

    try {
      const response =
        await saveClinicianSchedule(
          clinicianId,
          schedule,
        );

      setSchedule(
        response.rules ??
          response.results ??
          [],
      );
    } catch {
      setActionError(
        "스케줄 저장에 실패했습니다.",
      );
    }
  }


  /* =========================================================
   * Tab
   * ======================================================= */

  function openTab(
    tab: PageTab,
  ) {
    setActiveTab(tab);
    setError(null);
    setActionError(null);

    /*
     * 진료 일정은 예약 상태별 업무 목록이 아니라
     * 선택한 날짜의 전체 일정을 보는 탭이므로,
     * 예약 목록에서 사용하던 숨은 status 필터를 제거한다.
     */
    if (tab === "schedule") {
      setStatus("");
      setPage(1);
      setSelected(null);
    }

  }


  /* =========================================================
   * Render
   * ======================================================= */

  return (
    <section className="appointment-page">

      {/* =====================================================
       * Page Header
       * =================================================== */}

      <header className="appointment-heading">
        <div>
          <span>
            예약 및 진료 일정
          </span>

          <div className="appointment-heading__title-row">
            <h2>
              예약 · 일정
            </h2>

            <p>
              예약 및 의료진 일정을
              조회하고 관리합니다.
            </p>
          </div>
        </div>

      </header>


      {/* =====================================================
       * 오늘 일정
       * =================================================== */}

      <section
        className="appointment-today"
        aria-label="오늘 일정 요약"
      >
        <header>
          <div>
            <span>
              오늘 일정 요약
            </span>

            <h3>
              오늘 일정{" "}
              <strong>
                {date.replaceAll(
                  "-",
                  ".",
                )}
              </strong>
            </h3>
          </div>

          {summaryLoading && (
            <small>
              상태별 예약 건수를
              확인하는 중입니다.
            </small>
          )}
        </header>

        <div className="appointment-summary-grid">
          {[
            [
              "승인 대기",
              summaryLoading ||
              summaryCounts.requested ===
                null
                ? "-"
                : summaryCounts.requested,
            ],
            [
              "예약 확정",
              summaryLoading ||
              summaryCounts.confirmed ===
                null
                ? "-"
                : summaryCounts.confirmed,
            ],
            [
              "진료 중",
              summaryLoading ||
              summaryCounts.inProgress ===
                null
                ? "-"
                : summaryCounts.inProgress,
            ],
            [
              "진료 완료",
              summaryLoading ||
              summaryCounts.completed ===
                null
                ? "-"
                : summaryCounts.completed,
            ],
          ].map(
            ([
              label,
              value,
            ]) => (
              <article
                key={String(
                  label,
                )}
              >
                <span>
                  {label}
                </span>

                <strong>
                  {value}
                </strong>
              </article>
            ),
          )}
        </div>
      </section>


      {/* =====================================================
       * Main Tabs
       * =================================================== */}

      <nav
        className="appointment-tabs"
        aria-label="예약 일정 분류"
      >
        <button
          type="button"
          className={
            activeTab ===
            "appointments"
              ? "is-active"
              : ""
          }
          onClick={() =>
            openTab(
              "appointments",
            )
          }
        >
          예약 목록
        </button>

        <button
          type="button"
          className={
            activeTab ===
            "schedule"
              ? "is-active"
              : ""
          }
          onClick={() =>
            openTab(
              "schedule",
            )
          }
        >
          진료 일정
        </button>

        <button
          type="button"
          className={
            activeTab ===
            "requests"
              ? "is-active"
              : ""
          }
          onClick={() =>
            openTab(
              "requests",
            )
          }
          disabled={!isNurse}
        >
          예약 요청
        </button>

        <button
          type="button"
          className={
            activeTab ===
            "manage"
              ? "is-active"
              : ""
          }
          onClick={() =>
            openTab(
              "manage",
            )
          }
          disabled={
            !(
              isDoctor ||
              isNurse
            ) ||
            !mayManageSchedule
          }
        >
          스케줄 관리
        </button>
      </nav>


      {/* =====================================================
       * 예약 목록 / 진료 일정
       * =================================================== */}

      {(
        activeTab ===
          "appointments" ||
        activeTab ===
          "schedule"
      ) && (
        <div className="appointment-workspace">

          <main className="appointment-list-card">

            {/* 예약 목록일 때 상태 빠른 필터 표시 */}

            {activeTab ===
              "appointments" && (
              <div
                className="appointment-status-filters"
                aria-label="예약 상태"
              >
                {STATUS_OPTIONS.map(
                  (
                    value,
                  ) => (
                    <button
                      key={
                        value ||
                        "all"
                      }
                      type="button"
                      className={
                        status ===
                        value
                          ? "is-active"
                          : ""
                      }
                      aria-pressed={
                        status ===
                        value
                      }
                      onClick={() =>
                        setStatus(
                          value,
                        )
                      }
                    >
                      {value
                        ? statusLabel(
                            value,
                          )
                        : "전체"}
                    </button>
                  ),
                )}
              </div>
            )}


            {/* 검색 필터 */}

            <div className="appointment-filters">

              <label>
                환자 검색

                <input
                  value={search}
                  onChange={(
                    event,
                  ) =>
                    setSearch(
                      event
                        .target
                        .value,
                    )
                  }
                  placeholder="환자명, 환자번호 또는 ID"
                />
              </label>


              <label>
                날짜

                <input
                  type="date"
                  value={date}
                  onChange={(
                    event,
                  ) =>
                    setDate(
                      event
                        .target
                        .value,
                    )
                  }
                />
              </label>


              <label>
                담당 의료진

                <select
                  value={
                    clinicianId
                  }
                  onChange={(
                    event,
                  ) =>
                    setClinicianId(
                      event
                        .target
                        .value,
                    )
                  }
                >
                  <option value="">
                    전체
                  </option>

                  {clinicianOptions.map(
                    ([
                      id,
                      name,
                    ]) => (
                      <option
                        value={
                          id
                        }
                        key={
                          id
                        }
                      >
                        {name}
                      </option>
                    ),
                  )}
                </select>
              </label>
            </div>


            {/* 목록 메타 */}

            <div className="appointment-list-meta">
              <strong>
                총 {visibleTotal}건
                {" "}
                <span>
                  ({page}/{pageCount} 페이지)
                </span>
              </strong>

            </div>


            {/* 예약 목록 */}

            {!mayReadStaff ||
            isAdmin ? (
              <div className="appointment-empty">
                현재 역할에는
                의료진 예약 일정
                API 접근 권한이
                없습니다.
              </div>
            ) : loading ? (
              <div className="appointment-empty">
                불러오는 중...
              </div>
            ) : error ? (
              <div className="appointment-empty is-error">
                {error}
              </div>
            ) : pagedAppointments.length ===
              0 ? (
              <div className="appointment-empty">
                조회된 예약 일정이
                없습니다.
              </div>
            ) : (
              <div className="appointment-table-wrap">
                <table>
                  <thead>
                    <tr>
                      <th>
                        시간
                      </th>

                      <th>
                        환자
                      </th>

                      <th>
                        진료과
                      </th>

                      <th>
                        담당의
                      </th>

                      <th>
                        상태
                      </th>

                      <th>
                        예약 유형
                      </th>
                    </tr>
                  </thead>

                  <tbody>
                    {pagedAppointments.map(
                      (
                        item,
                      ) => (
                        <tr
                          key={
                            item.appointment_id
                          }
                          className={
                            selected?.appointment_id ===
                            item.appointment_id
                              ? "is-selected"
                              : ""
                          }
                          onClick={() =>
                            void selectAppointment(
                              item,
                            )
                          }
                        >
                          <td>
                            {formatTime(
                              appointmentStart(
                                item,
                              ),
                            )}
                          </td>

                          <td>
                            <strong>
                              {item
                                .patient
                                ?.name ??
                                item.patient_id ??
                                "-"}
                            </strong>

                            <small>
                              {item
                                .patient
                                ?.patient_no ??
                                ""}
                            </small>
                          </td>

                          <td>
                            <span className="appointment-department-label">
                              {item
                                .department
                                ?.name ??
                                item.department_id ??
                                "-"}
                            </span>
                          </td>

                          <td>
                            <span className="appointment-clinician-name">
                              {item
                                .clinician
                                ?.name ??
                                item.clinician_id ??
                                "-"}
                            </span>
                          </td>

                          <td>
                            <span
                              className={`appointment-status is-${item.status.toLowerCase()}`}
                            >
                              {statusLabel(
                                item.status,
                              )}
                            </span>
                          </td>

                          <td>
                            <span className="appointment-type-label">
                              {requestTypeLabel(
                                item.request_type,
                              )}
                            </span>
                          </td>

                        </tr>
                      ),
                    )}
                  </tbody>
                </table>
              </div>
            )}


            {/* Pagination */}

            {mayReadStaff &&
              !isAdmin &&
              !loading &&
              !error &&
              visibleTotal >
                0 && (
                <nav
                  className="appointment-pagination"
                  aria-label="예약 목록 페이지"
                >
                  <button
                    type="button"
                    aria-label="이전 페이지"
                    disabled={
                      page <=
                        1 ||
                      (
                        usesApiPagination &&
                        !hasPreviousPage
                      )
                    }
                    onClick={() =>
                      setPage(
                        (
                          current,
                        ) =>
                          Math.max(
                            1,
                            current -
                              1,
                          ),
                      )
                    }
                  >
                    ‹
                  </button>

                  <span>
                    <strong>
                      {page}
                    </strong>{" "}
                    /{" "}
                    {pageCount}
                  </span>

                  <button
                    type="button"
                    aria-label="다음 페이지"
                    disabled={
                      page >=
                        pageCount ||
                      (
                        usesApiPagination &&
                        !hasNextPage
                      )
                    }
                    onClick={() =>
                      setPage(
                        (
                          current,
                        ) =>
                          Math.min(
                            pageCount,
                            current +
                              1,
                          ),
                      )
                    }
                  >
                    ›
                  </button>
                </nav>
              )}
          </main>


          {/* =================================================
           * 예약 상세
           * =============================================== */}

          <aside className="appointment-detail-card">
            <header className="appointment-detail-heading">
              <div>
                <span>
                  예약 상세 정보
                </span>

                <h3>
                  환자 예약 상세
                </h3>
              </div>
            </header>

            {selected ? (
              <div className="appointment-detail-content">
                <section className="appointment-patient-summary">
                  <div className="appointment-patient-avatar">
                    {(
                      selected.patient?.name ??
                      "?"
                    ).slice(0, 1)}
                  </div>

                  <div className="appointment-patient-main">
                    <h4>
                      {selected.patient?.name ??
                        selected.patient_id ??
                        "환자 정보 없음"}
                    </h4>

                    {patientSupplement(
                      selected,
                    ) && (
                      <p className="appointment-patient-demographic">
                        {patientSupplement(
                          selected,
                        )}
                      </p>
                    )}

                    <p className="appointment-patient-number">
                      환자번호
                      <span aria-hidden="true">
                        |
                      </span>
                      {selected.patient?.patient_no ??
                        "정보 없음"}
                    </p>
                  </div>

                  <div className="appointment-patient-state">
                    <span
                      className={`appointment-status is-${selected.status.toLowerCase()}`}
                    >
                      {statusLabel(
                        selected.status,
                      )}
                    </span>

                    {selected.status ===
                      "REQUESTED" && (
                      <small>
                        신규 예약 요청
                      </small>
                    )}
                  </div>
                </section>

                {selected.requested_slot && (
                  <div className="appointment-request-notice">
                    일정 변경 승인 대기 요청이 있습니다.
                  </div>
                )}

                <section className="appointment-detail-section">
                  <h4>
                    예약 정보
                  </h4>

                  <dl>
                    <div>
                      <dt>예약 일시</dt>
                      <dd>
                        {formatDateTime(
                          appointmentStart(
                            selected,
                          ),
                        )}
                      </dd>
                    </div>

                    <div>
                      <dt>진료과</dt>
                      <dd>
                        {selected.department?.name ??
                          selected.department_id ??
                          "-"}
                      </dd>
                    </div>

                    <div>
                      <dt>담당의</dt>
                      <dd>
                        {selected.clinician?.name ??
                          selected.clinician_id ??
                          "-"}
                      </dd>
                    </div>

                    <div>
                      <dt>예약 유형</dt>
                      <dd>
                        {requestTypeLabel(
                          selected.request_type,
                        )}
                      </dd>
                    </div>
                  </dl>
                </section>

                <section className="appointment-detail-section">
                  <h4>
                    요청 정보
                  </h4>

                  <dl>
                    <div>
                      <dt>요청 시각</dt>
                      <dd>
                        {formatDateTime(
                          selected.requested_at,
                        )}
                      </dd>
                    </div>

                    <div
                      className={`is-request-reason ${
                        appointmentRequestReason(selected)
                          ? ""
                          : "is-empty"
                      }`}
                    >
                      <dt>
                        요청 사유
                      </dt>
                      <dd>
                        {appointmentRequestReason(
                          selected,
                        ) ?? "등록된 요청 사유 없음"}
                      </dd>
                    </div>

                    {selected.reschedule_requested_at && (
                      <div>
                        <dt>변경 요청 시각</dt>
                        <dd>
                          {formatDateTime(
                            selected.reschedule_requested_at,
                          )}
                        </dd>
                      </div>
                    )}

                    {selected.requested_slot && (
                      <div>
                        <dt>변경 희망 일정</dt>
                        <dd>
                          {formatDateTime(
                            selected.requested_slot.start_at,
                          )}
                        </dd>
                      </div>
                    )}
                  </dl>
                </section>

                {(
                  selected.confirmed_at ||
                  selected.completed_at ||
                  selected.rejection_reason ||
                  selected.cancel_reason ||
                  selected.handled_by
                ) && (
                  <section className="appointment-detail-section">
                    <h4>
                      처리 정보
                    </h4>

                    <dl>
                      {selected.confirmed_at && (
                        <div>
                          <dt>확정 시각</dt>
                          <dd>
                            {formatDateTime(
                              selected.confirmed_at,
                            )}
                          </dd>
                        </div>
                      )}

                      {selected.completed_at && (
                        <div>
                          <dt>완료 시각</dt>
                          <dd>
                            {formatDateTime(
                              selected.completed_at,
                            )}
                          </dd>
                        </div>
                      )}

                      {selected.handled_by && (
                        <div>
                          <dt>처리 담당자</dt>
                          <dd>
                            {selected.handled_by.name ??
                              selected.handled_by.id}
                          </dd>
                        </div>
                      )}

                      {selected.rejection_reason && (
                        <div className="is-reason">
                          <dt>거절 사유</dt>
                          <dd>
                            {selected.rejection_reason}
                          </dd>
                        </div>
                      )}

                      {selected.cancel_reason && (
                        <div className="is-reason">
                          <dt>취소 사유</dt>
                          <dd>
                            {selected.cancel_reason}
                          </dd>
                        </div>
                      )}
                    </dl>
                  </section>
                )}

                {hasPendingAppointmentRequest(
                  selected,
                ) &&
                  isNurse && (
                    <div className="appointment-actions appointment-request-actions">
                      <button
                        type="button"
                        className="is-primary"
                        disabled={
                          !can(
                            currentUser,
                            "appointment.accept",
                          )
                        }
                        onClick={() =>
                          void processRequest(
                            selected,
                            "accept",
                          )
                        }
                      >
                        예약 승인
                      </button>

                      <button
                        type="button"
                        className="is-danger"
                        disabled={
                          !can(
                            currentUser,
                            "appointment.reject",
                          )
                        }
                        onClick={() =>
                          void processRequest(
                            selected,
                            "reject",
                          )
                        }
                      >
                        예약 거절
                      </button>
                    </div>
                  )}

                {selected.status ===
                  "CONFIRMED" &&
                  isDoctor &&
                  can(
                    currentUser,
                    "appointment.complete",
                  ) && (
                    <div className="appointment-actions">
                      <button
                        type="button"
                        className="is-primary"
                        onClick={() =>
                          void handleComplete()
                        }
                      >
                        완료 처리
                      </button>
                    </div>
                  )}

                {isNurse &&
                  correctionTargetStatus(
                    selected,
                  ) && (
                    <div className="appointment-actions">
                      <button
                        type="button"
                        className="is-secondary"
                        onClick={() =>
                          openCorrectionModal(
                            selected,
                          )
                        }
                      >
                        상태 정정
                      </button>
                    </div>
                  )}

                {actionError && (
                  <p className="appointment-action-error">
                    {actionError}
                  </p>
                )}
              </div>
            ) : (
              <div className="appointment-empty is-detail-empty">
                <strong>
                  예약을 선택해 주세요.
                </strong>
                <span>
                  환자를 선택하면 예약 정보와 처리 기능이 표시됩니다.
                </span>
              </div>
            )}
          </aside>
        </div>
      )}


      {/* =====================================================
       * 예약 요청
       * =================================================== */}

      {activeTab ===
        "requests" && (
        <section className="appointment-list-card">

          {!isNurse ? (
            <div className="appointment-empty">
              예약 요청 처리는
              간호사 역할에서만
              사용할 수 있습니다.
            </div>
          ) : loading ? (
            <div className="appointment-empty">
              불러오는 중...
            </div>
          ) : error ? (
            <div className="appointment-empty is-error">
              {error}
            </div>
          ) : requests.length ===
            0 ? (
            <div className="appointment-empty">
              승인 대기 예약
              요청이 없습니다.
            </div>
          ) : (
            <div className="appointment-request-list">
              {requests.map(
                (item) => (
                  <article
                    key={
                      item.appointment_id
                    }
                  >
                    <div>
                      <strong>
                        {item
                          .patient
                          ?.name ??
                          item.patient_id ??
                          "환자 정보 없음"}
                      </strong>

                      <span>
                        {formatDateTime(
                          item.requested_at,
                        )}
                        {" · "}
                        {requestTypeLabel(
                          item.request_type,
                        )}
                      </span>
                    </div>

                    <span className="appointment-status is-requested">
                      {statusLabel(
                        item.status,
                      )}
                    </span>

                    <div>
                      <button
                        type="button"
                        disabled={
                          !can(
                            currentUser,
                            "appointment.accept",
                          )
                        }
                        onClick={() =>
                          void processRequest(
                            item,
                            "accept",
                          )
                        }
                      >
                        승인
                      </button>

                      <button
                        type="button"
                        disabled={
                          !can(
                            currentUser,
                            "appointment.reject",
                          )
                        }
                        onClick={() =>
                          void processRequest(
                            item,
                            "reject",
                          )
                        }
                      >
                        거절
                      </button>
                    </div>
                  </article>
                ),
              )}
            </div>
          )}

          {actionError && (
            <p className="appointment-action-error">
              {actionError}
            </p>
          )}
        </section>
      )}


      {/* =====================================================
       * 스케줄 관리
       * =================================================== */}

      {activeTab === "manage" && (
        <>
          <div className="weekly-schedule-clinician">
            <span>담당 의료진</span>
            {isDoctor ? (
              <strong>
                {clinicians.find((clinician) => clinician.id === clinicianId)?.name ?? currentUser.name}
              </strong>
            ) : (
              <select
                value={clinicianId}
                onChange={(event) => setClinicianId(event.target.value)}
              >
                <option value="">담당 의료진 선택</option>
                {clinicianOptions.map(([id, name]) => (
                  <option value={id} key={id}>{name}</option>
                ))}
              </select>
            )}
          </div>
          {clinicianId ? (
            <WeeklyScheduleCalendar
              weekStart={weekStart}
              onWeekChange={setWeekStart}
              schedule={schedule}
              appointments={weeklyAppointments}
            />
          ) : (
            <section className="weekly-schedule-card">
              <div className="appointment-empty">
                {isDoctor
                  ? "로그인 사용자와 연결된 의료진 정보를 확인할 수 없습니다."
                  : "담당 의료진을 선택해 주세요."}
              </div>
            </section>
          )}
        </>
      )}

      {isDoctor && isNurse && activeTab ===
        "manage" && (
        <section className="appointment-schedule-card">

          <header>
            <div>
              <span>
                스케줄 관리
              </span>

              <h3>
                의료진 스케줄
                관리
              </h3>
            </div>

            {isDoctor ? (
              <div>
                <strong>
                  {clinicians.find(
                    (clinician) =>
                      clinician.id === clinicianId,
                  )?.name ?? currentUser.name}
                </strong>
              </div>
            ) : (
              <div>
                <select
                  value={clinicianId}
                  onChange={(event) =>
                    setClinicianId(event.target.value)
                  }
                >
                  <option value="">
                    담당 의료진 선택
                  </option>

                  {clinicianOptions.map(([id, name]) => (
                    <option value={id} key={id}>
                      {name}
                    </option>
                  ))}
                </select>

                <button
                  type="button"
                  disabled={!clinicianId}
                  onClick={() => void loadSchedule()}
                >
                  조회
                </button>
              </div>
            )}
          </header>


          {!clinicianId ? (
            <div className="appointment-empty">
              {isDoctor
                ? "로그인 사용자와 연결된 의료진 정보를 확인할 수 없습니다."
                : "담당 의료진을 선택해 주세요."}
            </div>
          ) : (
            <>
              {!isDoctor && (
                <div className="schedule-rule-editor">

                <label>
                  요일

                  <select
                    value={
                      draftRule.weekday
                    }
                    onChange={(
                      event,
                    ) =>
                      setDraftRule(
                        (
                          rule,
                        ) => ({
                          ...rule,
                          weekday:
                            Number(
                              event
                                .target
                                .value,
                            ),
                        }),
                      )
                    }
                  >
                    {WEEKDAYS.map(
                      (
                        day,
                        index,
                      ) => (
                        <option
                          key={
                            day
                          }
                          value={
                            index
                          }
                        >
                          {
                            day
                          }
                        </option>
                      ),
                    )}
                  </select>
                </label>


                <label>
                  시작

                  <input
                    type="time"
                    value={
                      draftRule.start_time
                    }
                    onChange={(
                      event,
                    ) =>
                      setDraftRule(
                        (
                          rule,
                        ) => ({
                          ...rule,
                          start_time:
                            event
                              .target
                              .value,
                        }),
                      )
                    }
                  />
                </label>


                <label>
                  종료

                  <input
                    type="time"
                    value={
                      draftRule.end_time
                    }
                    onChange={(
                      event,
                    ) =>
                      setDraftRule(
                        (
                          rule,
                        ) => ({
                          ...rule,
                          end_time:
                            event
                              .target
                              .value,
                        }),
                      )
                    }
                  />
                </label>


                <label>
                  간격

                  <input
                    type="number"
                    min="1"
                    value={
                      draftRule.slot_minutes
                    }
                    onChange={(
                      event,
                    ) =>
                      setDraftRule(
                        (
                          rule,
                        ) => ({
                          ...rule,
                          slot_minutes:
                            Number(
                              event
                                .target
                                .value,
                            ),
                        }),
                      )
                    }
                  />
                </label>


                <label>
                  적용 시작

                  <input
                    type="date"
                    value={
                      draftRule.effective_from
                    }
                    onChange={(
                      event,
                    ) =>
                      setDraftRule(
                        (
                          rule,
                        ) => ({
                          ...rule,
                          effective_from:
                            event
                              .target
                              .value,
                        }),
                      )
                    }
                  />
                </label>


                <button
                  type="button"
                  onClick={() =>
                    setSchedule(
                      (
                        rules,
                      ) => [
                        ...rules,
                        draftRule,
                      ],
                    )
                  }
                >
                  규칙 추가
                </button>
                </div>
              )}


              {schedule.length ===
              0 ? (
                <div className="appointment-empty is-compact">
                  등록된 스케줄
                  규칙이 없습니다.
                </div>
              ) : (
                <div className="schedule-rule-list">
                  {schedule.map(
                    (
                      rule,
                      index,
                    ) => (
                      <div
                        key={
                          rule.id ??
                          index
                        }
                      >
                        <strong>
                          {WEEKDAYS[
                            rule
                              .weekday
                          ] ??
                            rule.weekday}
                        </strong>

                        <span>
                          {
                            rule.start_time
                          }
                          –
                          {
                            rule.end_time
                          }
                        </span>

                        <span>
                          {
                            rule.slot_minutes
                          }
                          분
                        </span>

                        <span>
                          {
                            rule.effective_from
                          }
                          –
                          {rule.effective_to ??
                            "계속"}
                        </span>

                        {isDoctor ? (
                          <span>확정</span>
                        ) : (
                          <label>
                            <input
                              type="checkbox"
                              checked={rule.is_active}
                              onChange={(event) =>
                                setSchedule((previous) =>
                                  previous.map((item, itemIndex) =>
                                    itemIndex === index
                                      ? {
                                          ...item,
                                          is_active: event.target.checked,
                                        }
                                      : item,
                                  ),
                                )
                              }
                            />

                            활성
                          </label>
                        )}
                      </div>
                    ),
                  )}
                </div>
              )}
            </>
          )}


          {!isDoctor && (
            <footer>
              <button
                type="button"
                disabled={
                  !clinicianId ||
                  !mayManageSchedule ||
                  schedule.length === 0
                }
                onClick={() => void saveSchedule()}
              >
                스케줄 저장
              </button>
            </footer>
          )}


          {actionError && (
            <p className="appointment-action-error">
              {actionError}
            </p>
          )}
        </section>
      )}
      {rejectTarget && (
        <div
          className="appointment-modal-backdrop"
          role="presentation"
          onMouseDown={(event) => {
            if (
              event.target ===
              event.currentTarget
            ) {
              closeRejectModal();
            }
          }}
        >
          <section
            className="appointment-reject-modal"
            role="dialog"
            aria-modal="true"
            aria-labelledby="appointment-reject-modal-title"
          >
            <header>
              <div>
                <span>
                  예약 요청 처리
                </span>

                <h3
                  id="appointment-reject-modal-title"
                >
                  예약 거절
                </h3>
              </div>

              <button
                type="button"
                className="appointment-modal-close"
                aria-label="닫기"
                disabled={rejectSubmitting}
                onClick={closeRejectModal}
              >
                ×
              </button>
            </header>

            <div className="appointment-reject-modal-body">
              <div className="appointment-reject-patient">
                <div className="appointment-reject-avatar">
                  {(
                    rejectTarget.patient?.name ??
                    "환"
                  ).slice(0, 1)}
                </div>

                <div>
                  <strong>
                    {rejectTarget.patient?.name ??
                      rejectTarget.patient_id ??
                      "환자 정보 없음"}
                  </strong>

                  <span>
                    {rejectTarget.patient?.patient_no ??
                      ""}
                  </span>
                </div>

                <span className="appointment-status is-requested">
                  {statusLabel(
                    rejectTarget.status,
                  )}
                </span>
              </div>

              <div className="appointment-reject-context">
                <div>
                  <span>예약 일정</span>
                  <strong>
                    {formatDateTime(
                      appointmentStart(
                        rejectTarget,
                      ),
                    )}
                  </strong>
                </div>

                <div>
                  <span>진료과</span>
                  <strong>
                    {rejectTarget.department?.name ??
                      rejectTarget.department_id ??
                      "-"}
                  </strong>
                </div>

                <div>
                  <span>담당의</span>
                  <strong>
                    {rejectTarget.clinician?.name ??
                      rejectTarget.clinician_id ??
                      "-"}
                  </strong>
                </div>
              </div>

              <label className="appointment-reject-reason">
                <span>
                  거절 사유
                  <strong>*</strong>
                </span>

                <textarea
                  autoFocus
                  maxLength={255}
                  rows={5}
                  value={rejectReason}
                  placeholder="환자에게 안내할 예약 거절 사유를 입력해 주세요."
                  onChange={(event) => {
                    setRejectReason(
                      event.target.value,
                    );

                    if (rejectError) {
                      setRejectError(null);
                    }
                  }}
                />

                <small>
                  {rejectReason.length}/255
                </small>
              </label>

              {rejectError && (
                <p className="appointment-reject-error">
                  {rejectError}
                </p>
              )}
            </div>

            <footer>
              <button
                type="button"
                className="is-secondary"
                disabled={rejectSubmitting}
                onClick={closeRejectModal}
              >
                취소
              </button>

              <button
                type="button"
                className="is-danger"
                disabled={
                  rejectSubmitting ||
                  !rejectReason.trim()
                }
                onClick={() =>
                  void submitReject()
                }
              >
                {rejectSubmitting
                  ? "처리 중..."
                  : "예약 거절"}
              </button>
            </footer>
          </section>
        </div>
      )}

      {correctionTarget && (
        <div
          className="appointment-modal-backdrop"
          role="presentation"
          onMouseDown={(event) => {
            if (
              event.target ===
              event.currentTarget
            ) {
              closeCorrectionModal();
            }
          }}
        >
          <section
            className="appointment-reject-modal"
            role="dialog"
            aria-modal="true"
            aria-labelledby="appointment-correction-modal-title"
          >
            <header>
              <div>
                <span>
                  예약 상태 관리
                </span>

                <h3
                  id="appointment-correction-modal-title"
                >
                  예약 상태 정정
                </h3>
              </div>

              <button
                type="button"
                className="appointment-modal-close"
                aria-label="닫기"
                disabled={correctionSubmitting}
                onClick={closeCorrectionModal}
              >
                ×
              </button>
            </header>

            <div className="appointment-reject-modal-body">
              <div className="appointment-reject-patient">
                <div className="appointment-reject-avatar">
                  {(
                    correctionTarget.patient?.name ??
                    "환"
                  ).slice(0, 1)}
                </div>

                <div>
                  <strong>
                    {correctionTarget.patient?.name ??
                      correctionTarget.patient_id ??
                      "환자 정보 없음"}
                  </strong>

                  <span>
                    {correctionTarget.patient?.patient_no ??
                      ""}
                  </span>
                </div>

                <span
                  className={`appointment-status is-${correctionTarget.status.toLowerCase()}`}
                >
                  {statusLabel(
                    correctionTarget.status,
                  )}
                </span>
              </div>

              <div className="appointment-reject-context">
                <div>
                  <span>예약 일정</span>
                  <strong>
                    {formatDateTime(
                      appointmentStart(
                        correctionTarget,
                      ),
                    )}
                  </strong>
                </div>

                <div>
                  <span>현재 상태</span>
                  <strong>
                    {statusLabel(
                      correctionTarget.status,
                    )}
                  </strong>
                </div>

                <div>
                  <span>정정 후 상태</span>
                  <strong>
                    {statusLabel(
                      correctionTargetStatus(
                        correctionTarget,
                      ) ?? undefined,
                    )}
                  </strong>
                </div>
              </div>

              <label className="appointment-reject-reason">
                <span>
                  정정 사유
                  <strong>*</strong>
                </span>

                <textarea
                  autoFocus
                  maxLength={255}
                  rows={5}
                  value={correctionReason}
                  placeholder="잘못 처리된 예약 상태를 정정하는 사유를 입력해 주세요."
                  onChange={(event) => {
                    setCorrectionReason(
                      event.target.value,
                    );

                    if (correctionError) {
                      setCorrectionError(null);
                    }
                  }}
                />

                <small>
                  {correctionReason.length}/255
                </small>
              </label>

              {correctionError && (
                <p className="appointment-reject-error">
                  {correctionError}
                </p>
              )}
            </div>

            <footer>
              <button
                type="button"
                className="is-secondary"
                disabled={correctionSubmitting}
                onClick={closeCorrectionModal}
              >
                취소
              </button>

              <button
                type="button"
                className="is-primary"
                disabled={
                  correctionSubmitting ||
                  !correctionReason.trim()
                }
                onClick={() =>
                  void submitCorrection()
                }
              >
                {correctionSubmitting
                  ? "정정 중..."
                  : "상태 정정"}
              </button>
            </footer>
          </section>
        </div>
      )}

    </section>
  );
}
