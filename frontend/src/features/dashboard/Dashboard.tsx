import { useEffect, useMemo, useState } from "react";
import type { CSSProperties } from "react";

import type { AssessmentWorklistItem } from "../assessments/types";
import { getAIAnalyses } from "../ai-analysis/api";
import type { AIAnalysisItem } from "../ai-analysis/types";
import type { LoginUser } from "../auth/types";
import { getConsultations } from "../consultations/api";
import type { ConsultationListItem } from "../consultations/types";
import { getImagingStudies } from "../imaging/api";
import type { ImagingStudy } from "../imaging/types";
import { getPatientEncounters } from "../medication-safety/api";
import type { EncounterListItem } from "../medication-safety/types";
import { getPatients } from "../patients/api";
import type { Patient } from "../patients/types";

import "./dashboard.css";

interface DashboardProps {
  currentUser: LoginUser;
  onOpenPatient: (patient: Patient) => void;
  onOpenMenu?: (menu: "imaging" | "ai-results") => void;
}

interface DashboardData {
  patients: Patient[];
  studies: ImagingStudy[];
  analyses: AIAnalysisItem[];
  consultations: ConsultationListItem[];
  assessments: AssessmentWorklistItem[];
  encounters: EncounterListItem[];
}

const EMPTY_DATA: DashboardData = {
  patients: [],
  studies: [],
  analyses: [],
  consultations: [],
  assessments: [],
  encounters: [],
};

const PATIENT_PAGE_SIZE = 6;

const MODEL_GROUPS = [
  {
    key: "ISCHEMIA",
    label: "허혈성 뇌졸중",
    color: "#3785ee",
  },
  {
    key: "HEMORRHAGE",
    label: "출혈성 뇌졸중",
    color: "#8c6ce9",
  },
  {
    key: "ANEURYSM",
    label: "뇌동맥류",
    color: "#42c4a2",
  },
];

function formatSex(sex: string | null) {
  if (sex === "M" || sex === "MALE") return "남";
  if (sex === "F" || sex === "FEMALE") return "여";
  return sex ?? "-";
}

function getAge(patient: Patient) {
  if (patient.estimated_age !== null) {
    return patient.estimated_age;
  }

  if (!patient.birth_date) {
    return null;
  }

  const birth = new Date(patient.birth_date);

  if (Number.isNaN(birth.getTime())) {
    return null;
  }

  const today = new Date();

  let age =
    today.getFullYear() -
    birth.getFullYear();

  if (
    today.getMonth() < birth.getMonth() ||
    (
      today.getMonth() === birth.getMonth() &&
      today.getDate() < birth.getDate()
    )
  ) {
    age -= 1;
  }

  return age;
}

function isToday(
  value: string | null | undefined,
  selectedDate: Date,
) {
  if (!value) {
    return false;
  }

  const date = new Date(value);

  return (
    !Number.isNaN(date.getTime()) &&
    date.toDateString() ===
      selectedDate.toDateString()
  );
}

function includesModel(
  analysis: AIAnalysisItem,
  key: string,
) {
  const type = [
    analysis.analysis_type,
    analysis.model?.code,
  ]
    .filter(
      (value): value is string =>
        typeof value === "string",
    )
    .join(" ")
    .toUpperCase();

  if (key === "ISCHEMIA") {
    return type.includes("ISCHEM");
  }

  if (key === "HEMORRHAGE") {
    return type.includes("HEMORRH");
  }

  return type.includes(key);
}

function DashboardPatientList({
  patients,
  studies,
  analyses,
  selected,
  search,
  onSearch,
  onSelect,
  encounters,
}: {
  patients: Patient[];
  studies: ImagingStudy[];
  analyses: AIAnalysisItem[];
  selected: Patient | null;
  search: string;
  onSearch: (value: string) => void;
  onSelect: (patient: Patient) => void;
  encounters: EncounterListItem[];
}) {
  const [page, setPage] =
    useState(1);

  const filtered =
    patients.filter((patient) => {
      const keyword =
        search.trim().toLowerCase();

      return (
        !keyword ||
        patient.name
          .toLowerCase()
          .includes(keyword) ||
        patient.patient_no
          .toLowerCase()
          .includes(keyword)
      );
    });

  const pageCount =
    Math.max(
      1,
      Math.ceil(
        filtered.length /
          PATIENT_PAGE_SIZE,
      ),
    );

  const currentPage =
    Math.min(page, pageCount);

  const pagePatients =
    filtered.slice(
      (
        currentPage - 1
      ) *
        PATIENT_PAGE_SIZE,
      currentPage *
        PATIENT_PAGE_SIZE,
    );

  useEffect(() => {
    setPage(1);
  }, [search]);

  return (
    <aside className="dash-patient-panel">
      <header className="dash-patient-panel__header">
        <h2>
          환자 목록{" "}
          <span>
            ({patients.length})
          </span>
        </h2>

        <button
          type="button"
          className="dash-patient-all-button"
        >
          전체
        </button>
      </header>

      <label className="dash-patient-search">
        <span aria-hidden="true">
          ⌕
        </span>

        <input
          value={search}
          onChange={(event) =>
            onSearch(
              event.target.value,
            )
          }
          placeholder="이름, 등록번호, 진료과로 검색"
        />
      </label>

      <div className="dash-patient-scroll">
        {pagePatients.map(
          (patient) => {
            const encounter = encounters.find((item) => item.patient_id === patient.id);
            const patientStudies =
              studies.filter(
                (study) =>
                  study.patient_id ===
                  patient.id,
              );

            const studyIds =
              new Set(
                patientStudies.map(
                  (study) =>
                    study.id,
                ),
              );

            const patientAnalyses =
              analyses.filter(
                (analysis) =>
                  studyIds.has(
                    analysis.study_id,
                  ),
              );

            const age =
              getAge(patient);

            return (
              <button
                key={patient.id}
                type="button"
                className={
                  selected?.id ===
                  patient.id
                    ? "dash-patient is-selected"
                    : "dash-patient"
                }
                onClick={() =>
                  onSelect(patient)
                }
              >
                <span className="dash-patient__top">
                  <span
                    className="dash-patient__avatar"
                    aria-hidden="true"
                  >
                    ♙
                  </span>

                  <strong>
                    {patient.name}
                  </strong>

                  {encounter && (
                    <em
                      className={
                        encounter.status === "IN_PROGRESS"
                          ? "is-in-progress"
                          : encounter.status === "REGISTERED"
                            ? "is-registered"
                            : "is-default"
                      }
                    >
                      {encounter.status === "IN_PROGRESS"
                        ? "진료중"
                        : encounter.status === "REGISTERED"
                          ? "접수"
                          : encounter.status}
                    </em>
                  )}
                </span>

                <small>
                  {formatSex(
                    patient.sex,
                  )}
                  {" · "}
                  {age === null
                    ? "-"
                    : `${age}세`}
                  <i />
                  {patient.birth_date ??
                    "-"}
                </small>

                <small>{encounter ? `${encounter.encounter_type} · ${encounter.status}` : "현재 Encounter 없음"}</small>

                <span className="dash-patient__tags">
                  <i>
                    {patientStudies.length >
                    0
                      ? `${patientStudies[0].modality} ${patientStudies[0].status}`
                      : "영상 없음"}
                  </i>

                  <i
                    className={
                      patientAnalyses.some(
                        (item) =>
                          item.status ===
                          "COMPLETED",
                      )
                        ? "is-done"
                        : ""
                    }
                  >
                    {patientAnalyses.length >
                    0
                      ? `AI ${patientAnalyses[0].status}`
                      : "AI 분석 없음"}
                  </i>
                </span>
              </button>
            );
          },
        )}

        {filtered.length ===
          0 && (
          <div className="dash-empty">
            조회된 환자가
            없습니다.
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
            setPage(
              (value) =>
                Math.max(
                  1,
                  value - 1,
                ),
            )
          }
          disabled={
            currentPage === 1
          }
          aria-label="이전 페이지"
        >
          ‹
        </button>

        <span>
          <strong>
            {currentPage}
          </strong>{" "}
          / {pageCount}
        </span>

        <button
          type="button"
          onClick={() =>
            setPage(
              (value) =>
                Math.min(
                  pageCount,
                  value + 1,
                ),
            )
          }
          disabled={
            currentPage ===
            pageCount
          }
          aria-label="다음 페이지"
        >
          ›
        </button>
      </nav>
    </aside>
  );
}

function KpiCard({
  icon,
  label,
  value,
  summary,
  tone,
}: {
  icon: string;
  label: string;
  value: string;
  summary: string;
  tone: string;
}) {
  return (
    <article className="dash-kpi">
      <span
        className={`dash-kpi__icon is-${tone}`}
      >
        {icon}
      </span>

      <div>
        <span>{label}</span>
        <strong>{value}</strong>
        <small>{summary}</small>
      </div>
    </article>
  );
}

function RiskPanel() {
  return (
    <article className="dash-chart-card dash-risk">
      <header>
        <h3>
          <span aria-hidden="true">
            ▥
          </span>{" "}
          오늘 환자 위험도 현황
        </h3>
      </header>

      <div className="dash-risk__empty">
        <strong>
          위험도 데이터가 연결되지
          않았습니다
        </strong>

        <p>
          환자별 Critical · 고위험 ·
          주의 · 안정 분류 API가
          연결되면 현황을 표시합니다.
        </p>
      </div>
    </article>
  );
}

function DiseasePanel() {
  const style = {
    "--donut-fill": "#e8edf4",
  } as CSSProperties;

  return (
    <article className="dash-chart-card">
      <header>
        <h3>
          <span aria-hidden="true">
            ⬡
          </span>{" "}
          뇌질환별 환자 분포
        </h3>
      </header>

      <div className="dash-disease">
        <div
          className="dash-donut"
          style={style}
        >
          <div>
            <small>총</small>
            <strong>—</strong>
          </div>
        </div>

        <div className="dash-disease__empty">
          <strong>
            질환 분류 데이터 없음
          </strong>

          <p>
            AI 분석 유형은 확정
            진단으로 간주하지
            않습니다.
          </p>
        </div>
      </div>

      <p className="dash-source-note">
        환자별 확정 질환 데이터
        연동 예정
      </p>
    </article>
  );
}

function AIStatusPanel({
  analyses,
}: {
  analyses: AIAnalysisItem[];
}) {
  const modelCounts =
    MODEL_GROUPS.map(
      (group) =>
        analyses.filter(
          (analysis) =>
            includesModel(
              analysis,
              group.key,
            ),
        ).length,
    );

  const max =
    Math.max(
      ...modelCounts,
      1,
    );

  const queued =
    analyses.filter(
      (item) =>
        item.status === "QUEUED",
    ).length;

  const processing =
    analyses.filter(
      (item) =>
        item.status ===
          "PROCESSING" ||
        item.status ===
          "RETRYING",
    ).length;

  const completed =
    analyses.filter(
      (item) =>
        item.status ===
        "COMPLETED",
    ).length;

  return (
    <article className="dash-chart-card dash-ai-status">
      <header>
        <h3>
          <span aria-hidden="true">
            ◴
          </span>{" "}
          AI 분석 현황
        </h3>
      </header>

      <div className="dash-ai-bars">
        {MODEL_GROUPS.map(
          (group, index) => (
            <div key={group.key}>
              <span>
                {group.label}
              </span>

              <div>
                <i
                  style={{
                    width: `${
                      (
                        modelCounts[
                          index
                        ] /
                        max
                      ) *
                      100
                    }%`,
                    background:
                      group.color,
                  }}
                />
              </div>

              <strong>
                {
                  modelCounts[
                    index
                  ]
                }
              </strong>
            </div>
          ),
        )}
      </div>

      <div className="dash-ai-summary">
        분석 대기{" "}
        <strong>
          {queued}건
        </strong>{" "}
        · 분석중{" "}
        <strong>
          {processing}건
        </strong>{" "}
        · 현재 완료{" "}
        <strong>
          {completed}건
        </strong>
      </div>
    </article>
  );
}

function WorkflowPanel({
  assessments,
  studies,
  analyses,
  consultations,
  selectedDate,
}: {
  assessments: AssessmentWorklistItem[];
  studies: ImagingStudy[];
  analyses: AIAnalysisItem[];
  consultations: ConsultationListItem[];
  selectedDate: Date;
}) {
  const rows: Array<
    [
      string,
      number | null,
      number | null,
      number | null,
    ]
  > = [
    [
      "초기평가",
      assessments.filter(
        (item) =>
          item.status ===
          "IN_PROGRESS",
      ).length,
      assessments.filter(
        (item) =>
          item.status ===
          "PENDING",
      ).length,
      assessments.filter((item) => item.status === "COMPLETED" && isToday(item.created_at, selectedDate)).length,
    ],
    [
      "영상검사",
      studies.filter((item) => item.status === "RECEIVING").length,
      studies.filter(
        (item) =>
          item.status === "INCOMPLETE" || item.status === "UNMATCHED",
      ).length,
      studies.filter((item) => item.status === "AVAILABLE" && isToday(item.study_at, selectedDate)).length,
    ],
    [
      "AI 분석",
      analyses.filter(
        (item) =>
          item.status ===
          "PROCESSING",
      ).length,
      analyses.filter(
        (item) =>
          item.status ===
          "QUEUED",
      ).length,
      analyses.filter((item) => item.status === "COMPLETED" && isToday(item.completed_at, selectedDate)).length,
    ],
    [
      "협진",
      consultations.filter(
        (item) =>
          item.status ===
          "IN_PROGRESS",
      ).length,
      consultations.filter(
        (item) =>
          item.status ===
          "REQUESTED",
      ).length,
      consultations.filter(
        (item) =>
          item.status ===
            "RESPONDED" &&
          isToday(
            item.completed_at,
            selectedDate,
          ),
      ).length,
    ],
    [
      "처방 / DUR",
      null,
      null,
      null,
    ],
  ];

  return (
    <article className="dash-workflow dash-chart-card">
      <header>
        <h3>
          <span aria-hidden="true">
            ▣
          </span>{" "}
          진료 워크플로우 현황
        </h3>

        <button
          type="button"
          disabled
        >
          전체 보기 ›
        </button>
      </header>

      <div className="dash-table-wrap">
        <table>
          <thead>
            <tr>
              <th>단계</th>
              <th>진행중</th>
              <th>대기</th>
              <th>완료 (오늘)</th>
            </tr>
          </thead>

          <tbody>
            {rows.map(
              ([
                label,
                active,
                waiting,
                done,
              ]) => (
                <tr key={label}>
                  <td>
                    <i />
                    {label}
                  </td>

                  <td>
                    {active ?? "—"}
                  </td>

                  <td>
                    {waiting ?? "—"}
                  </td>

                  <td>
                    {done ?? "—"}
                  </td>
                </tr>
              ),
            )}
          </tbody>
        </table>
      </div>
    </article>
  );
}

function PatientQuickView({
  patient,
  studies,
  analyses,
  encounter,
  onOpenPatient,
  onOpenImaging,
}: {
  patient: Patient | null;
  studies: ImagingStudy[];
  analyses: AIAnalysisItem[];
  encounter: EncounterListItem | null;
  onOpenPatient: (
    patient: Patient,
  ) => void;
  onOpenImaging?: () => void;
}) {
  if (!patient) {
    return (
      <article className="dash-quick dash-chart-card">
        <header>
          <h3>
            환자 Quick View
          </h3>
        </header>

        <div className="dash-empty">
          왼쪽 환자 목록에서
          환자를 선택하세요.
        </div>
      </article>
    );
  }

  const patientStudies =
    studies.filter(
      (study) =>
        study.patient_id ===
        patient.id,
    );

  const ids =
    new Set(
      patientStudies.map(
        (study) =>
          study.id,
      ),
    );

  const patientAnalyses =
    analyses.filter(
      (analysis) =>
        ids.has(
          analysis.study_id,
        ),
    );

  const age =
    getAge(patient);

  return (
    <article className="dash-quick dash-chart-card">
      <header>
        <h3>
          <span aria-hidden="true">
            ♨
          </span>{" "}
          환자 Quick View
        </h3>

        <button
          type="button"
          aria-label="추가 메뉴"
          disabled
        >
          ⋮
        </button>
      </header>

      <div className="dash-quick__person">
        <span>♙</span>

        <div>
          <h4>
            {patient.name}{" "}
            {encounter && (
              <em
                className={
                  encounter.status === "IN_PROGRESS"
                    ? "is-in-progress"
                    : encounter.status === "REGISTERED"
                      ? "is-registered"
                      : "is-default"
                }
              >
                {encounter.status === "IN_PROGRESS"
                  ? "진료중"
                  : encounter.status === "REGISTERED"
                    ? "접수"
                    : encounter.status}
              </em>
            )}
          </h4>

          <p>
            {formatSex(
              patient.sex,
            )}
            {" · "}
            {age === null
              ? "-"
              : `${age}세`}
            {" | "}
            {patient.birth_date ??
              "-"}
            {" | "}
            진료과 미연결
          </p>
        </div>
      </div>

      <div className="dash-quick__status">
        <div>
          <span>▧</span>

          <p>
            영상 상태
            <strong>
              {patientStudies.length >
              0
                ? patientStudies[0]
                    .status
                : "영상 없음"}
            </strong>
          </p>
        </div>

        <div>
          <span>AI</span>

          <p>
            AI 분석
            <strong>
              {patientAnalyses.length >
              0
                ? patientAnalyses[0]
                    .status
                : "분석 없음"}
            </strong>
          </p>
        </div>
      </div>

      <dl>
        <div>
          <dt>내원일</dt>
          <dd>{encounter?.arrived_at ? new Date(encounter.arrived_at).toLocaleDateString("ko-KR") : "Encounter 없음"}</dd>
        </div>

        <div>
          <dt>내원 형태</dt>
          <dd>{encounter?.encounter_type ?? "Encounter 없음"}</dd>
        </div>

        <div>
          <dt>Encounter 상태</dt>
          <dd>{encounter?.status ?? "Encounter 없음"}</dd>
        </div>
      </dl>

      <div className="dash-quick__actions">
        <button
          type="button"
          onClick={() =>
            onOpenPatient(
              patient,
            )
          }
        >
          환자 상세 보기 →
        </button>

        <button
          type="button"
          onClick={
            onOpenImaging
          }
          disabled={
            !onOpenImaging
          }
        >
          ▷ 영상/AI 보기
        </button>
      </div>
    </article>
  );
}

export default function Dashboard({
  currentUser,
  onOpenPatient,
  onOpenMenu,
}: DashboardProps) {
  const [
    data,
    setData,
  ] =
    useState<DashboardData>(
      EMPTY_DATA,
    );

  const [
    selectedPatient,
    setSelectedPatient,
  ] =
    useState<Patient | null>(
      null,
    );

  const [
    search,
    setSearch,
  ] =
    useState("");

  const [
    selectedDate,
    setSelectedDate,
  ] =
    useState(
      () => new Date(),
    );

  const [
    error,
    setError,
  ] =
    useState<string | null>(
      null,
    );

  useEffect(() => {
    let active = true;

    Promise.allSettled([
      getPatients(),
      getImagingStudies(),
      getAIAnalyses(),
      getConsultations(),
    ]).then(
      ([
        patients,
        studies,
        analyses,
        consultations,
      ]) => {
        if (!active) {
          return;
        }

        const next = {
          patients:
            patients.status ===
            "fulfilled"
              ? patients.value
                  .results
              : [],

          studies:
            studies.status ===
            "fulfilled"
              ? studies.value
              : [],

          analyses:
            analyses.status ===
            "fulfilled"
              ? analyses.value
                  .results
              : [],

          consultations:
            consultations.status ===
            "fulfilled"
              ? consultations.value
                  .results
              : [],

          assessments:
            [],
          encounters: [],
        };

        setData(next);

        setSelectedPatient(
          (current) =>
            current ??
            next.patients[0] ??
            null,
        );

        void Promise.allSettled(
          next.patients.map((patient) => getPatientEncounters(patient.id)),
        ).then((results) => {
          if (!active) return;
          const encounters = results.flatMap((result) =>
            result.status === "fulfilled" ? result.value : [],
          );
          setData((current) => ({ ...current, encounters }));
        });

        if (
          [
            patients,
            studies,
            analyses,
            consultations,
          ].some(
            (result) =>
              result.status ===
              "rejected",
          )
        ) {
          setError(
            "일부 Dashboard 데이터를 불러오지 못했습니다.",
          );
        }
      },
    );

    return () => {
      active = false;
    };
  }, []);

  const selectedStudies =
    useMemo(
      () =>
        selectedPatient
          ? data.studies.filter(
              (study) =>
                study.patient_id ===
                selectedPatient.id,
            )
          : [],
      [
        data.studies,
        selectedPatient,
      ],
    );

  const studyIds =
    useMemo(
      () =>
        new Set(
          selectedStudies.map(
            (study) =>
              study.id,
          ),
        ),
      [selectedStudies],
    );

  const selectedAnalyses =
    useMemo(
      () =>
        data.analyses.filter(
          (analysis) =>
            studyIds.has(
              analysis.study_id,
            ),
        ),
      [
        data.analyses,
        studyIds,
      ],
    );

  const selectedEncounter = selectedPatient
    ? data.encounters.find((encounter) => encounter.patient_id === selectedPatient.id) ?? null
    : null;
  const encountersForDate = data.encounters.filter((encounter) =>
    isToday(encounter.arrived_at, selectedDate),
  );

  const dateLabel =
    selectedDate.toLocaleDateString(
      "ko-KR",
      {
        year: "numeric",
        month: "long",
        day: "numeric",
        weekday: "short",
      },
    );

  function changeDate(
    days: number,
  ) {
    setSelectedDate(
      (date) => {
        const next =
          new Date(date);

        next.setDate(
          next.getDate() +
            days,
        );

        return next;
      },
    );
  }

  function selectPatient(
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
    <section className="clinical-dashboard">
      <DashboardPatientList
        patients={
          data.patients
        }
        studies={
          data.studies
        }
        analyses={
          data.analyses
        }
        selected={
          selectedPatient
        }
        search={search}
        onSearch={
          setSearch
        }
        onSelect={
          selectPatient
        }
        encounters={data.encounters}
      />

      <main className="dash-main">
        <header className="dash-heading">
          <div>
            <span>
              DASHBOARD
            </span>

            <h1>
              좋은 하루입니다,{" "}
              {currentUser.name}님{" "}
              <i>👋</i>
            </h1>

            <p>
              오늘도 환자들의 더
              나은 내일을 위해,
              함께 만들어가는
              진료를 응원합니다.
            </p>
          </div>

          <div className="dash-date">
            <strong>
              ▣ {dateLabel}
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
                changeDate(-1)
              }
              aria-label="이전 날짜"
            >
              ‹
            </button>

            <button
              type="button"
              onClick={() =>
                changeDate(1)
              }
              aria-label="다음 날짜"
            >
              ›
            </button>
          </div>
        </header>

        {error && (
          <div className="dash-warning">
            {error}
          </div>
        )}

        <section
          className="dash-kpis"
          aria-label="Dashboard 주요 지표"
        >
          <KpiCard
            icon="♟"
            label="오늘 환자"
            value={`${encountersForDate.length}건`}
            summary="Encounter 내원 기준"
            tone="blue"
          />

          <KpiCard
            icon="◷"
            label="대기 환자"
            value={`${encountersForDate.filter((encounter) => encounter.status === "REGISTERED").length}건`}
            summary="REGISTERED 상태"
            tone="purple"
          />

          <KpiCard
            icon="▧"
            label="영상검사"
            value={`${data.studies.length}건`}
            summary={`대기 ${
              data.studies.filter(
                (item) =>
                  item.status ===
                  "QUEUED",
              ).length
            } · 확인 ${
              data.studies.filter(
                (item) =>
                  item.status ===
                  "REVIEW_REQUIRED",
              ).length
            } · 준비 ${
              data.studies.filter(
                (item) =>
                  item.status ===
                  "READY",
              ).length
            }`}
            tone="green"
          />

          <KpiCard
            icon="AI"
            label="AI 분석"
            value={`${data.analyses.length}건`}
            summary={`대기 ${
              data.analyses.filter(
                (item) =>
                  item.status ===
                  "QUEUED",
              ).length
            } · 진행 ${
              data.analyses.filter(
                (item) =>
                  item.status ===
                  "PROCESSING",
              ).length
            } · 완료 ${
              data.analyses.filter(
                (item) =>
                  item.status ===
                  "COMPLETED",
              ).length
            }`}
            tone="violet"
          />

          <KpiCard
            icon="♣"
            label="협진 요청"
            value={`${data.consultations.length}건`}
            summary={`요청 ${
              data.consultations.filter(
                (item) =>
                  item.status ===
                  "REQUESTED",
              ).length
            } · 진행 ${
              data.consultations.filter(
                (item) =>
                  item.status ===
                  "IN_PROGRESS",
              ).length
            }`}
            tone="orange"
          />
        </section>

        <section className="dash-charts">
          <RiskPanel />

          <DiseasePanel />

          <AIStatusPanel
            analyses={
              data.analyses
            }
          />
        </section>

        <section className="dash-bottom">
          <WorkflowPanel
            assessments={
              data.assessments
            }
            studies={
              data.studies
            }
            analyses={
              data.analyses
            }
            consultations={
              data.consultations
            }
            selectedDate={
              selectedDate
            }
          />

          <PatientQuickView
            patient={
              selectedPatient
            }
            studies={
              selectedStudies
            }
            analyses={
              selectedAnalyses
            }
            encounter={selectedEncounter}
            onOpenPatient={
              onOpenPatient
            }
            onOpenImaging={
              onOpenMenu
                ? () =>
                    onOpenMenu(
                      "imaging",
                    )
                : undefined
            }
          />
        </section>
      </main>
    </section>
  );
}
