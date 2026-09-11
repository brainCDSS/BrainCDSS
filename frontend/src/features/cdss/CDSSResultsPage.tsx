import {
  useCallback,
  useEffect,
  useMemo,
  useState,
} from "react";

import type {
  KeyboardEvent,
} from "react";

import {
  getPatients,
} from "../patients/api";

import type {
  Patient,
} from "../patients/types";

import "./cdss.css";


const PATIENTS_PER_PAGE = 8;


type DetailTab =
  | "cdss"
  | "ai"
  | "clinical"
  | "review"
  | "consultation";


const DETAIL_TABS: Array<{
  key: DetailTab;
  label: string;
}> = [
  {
    key: "cdss",
    label: "CDSS 판단지원",
  },
  {
    key: "ai",
    label: "AI 분석 결과",
  },
  {
    key: "clinical",
    label: "임상 정보",
  },
  {
    key: "review",
    label: "의사 검토 / 판독",
  },
  {
    key: "consultation",
    label: "협진 현황",
  },
];


function sexLabel(
  sex?: string | null,
) {
  switch (sex) {
    case "M":
      return "남";

    case "F":
      return "여";

    default:
      return "-";
  }
}


function formatDate(
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

  return date.toLocaleDateString(
    "ko-KR",
  );
}


function ageLabel(
  patient: Patient,
) {
  if (
    patient.estimated_age !== null &&
    patient.estimated_age !== undefined
  ) {
    return `${patient.estimated_age}세`;
  }

  if (!patient.birth_date) {
    return "-";
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
    return "-";
  }

  const today =
    new Date();

  let age =
    today.getFullYear() -
    birth.getFullYear();

  const birthdayPassed =
    today.getMonth() >
      birth.getMonth() ||
    (
      today.getMonth() ===
        birth.getMonth() &&
      today.getDate() >=
        birth.getDate()
    );

  if (!birthdayPassed) {
    age -= 1;
  }

  return `${Math.max(
    age,
    0,
  )}세`;
}


export default function CDSSResultsPage() {
  const [
    patients,
    setPatients,
  ] = useState<Patient[]>([]);

  const [
    patientCount,
    setPatientCount,
  ] = useState(0);

  const [
    selectedPatientId,
    setSelectedPatientId,
  ] = useState<
    string | null
  >(null);

  const [
    search,
    setSearch,
  ] = useState("");

  const [
    patientPage,
    setPatientPage,
  ] = useState(1);

  const [
    activeTab,
    setActiveTab,
  ] = useState<DetailTab>(
    "cdss",
  );

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


  /* =======================================================
     환자 목록 조회
  ======================================================= */

  const loadPatients =
    useCallback(
      async (
        keyword = "",
      ) => {
        setLoading(true);
        setError(null);

        try {
          const firstResponse =
            await getPatients(
              keyword.trim() ||
                undefined,
              1,
            );

          let allPatients =
            firstResponse.results ?? [];

          const totalCount =
            firstResponse.count ??
            allPatients.length;

          if (
            allPatients.length > 0 &&
            totalCount >
              allPatients.length
          ) {
            const serverPageSize =
              allPatients.length;

            const totalServerPages =
              Math.ceil(
                totalCount /
                  serverPageSize,
              );

            const remainingPages =
              Array.from(
                {
                  length:
                    totalServerPages -
                    1,
                },
                (
                  _,
                  index,
                ) => index + 2,
              );

            const responses =
              await Promise.all(
                remainingPages.map(
                  (page) =>
                    getPatients(
                      keyword.trim() ||
                        undefined,
                      page,
                    ),
                ),
              );

            allPatients = [
              ...allPatients,
              ...responses.flatMap(
                (response) =>
                  response.results ??
                  [],
              ),
            ];
          }

          setPatients(
            allPatients,
          );

          setPatientCount(
            totalCount,
          );

          setPatientPage(1);

          setSelectedPatientId(
            allPatients[0]?.id ??
              null,
          );
        } catch {
          setPatients([]);
          setPatientCount(0);
          setPatientPage(1);
          setSelectedPatientId(
            null,
          );

          setError(
            "환자 목록을 불러오지 못했습니다.",
          );
        } finally {
          setLoading(false);
        }
      },
      [],
    );


  useEffect(() => {
    void loadPatients();
  }, [loadPatients]);


  /* =======================================================
     선택 환자
  ======================================================= */

  const selectedPatient =
    useMemo(
      () =>
        patients.find(
          (patient) =>
            patient.id ===
            selectedPatientId,
        ) ?? null,
      [
        patients,
        selectedPatientId,
      ],
    );


  /* =======================================================
     화면용 페이지네이션
  ======================================================= */

  const totalPatientPages =
    useMemo(
      () =>
        Math.max(
          1,
          Math.ceil(
            patients.length /
              PATIENTS_PER_PAGE,
          ),
        ),
      [patients.length],
    );


  const visiblePatients =
    useMemo(
      () => {
        const start =
          (
            patientPage -
            1
          ) *
          PATIENTS_PER_PAGE;

        return patients.slice(
          start,
          start +
            PATIENTS_PER_PAGE,
        );
      },
      [
        patients,
        patientPage,
      ],
    );


  function handlePatientPageChange(
    nextPage: number,
  ) {
    const safePage =
      Math.min(
        Math.max(
          nextPage,
          1,
        ),
        totalPatientPages,
      );

    setPatientPage(
      safePage,
    );

    const firstPatient =
      patients[
        (
          safePage -
          1
        ) *
          PATIENTS_PER_PAGE
      ];

    if (firstPatient) {
      setSelectedPatientId(
        firstPatient.id,
      );

      setActiveTab(
        "cdss",
      );
    }
  }


  function handleSearch() {
    void loadPatients(
      search,
    );
  }


  function handleSearchKeyDown(
    event:
      KeyboardEvent<HTMLInputElement>,
  ) {
    if (
      event.key ===
      "Enter"
    ) {
      event.preventDefault();

      handleSearch();
    }
  }


  /* =======================================================
     상세 탭
  ======================================================= */

  function renderDetailTab() {
    if (!selectedPatient) {
      return (
        <div className="cdss-empty cdss-empty--large">
          환자를 선택해 주세요.
        </div>
      );
    }


    if (
      activeTab === "cdss"
    ) {
      return (
        <>
          {/* 상단 */}

          <div className="cdss-result-top-grid">

            <article className="cdss-panel">
              <header className="cdss-panel__header">
                <h3>
                  AI 분석 결과
                </h3>
              </header>

              <div className="cdss-empty cdss-empty--analysis">
                표시할 AI 분석 결과가 없습니다.
              </div>
            </article>


            <article className="cdss-panel">
              <header className="cdss-panel__header">
                <h3>
                  주요 영상
                </h3>
              </header>

              <div className="cdss-image-preview-grid">

                <div className="cdss-image-placeholder">
                  <strong>
                    원본 영상
                  </strong>
                </div>

                <div className="cdss-image-placeholder">
                  <strong>
                    AI 분석
                  </strong>
                </div>

                <div className="cdss-image-placeholder">
                  <strong>
                    Overlay
                  </strong>
                </div>

              </div>
            </article>

          </div>


          {/* 하단 */}

          <div className="cdss-result-bottom-grid">

            <article className="cdss-info-card">

              <header>
                <span className="cdss-info-icon">
                  AI
                </span>

                <h3>
                  AI 분석 상세
                </h3>
              </header>

              <div className="cdss-info-empty">
                표시할 분석 상세 결과가 없습니다.
              </div>

              <footer>
                <button
                  type="button"
                  disabled
                >
                  AI 상세 결과 보기
                </button>
              </footer>

            </article>


            <article className="cdss-info-card">

              <header>
                <span className="cdss-info-icon">
                  MD
                </span>

                <h3>
                  의사 검토 / 판독
                </h3>
              </header>

              <div className="cdss-info-empty">
                등록된 의료진 소견이 없습니다.
              </div>

              <footer>
                <button
                  type="button"
                  disabled
                >
                  판독 결과 확인
                </button>
              </footer>

            </article>


            <article className="cdss-info-card cdss-info-card--decision">

              <header>
                <span className="cdss-info-icon">
                  CDSS
                </span>

                <h3>
                  CDSS 판단지원
                </h3>
              </header>

              <div className="cdss-decision-placeholder">

                <strong>
                  표시할 CDSS 결과가 없습니다.
                </strong>

                <p>
                  임상 의사결정 지원 결과가
                  연결되면 이 영역에서
                  확인할 수 있습니다.
                </p>

              </div>

              <footer>
                <button
                  type="button"
                  disabled
                >
                  상세 CDSS 결과
                </button>
              </footer>

            </article>

          </div>


          <footer className="cdss-quick-actions">

            <strong>
              빠른 작업
            </strong>

            <button
              type="button"
              disabled
            >
              영상 보기
            </button>

            <button
              type="button"
              disabled
            >
              협진 요청
            </button>

            <button
              type="button"
              disabled
            >
              환자 요약
            </button>

          </footer>
        </>
      );
    }


    if (
      activeTab === "ai"
    ) {
      return (
        <section className="cdss-single-panel">

          <header>
            <h3>
              AI 분석 결과
            </h3>
          </header>

          <div className="cdss-empty cdss-empty--large">
            표시할 AI 분석 결과가 없습니다.
          </div>

        </section>
      );
    }


    if (
      activeTab ===
      "clinical"
    ) {
      return (
        <section className="cdss-single-panel">

          <header>
            <h3>
              임상 정보
            </h3>
          </header>

          <dl className="cdss-clinical-list">

            <div>
              <dt>
                환자번호
              </dt>

              <dd>
                {selectedPatient.patient_no ||
                  "-"}
              </dd>
            </div>


            <div>
              <dt>
                환자명
              </dt>

              <dd>
                {selectedPatient.name ||
                  "-"}
              </dd>
            </div>


            <div>
              <dt>
                성별
              </dt>

              <dd>
                {sexLabel(
                  selectedPatient.sex,
                )}
              </dd>
            </div>


            <div>
              <dt>
                나이
              </dt>

              <dd>
                {ageLabel(
                  selectedPatient,
                )}
              </dd>
            </div>


            <div>
              <dt>
                생년월일
              </dt>

              <dd>
                {formatDate(
                  selectedPatient.birth_date,
                )}
              </dd>
            </div>


            <div>
              <dt>
                연락처
              </dt>

              <dd>
                {selectedPatient.phone ||
                  "-"}
              </dd>
            </div>

          </dl>

        </section>
      );
    }


    if (
      activeTab === "review"
    ) {
      return (
        <section className="cdss-single-panel">

          <header>
            <h3>
              의사 검토 / 판독
            </h3>
          </header>

          <div className="cdss-empty cdss-empty--large">
            등록된 의료진 소견이 없습니다.
          </div>

        </section>
      );
    }


    return (
      <section className="cdss-single-panel">

        <header>
          <h3>
            협진 현황
          </h3>
        </header>

        <div className="cdss-empty cdss-empty--large">
          표시할 협진 정보가 없습니다.
        </div>

      </section>
    );
  }


  return (
    <section className="cdss-page">

      {/* 페이지 헤더 */}

      <header className="cdss-page-header">

        <div className="cdss-title-row">

          <h2>
            CDSS 결과
          </h2>

          <span />

          <p>
            AI 분석 결과와 임상 정보를 종합하여
            치료 의사결정을 지원합니다.
          </p>

        </div>


        <button
          type="button"
          className="cdss-refresh-button"
          disabled={loading}
          onClick={() =>
            void loadPatients(
              search,
            )
          }
        >
          {loading
            ? "조회 중..."
            : "데이터 새로고침"}
        </button>

      </header>


      {/* Summary */}

      <section className="cdss-summary-row">

        <article className="cdss-summary-card cdss-summary-card--primary">
          <span>
            전체 환자
          </span>

          <strong>
            {patientCount}
          </strong>
        </article>


        <article className="cdss-summary-card cdss-summary-card--ischemia">
          <span>
            허혈성 뇌졸중 의심
          </span>

          <strong>
            -
          </strong>
        </article>


        <article className="cdss-summary-card cdss-summary-card--hemorrhage">
          <span>
            뇌출혈 의심
          </span>

          <strong>
            -
          </strong>
        </article>


        <article className="cdss-summary-card cdss-summary-card--aneurysm">
          <span>
            동맥류 의심
          </span>

          <strong>
            -
          </strong>
        </article>


        <article className="cdss-summary-card cdss-summary-card--normal">
          <span>
            특이소견 없음
          </span>

          <strong>
            -
          </strong>
        </article>


        <article className="cdss-summary-card cdss-summary-card--review">
          <span>
            확인 필요
          </span>

          <strong>
            -
          </strong>
        </article>

      </section>


      {/* Workspace */}

      <div className="cdss-workspace">

        {/* 환자 목록 */}

        <aside className="cdss-patient-panel">

          <header className="cdss-patient-panel__header">

            <h3>
              환자 목록
            </h3>

            <span>
              {patientCount}명
            </span>

          </header>


          <div className="cdss-patient-search">

            <input
              value={search}
              onChange={(
                event,
              ) =>
                setSearch(
                  event.target.value,
                )
              }
              onKeyDown={
                handleSearchKeyDown
              }
              placeholder="환자명 또는 환자번호 검색"
            />

            <button
              type="button"
              disabled={loading}
              onClick={
                handleSearch
              }
            >
              검색
            </button>

          </div>


          <div className="cdss-patient-list-head">
            <span>
              환자명
            </span>

            <span>
              환자번호
            </span>
          </div>


          <div className="cdss-patient-list">

            {loading ? (
              <div className="cdss-patient-list-state">
                환자 목록을 불러오는 중입니다.
              </div>
            ) : error ? (
              <div className="cdss-patient-list-state is-error">
                {error}
              </div>
            ) : visiblePatients.length ===
              0 ? (
              <div className="cdss-patient-list-state">
                조회된 환자가 없습니다.
              </div>
            ) : (
              visiblePatients.map(
                (patient) => (
                  <button
                    type="button"
                    key={
                      patient.id
                    }
                    className={
                      patient.id ===
                      selectedPatientId
                        ? "cdss-patient-row is-selected"
                        : "cdss-patient-row"
                    }
                    onClick={() => {
                      setSelectedPatientId(
                        patient.id,
                      );

                      setActiveTab(
                        "cdss",
                      );
                    }}
                  >
                    <strong className="cdss-patient-name">
                      {patient.name ||
                        "-"}
                    </strong>

                    <span className="cdss-patient-number">
                      {patient.patient_no ||
                        "-"}
                    </span>
                  </button>
                ),
              )
            )}

          </div>


          <footer className="cdss-patient-pagination">

            <button
              type="button"
              aria-label="이전 페이지"
              disabled={
                loading ||
                patientPage <= 1
              }
              onClick={() =>
                handlePatientPageChange(
                  patientPage -
                    1,
                )
              }
            >
              ‹
            </button>


            <span>
              <strong>
                {patientPage}
              </strong>

              <span>
                /
              </span>

              {totalPatientPages}
            </span>


            <button
              type="button"
              aria-label="다음 페이지"
              disabled={
                loading ||
                patientPage >=
                  totalPatientPages
              }
              onClick={() =>
                handlePatientPageChange(
                  patientPage +
                    1,
                )
              }
            >
              ›
            </button>

          </footer>

        </aside>


        {/* 상세 */}

        <main className="cdss-detail-panel">

          <header className="cdss-patient-context">

            {selectedPatient ? (
              <div className="cdss-patient-context__main">

                <div className="cdss-patient-context__name">

                  <h3>
                    {selectedPatient.name ||
                      "환자명 없음"}
                  </h3>

                  <span>
                    {selectedPatient.patient_no ||
                      "-"}
                  </span>

                </div>


                <div className="cdss-patient-context__meta">

                  <span>
                    {sexLabel(
                      selectedPatient.sex,
                    )}
                  </span>

                  <span>
                    {ageLabel(
                      selectedPatient,
                    )}
                  </span>

                  <span>
                    {formatDate(
                      selectedPatient.birth_date,
                    )}
                  </span>

                  <span>
                    연락처{" "}
                    {selectedPatient.phone ||
                      "-"}
                  </span>

                  <span>
                    Encounter -
                  </span>

                </div>

              </div>
            ) : (
              <div className="cdss-context-empty">
                환자를 선택해 주세요.
              </div>
            )}

          </header>


          <nav
            className="cdss-detail-tabs"
            aria-label="CDSS 환자 상세 메뉴"
          >

            {DETAIL_TABS.map(
              (tab) => (
                <button
                  key={tab.key}
                  type="button"
                  className={
                    activeTab ===
                    tab.key
                      ? "is-active"
                      : ""
                  }
                  onClick={() =>
                    setActiveTab(
                      tab.key,
                    )
                  }
                >
                  {tab.label}
                </button>
              ),
            )}

          </nav>


          <div className="cdss-detail-content">
            {renderDetailTab()}
          </div>

        </main>

      </div>

    </section>
  );
}