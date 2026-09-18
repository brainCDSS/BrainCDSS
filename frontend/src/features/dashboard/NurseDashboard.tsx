import {
  useEffect,
  useMemo,
  useState,
} from "react";

import type {
  LoginUser,
} from "../auth/types";

import {
  getPatients,
} from "../patients/api";
import { getPatientEncounters } from "../medication-safety/api";

import type {
  Patient,
} from "../patients/types";

import type {
  AssessmentWorklistItem,
} from "../assessments/types";

import type {
  StaffAppointment,
} from "../appointments/types";

import {
  getNurseAssessmentWorklist,
  getNurseDashboardAppointments,
} from "./nurseDashboardApi";

import "./dashboard.css";
import "./nurse-dashboard.css";


interface NurseDashboardProps {
  currentUser: LoginUser;

  onOpenPatient: (
    patient: Patient,
  ) => void;

  onOpenMenu?: (
    menu: "triage" | "appointments",
  ) => void;
}


type AssessmentFilter =
  | "ALL"
  | "PENDING"
  | "IN_PROGRESS"
  | "COMPLETED";


const PATIENT_PAGE_SIZE = 6;


function toDateKey(
  date: Date,
) {
  const year =
    date.getFullYear();

  const month =
    String(
      date.getMonth() + 1,
    ).padStart(2, "0");

  const day =
    String(
      date.getDate(),
    ).padStart(2, "0");

  return `${year}-${month}-${day}`;
}


function formatSex(
  sex: string | null | undefined,
) {
  if (
    sex === "M" ||
    sex === "MALE"
  ) {
    return "남";
  }

  if (
    sex === "F" ||
    sex === "FEMALE"
  ) {
    return "여";
  }

  return "-";
}


function getAge(
  patient: Patient,
) {
  if (
    patient.estimated_age !== null
  ) {
    return patient.estimated_age;
  }

  if (!patient.birth_date) {
    return null;
  }

  const birth =
    new Date(
      patient.birth_date,
    );

  if (
    Number.isNaN(
      birth.getTime(),
    )
  ) {
    return null;
  }

  const today =
    new Date();

  let age =
    today.getFullYear() -
    birth.getFullYear();

  const beforeBirthday =
    today.getMonth() <
      birth.getMonth() ||
    (
      today.getMonth() ===
        birth.getMonth() &&
      today.getDate() <
        birth.getDate()
    );

  if (beforeBirthday) {
    age -= 1;
  }

  return age;
}


function getSummaryString(
  summary:
    Record<string, unknown>,
  keys: string[],
) {
  for (
    const key of keys
  ) {
    const value =
      summary[key];

    if (
      typeof value === "string" &&
      value.trim()
    ) {
      return value;
    }
  }

  return "";
}


function getSummaryNumber(
  summary:
    Record<string, unknown>,
  keys: string[],
) {
  for (
    const key of keys
  ) {
    const value =
      summary[key];

    if (
      typeof value === "number"
    ) {
      return value;
    }
  }

  return null;
}


function getAssessmentState(
  item:
    AssessmentWorklistItem,
): Exclude<
  AssessmentFilter,
  "ALL"
> {
  if (
    !item.assessment_id
  ) {
    return "PENDING";
  }

  const status =
    item.status
      ?.toUpperCase();

  if (
    status === "COMPLETED" ||
    status === "FINAL"
  ) {
    return "COMPLETED";
  }

  if (
    status === "DRAFT" ||
    status === "IN_PROGRESS"
  ) {
    return "IN_PROGRESS";
  }

  return "PENDING";
}


function getAssessmentLabel(
  item:
    AssessmentWorklistItem,
) {
  const state =
    getAssessmentState(item);

  if (
    state === "COMPLETED"
  ) {
    return "초기평가 완료";
  }

  if (
    state === "IN_PROGRESS"
  ) {
    return "초기평가 진행중";
  }

  return "초기평가 대기";
}


function getPriorityLabel(
  priority:
    string | null,
) {
  if (!priority) {
    return "-";
  }

  switch (
    priority.toUpperCase()
  ) {
    case "EMERGENCY":
      return "응급";

    case "URGENT":
      return "긴급";

    case "NON_EMERGENCY":
      return "비응급";

    default:
      return priority;
  }
}


function getEncounterTypeLabel(
  encounterType: string | null | undefined,
) {
  if (encounterType === "EMERGENCY") {
    return "응급실";
  }

  if (encounterType === "OUTPATIENT") {
    return "외래";
  }

  return encounterType ?? "-";
}


function formatTime(
  value:
    string | null | undefined,
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

  return date.toLocaleTimeString(
    "ko-KR",
    {
      hour: "2-digit",
      minute: "2-digit",
      hour12: false,
    },
  );
}


function normalizeAppointments(
  response: {
    appointments?:
      StaffAppointment[];

    results?:
      Array<
        StaffAppointment & {
          id?: string;
        }
      >;
  },
) {
  return (
    response.results ??
    response.appointments ??
    []
  );
}


function getAppointmentTime(
  appointment:
    StaffAppointment,
) {
  return formatTime(
    appointment.slot
      ?.start_at ??
      appointment.start_at,
  );
}


function getAppointmentStatus(
  status: string,
) {
  switch (
    status.toUpperCase()
  ) {
    case "REQUESTED":
      return "승인 대기";

    case "CONFIRMED":
      return "예약 확정";

    case "IN_PROGRESS":
      return "진료중";

    case "COMPLETED":
      return "완료";

    case "CANCELLED":
      return "취소";

    case "REJECTED":
      return "거절";

    default:
      return status;
  }
}


function createCalendarDays(
  selectedDate: Date,
) {
  const year =
    selectedDate.getFullYear();

  const month =
    selectedDate.getMonth();

  const firstDay =
    new Date(
      year,
      month,
      1,
    );

  const lastDay =
    new Date(
      year,
      month + 1,
      0,
    );

  const startOffset =
    firstDay.getDay();

  const days:
    Array<{
      date: Date;
      currentMonth: boolean;
    }> = [];

  for (
    let index =
      startOffset - 1;
    index >= 0;
    index -= 1
  ) {
    days.push({
      date: new Date(
        year,
        month,
        -index,
      ),
      currentMonth: false,
    });
  }

  for (
    let day = 1;
    day <=
    lastDay.getDate();
    day += 1
  ) {
    days.push({
      date: new Date(
        year,
        month,
        day,
      ),
      currentMonth: true,
    });
  }

  let nextDay = 1;

  while (
    days.length % 7 !== 0 ||
    days.length < 42
  ) {
    days.push({
      date: new Date(
        year,
        month + 1,
        nextDay,
      ),
      currentMonth: false,
    });

    nextDay += 1;
  }

  return days;
}


export default function NurseDashboard({
  currentUser,
  onOpenPatient,
  onOpenMenu,
}: NurseDashboardProps) {
  const [
    patients,
    setPatients,
  ] = useState<Patient[]>([]);

  const [
    assessments,
    setAssessments,
  ] = useState<
    AssessmentWorklistItem[]
  >([]);

  const [
    appointments,
    setAppointments,
  ] = useState<
    StaffAppointment[]
  >([]);

  const [
    selectedPatient,
    setSelectedPatient,
  ] = useState<
    Patient | null
  >(null);

  const [
    selectedDate,
    setSelectedDate,
  ] = useState(
    () => new Date(),
  );

  const [
    search,
    setSearch,
  ] = useState("");

  const [
    patientPage,
    setPatientPage,
  ] = useState(1);

  const [
    assessmentFilter,
    setAssessmentFilter,
  ] =
    useState<AssessmentFilter>(
      "ALL",
    );

  const [
    error,
    setError,
  ] =
    useState<string | null>(
      null,
    );
  const [encounterBadges, setEncounterBadges] = useState<Record<string, { label: string; tone: string }>>({});

  useEffect(() => {
    let active = true;
    if (!patients.length) { setEncounterBadges({}); return () => { active = false; }; }
    void Promise.allSettled(patients.map(async (patient) => ({ patientId: patient.id, encounters: await getPatientEncounters(patient.id) }))).then((results) => {
      if (!active) return;
      const next: Record<string, { label: string; tone: string }> = {};
      results.forEach((result) => {
        if (result.status !== "fulfilled") return;
        const latest = [...result.value.encounters].sort((a, b) => (b.arrived_at ?? "").localeCompare(a.arrived_at ?? ""))[0];
        if (!latest) return;
        if (latest.ended_at) next[result.value.patientId] = { label: "완료", tone: "completed" };
        else if (latest.status === "IN_PROGRESS") next[result.value.patientId] = { label: "진료중", tone: "in-progress" };
        else if (latest.status === "REGISTERED") next[result.value.patientId] = { label: "진료대기", tone: "registered" };
      });
      setEncounterBadges(next);
    });
    return () => { active = false; };
  }, [patients]);


  useEffect(() => {
    let active = true;

    getPatients()
      .then((response) => {
        if (!active) {
          return;
        }

        setPatients(
          response.results,
        );

        setSelectedPatient(
          (current) =>
            current ??
            response.results[0] ??
            null,
        );
      })
      .catch(() => {
        if (active) {
          setError(
            "환자 목록을 불러오지 못했습니다.",
          );
        }
      });

    return () => {
      active = false;
    };
  }, []);


  useEffect(() => {
    let active = true;

    const date =
      toDateKey(
        selectedDate,
      );

    setError(null);

    Promise.allSettled([
      getNurseAssessmentWorklist(
        date,
      ),
      getNurseAssessmentWorklist(
        date,
        "COMPLETED",
      ),
      getNurseDashboardAppointments(
        date,
      ),
    ]).then(
      ([
        assessmentResult,
        completedAssessmentResult,
        appointmentResult,
      ]) => {
        if (!active) {
          return;
        }

        const activeAssessments =
          assessmentResult.status === "fulfilled"
            ? assessmentResult.value.results
            : [];

        const completedAssessments =
          completedAssessmentResult.status === "fulfilled"
            ? completedAssessmentResult.value.results
            : [];

        setAssessments([
          ...activeAssessments,
          ...completedAssessments,
        ]);

        if (
          appointmentResult.status ===
          "fulfilled"
        ) {
          setAppointments(
            normalizeAppointments(
              appointmentResult.value,
            ),
          );
        } else {
          setAppointments([]);
        }

        if (
          assessmentResult.status ===
            "rejected" ||
          completedAssessmentResult.status ===
            "rejected" ||
          appointmentResult.status ===
            "rejected"
        ) {
          setError(
            "일부 대시보드 데이터를 불러오지 못했습니다.",
          );
        }
      },
    );

    return () => {
      active = false;
    };
  }, [selectedDate]);


  useEffect(() => {
    setPatientPage(1);
  }, [search]);


  const filteredPatients =
    useMemo(() => {
      const keyword =
        search
          .trim()
          .toLowerCase();

      if (!keyword) {
        return patients;
      }

      return patients.filter(
        (patient) =>
          patient.name
            .toLowerCase()
            .includes(keyword) ||
          patient.patient_no
            .toLowerCase()
            .includes(keyword),
      );
    }, [
      patients,
      search,
    ]);


  const pageCount =
    Math.max(
      1,
      Math.ceil(
        filteredPatients.length /
          PATIENT_PAGE_SIZE,
      ),
    );

  const currentPage =
    Math.min(
      patientPage,
      pageCount,
    );

  const visiblePatients =
    filteredPatients.slice(
      (
        currentPage - 1
      ) *
        PATIENT_PAGE_SIZE,
      currentPage *
        PATIENT_PAGE_SIZE,
    );


  const filteredAssessments =
    useMemo(() => {
      if (
        assessmentFilter ===
        "ALL"
      ) {
        return assessments;
      }

      return assessments.filter(
        (item) =>
          getAssessmentState(
            item,
          ) ===
          assessmentFilter,
      );
    }, [
      assessments,
      assessmentFilter,
    ]);


  const pendingCount =
    assessments.filter(
      (item) =>
        getAssessmentState(
          item,
        ) === "PENDING",
    ).length;

  const progressCount =
    assessments.filter(
      (item) =>
        getAssessmentState(
          item,
        ) === "IN_PROGRESS",
    ).length;

  const completeCount =
    assessments.filter(
      (item) =>
        getAssessmentState(
          item,
        ) === "COMPLETED",
    ).length;


  const calendarDays =
    useMemo(
      () =>
        createCalendarDays(
          selectedDate,
        ),
      [selectedDate],
    );


  const selectedDateKey =
    toDateKey(
      selectedDate,
    );


  const todayKey =
    toDateKey(
      new Date(),
    );


  function changeDay(
    amount: number,
  ) {
    setSelectedDate(
      (previous) => {
        const next =
          new Date(previous);

        next.setDate(
          next.getDate() +
            amount,
        );

        return next;
      },
    );
  }


  function changeMonth(
    amount: number,
  ) {
    setSelectedDate(
      (previous) => {
        const next =
          new Date(previous);

        next.setMonth(
          next.getMonth() +
            amount,
        );

        return next;
      },
    );
  }


  function openPatient(
    patient: Patient,
  ) {
    setSelectedPatient(
      patient,
    );

    onOpenPatient(
      patient,
    );
  }


  return (
    <section className="nurse-dashboard">
      
      
      <aside className="dash-patient-panel">
  <header className="dash-patient-panel__header">
    <h2>
      환자 목록 <span>({patients.length})</span>
    </h2>

    <span className="dash-patient-all-button is-active">
      전체
    </span>
  </header>

  <label className="dash-patient-search">
    <span aria-hidden="true">⌕</span>

    <input
      value={search}
      onChange={(event) =>
        setSearch(event.target.value)
      }
      placeholder="이름, 등록번호, 진료과로 검색"
    />
  </label>

  <div className="dash-patient-scroll">
    {visiblePatients.map((patient) => {
      const age = getAge(patient);

      return (
        <button
          key={patient.id}
          type="button"
          className={
            selectedPatient?.id === patient.id
              ? "dash-patient is-selected"
              : "dash-patient"
          }
          onClick={() =>
            openPatient(patient)
          }
        >
          <span className="dash-patient__top">
            <span
              className="dash-patient__avatar"
              aria-hidden="true"
            >
              ♙
            </span>

            <strong>{patient.name}</strong>

            {encounterBadges[patient.id] && <em className={`patient-mini-status is-${encounterBadges[patient.id].tone}`}>{encounterBadges[patient.id].label}</em>}
          </span>

          <small>
            {formatSex(patient.sex)}
            {" · "}
            {age === null
              ? "-"
              : `${age}세`}
            <i />
            {patient.birth_date ?? "-"}
          </small>

          <small>
            환자번호 {patient.patient_no}
          </small>
        </button>
      );
    })}

    {visiblePatients.length === 0 && (
      <div className="dash-empty">
        조회된 환자가 없습니다.
      </div>
    )}
  </div>

  <nav
    className="dash-patient-pagination"
    aria-label="환자 목록 페이지"
  >
    <button
      type="button"
      onClick={() =>
        setPatientPage((previous) =>
          Math.max(
            1,
            previous - 1,
          )
        )
      }
      disabled={currentPage === 1}
      aria-label="이전 페이지"
    >
      ‹
    </button>

    <span>
      <strong>{currentPage}</strong> / {pageCount}
    </span>

    <button
      type="button"
      onClick={() =>
        setPatientPage((previous) =>
          Math.min(
            pageCount,
            previous + 1,
          )
        )
      }
      disabled={currentPage === pageCount}
      aria-label="다음 페이지"
    >
      ›
    </button>
  </nav>
</aside>


      <main className="nurse-dashboard-main">
        <header className="nurse-dashboard-heading">
        <div>
            <span>DASHBOARD</span>

            <h1>
            좋은 하루입니다, {currentUser.name}님
            <i> 👋</i>
            </h1>

            <p>
            오늘도 환자들의 더 나은 내일을 위해, 함께 만들어가는 진료를 응원합니다.
            </p>
        </div>

          <div className="nurse-dashboard-date">
            <strong>
              {selectedDate.toLocaleDateString(
                "ko-KR",
                {
                  year:
                    "numeric",
                  month:
                    "long",
                  day: "numeric",
                  weekday:
                    "short",
                },
              )}
            </strong>

            <button
              type="button"
              onClick={() =>
                setSelectedDate(
                  new Date(),
                )
              }
            >
              오늘
            </button>

            <button
              type="button"
              onClick={() =>
                changeDay(-1)
              }
            >
              ‹
            </button>

            <button
              type="button"
              onClick={() =>
                changeDay(1)
              }
            >
              ›
            </button>
          </div>
        </header>


        {error && (
          <div className="nurse-dashboard-warning">
            {error}
          </div>
        )}


        <section className="nurse-kpis">
          <article className="nurse-kpi">
            <span className="nurse-kpi-icon">
              ♙
            </span>

            <div>
              <span>
                오늘 내원 환자
              </span>

              <strong>
                {
                  assessments.length
                }
                명
              </strong>

              <small>
                초기평가 대상
                기준
              </small>
            </div>
          </article>


          <article className="nurse-kpi">
            <span className="nurse-kpi-icon is-assessment">
              ▣
            </span>

            <div>
              <span>
                초기평가 현황
              </span>

              <strong>
                {
                  assessments.length
                }
                건
              </strong>

              <small>
                대기{" "}
                {pendingCount}
                {" · "}
                진행{" "}
                {progressCount}
                {" · "}
                완료{" "}
                {completeCount}
              </small>
            </div>
          </article>


          <article className="nurse-kpi">
            <span className="nurse-kpi-icon is-calendar">
              □
            </span>

            <div>
              <span>
                오늘 예약
              </span>

              <strong>
                {
                  appointments.length
                }
                건
              </strong>

              <small>
                선택 날짜 예약
                현황
              </small>
            </div>
          </article>
        </section>


        <section className="nurse-dashboard-content">
          <article className="nurse-today-card">
            <header>
              <div>
                <h2>
                  오늘 내원 환자
                </h2>

                <p>
                  접수 이후
                  초기평가 진행
                  현황입니다.
                </p>
              </div>

              {onOpenMenu && (
                <button
                  type="button"
                  onClick={() =>
                    onOpenMenu(
                      "triage",
                    )
                  }
                >
                  접수·내원관리 전체보기 ›
                </button>
              )}
            </header>


            <div className="nurse-assessment-tabs">
              <button
                type="button"
                className={
                  assessmentFilter ===
                  "ALL"
                    ? "is-active"
                    : ""
                }
                onClick={() =>
                  setAssessmentFilter(
                    "ALL",
                  )
                }
              >
                전체 (
                {
                  assessments.length
                }
                )
              </button>

              <button
                type="button"
                className={
                  assessmentFilter ===
                  "PENDING"
                    ? "is-active"
                    : ""
                }
                onClick={() =>
                  setAssessmentFilter(
                    "PENDING",
                  )
                }
              >
                접수 대기 (
                {pendingCount})
              </button>

              <button
                type="button"
                className={
                  assessmentFilter ===
                  "IN_PROGRESS"
                    ? "is-active"
                    : ""
                }
                onClick={() =>
                  setAssessmentFilter(
                    "IN_PROGRESS",
                  )
                }
              >
                평가중 (
                {progressCount})
              </button>

              <button
                type="button"
                className={
                  assessmentFilter ===
                  "COMPLETED"
                    ? "is-active"
                    : ""
                }
                onClick={() =>
                  setAssessmentFilter(
                    "COMPLETED",
                  )
                }
              >
                완료 (
                {completeCount})
              </button>
            </div>


            <div className="nurse-table-wrap">
              <table>
                <thead>
                  <tr>
                    <th>시간</th>
                    <th>환자</th>
                    <th>내원유형</th>
                    <th>
                      현재 단계
                    </th>
                    <th>
                      응급도
                    </th>
                    <th>환자번호</th>
                  </tr>
                </thead>

                <tbody>
                  {filteredAssessments.map(
                    (item) => {
                      const summary =
                        item.patient_summary ??
                        {};

                      const name =
                        getSummaryString(
                          summary,
                          [
                            "name",
                            "patient_name",
                          ],
                        ) ||
                        "환자 정보 없음";

                      const patientNo =
                        getSummaryString(
                          summary,
                          [
                            "patient_no",
                            "patient_number",
                          ],
                        ) ||
                        "-";

                      const age =
                        getSummaryNumber(
                          summary,
                          [
                            "age",
                            "estimated_age",
                          ],
                        );

                      const sex =
                        getSummaryString(
                          summary,
                          [
                            "sex",
                          ],
                        );

                      return (
                        <tr
                          key={
                            item.encounter_id
                          }
                        >
                          <td>
                            {formatTime(
                              item.created_at,
                            )}
                          </td>

                          <td>
                            <strong>
                              {name}
                            </strong>

                            <small>
                              {age !==
                              null
                                ? `${age}세`
                                : "-"}
                              {" / "}
                              {formatSex(
                                sex,
                              )}
                            </small>
                          </td>

                          <td>
                            {getEncounterTypeLabel(
                              item.encounter_type,
                            )}
                          </td>

                          <td>
                            <span
                              className={`nurse-stage is-${getAssessmentState(
                                item,
                              ).toLowerCase()}`}
                            >
                              {getAssessmentLabel(
                                item,
                              )}
                            </span>
                          </td>

                          <td>
                            <span
                              className={`nurse-priority is-${(
                                item.triage_priority ??
                                "none"
                              ).toLowerCase()}`}
                            >
                              {getPriorityLabel(
                                item.triage_priority,
                              )}
                            </span>
                          </td>

                          <td>
                            {
                              patientNo
                            }
                          </td>
                        </tr>
                      );
                    },
                  )}
                </tbody>
              </table>

              {filteredAssessments.length ===
                0 && (
                <div className="nurse-empty nurse-table-empty">
                  해당 날짜에
                  조회된 초기평가
                  환자가 없습니다.
                </div>
              )}
            </div>
          </article>


          <article className="nurse-schedule-card">
            <header>
              <h2>
                예약 · 일정
              </h2>

              {onOpenMenu && (
                <button
                  type="button"
                  onClick={() =>
                    onOpenMenu(
                      "appointments",
                    )
                  }
                >
                  전체 일정 보기 ›
                </button>
              )}
            </header>


            <div className="nurse-calendar-header">
              <button
                type="button"
                onClick={() =>
                  changeMonth(
                    -1,
                  )
                }
              >
                ‹
              </button>

              <strong>
                {selectedDate.getFullYear()}
                년{" "}
                {selectedDate.getMonth() +
                  1}
                월
              </strong>

              <button
                type="button"
                onClick={() =>
                  changeMonth(
                    1,
                  )
                }
              >
                ›
              </button>

              <button
                type="button"
                className="nurse-calendar-today"
                onClick={() =>
                  setSelectedDate(
                    new Date(),
                  )
                }
              >
                오늘
              </button>
            </div>


            <div className="nurse-calendar-week">
              <span>일</span>
              <span>월</span>
              <span>화</span>
              <span>수</span>
              <span>목</span>
              <span>금</span>
              <span>토</span>
            </div>


            <div className="nurse-calendar-grid">
              {calendarDays.map(
                ({
                  date,
                  currentMonth,
                }) => {
                  const key =
                    toDateKey(
                      date,
                    );

                  const selected =
                    key ===
                    selectedDateKey;

                  const today =
                    key ===
                    todayKey;

                  return (
                    <button
                      key={key}
                      type="button"
                      className={[
                        !currentMonth
                          ? "is-muted"
                          : "",
                        selected
                          ? "is-selected"
                          : "",
                        today
                          ? "is-today"
                          : "",
                      ]
                        .filter(
                          Boolean,
                        )
                        .join(
                          " ",
                        )}
                      onClick={() =>
                        setSelectedDate(
                          date,
                        )
                      }
                    >
                      {
                        date.getDate()
                      }
                    </button>
                  );
                },
              )}
            </div>


            <div className="nurse-appointment-heading">
              <h3>
                {selectedDateKey ===
                todayKey
                  ? "오늘 예약"
                  : `${selectedDate.getMonth() + 1}월 ${selectedDate.getDate()}일 예약`}
                {" "}
                (
                {
                  appointments.length
                }
                )
              </h3>
            </div>


            <div className="nurse-appointment-list">
              {appointments
                .slice(
                  0,
                  6,
                )
                .map(
                  (
                    appointment,
                  ) => (
                    <div
                      className="nurse-appointment-row"
                      key={
                        appointment.appointment_id
                      }
                    >
                      <strong>
                        {getAppointmentTime(
                          appointment,
                        )}
                      </strong>

                      <div>
                        <b>
                          {appointment.patient
                            ?.name ??
                            "-"}
                        </b>

                        <small>
                          {appointment.department
                            ?.name ??
                            "진료과 미연결"}
                        </small>
                      </div>

                      <span>
                        {getAppointmentStatus(
                          appointment.status,
                        )}
                      </span>
                    </div>
                  ),
                )}

              {appointments.length ===
                0 && (
                <div className="nurse-empty">
                  선택한 날짜의
                  예약이 없습니다.
                </div>
              )}
            </div>
          </article>
        </section>
      </main>
    </section>
  );
}
