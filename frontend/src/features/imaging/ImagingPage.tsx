import {
  useCallback,
  useEffect,
  useMemo,
  useState,
} from "react";

import {
  getImagingStudies,
} from "./api";

import type {
  AnalysisType,
  ImagingFilter,
  ImagingStatus,
  ImagingStudy,
} from "./types";

import "./imaging.css";


/* =========================================================
   화면 표시용 Label
   ========================================================= */

const analysisLabels: Record<AnalysisType, string> = {
  HEMORRHAGE: "뇌출혈",
  ISCHEMIA: "뇌경색",
  ANEURYSM: "뇌동맥류",
};


const statusLabels: Record<ImagingStatus, string> = {
  READY: "준비완료",
  REVIEW_REQUIRED: "확인필요",
  QUEUED: "분석대기",
};


type DateFilter =
  | "7D"
  | "30D"
  | "ALL";


export default function ImagingPage() {


  /* =======================================================
     API 데이터
     ======================================================= */

  const [
    studies,
    setStudies,
  ] = useState<ImagingStudy[]>([]);


  const [
    loading,
    setLoading,
  ] = useState(true);


  const [
    error,
    setError,
  ] = useState<string | null>(
    null,
  );


  const [
    lastLoadedAt,
    setLastLoadedAt,
  ] = useState<Date | null>(
    null,
  );


  /* =======================================================
     필터
     ======================================================= */

  const [
    modalityFilter,
    setModalityFilter,
  ] = useState<ImagingFilter>(
    "ALL",
  );


  const [
    dateFilter,
    setDateFilter,
  ] = useState<DateFilter>(
    "7D",
  );


  /* =======================================================
     선택 영상
     ======================================================= */

  const [
    selectedStudyId,
    setSelectedStudyId,
  ] = useState<string | null>(
    null,
  );


  const [
    selectedAnalysis,
    setSelectedAnalysis,
  ] = useState<AnalysisType | "">(
    "",
  );


  /* =======================================================
     페이지네이션
     ======================================================= */

  const [
    currentPage,
    setCurrentPage,
  ] = useState(1);


  const pageSize = 5;


  /* =======================================================
     영상 목록 조회

     React
     → imaging/api.ts
     → api/client.ts
     → Mock / Backend API
     ======================================================= */

  const loadStudies = useCallback(
    async () => {

      setLoading(true);

      setError(
        null,
      );


      try {

        const response =
          await getImagingStudies();


        setStudies(
          response,
        );


        setLastLoadedAt(
          new Date(),
        );

      } catch (requestError) {

        console.error(
          "Failed to load imaging studies:",
          requestError,
        );


        setStudies(
          [],
        );


        setError(
          "영상 목록을 불러오지 못했습니다.",
        );

      } finally {

        setLoading(
          false,
        );

      }

    },
    [],
  );


  useEffect(() => {

    void loadStudies();

  }, [
    loadStudies,
  ]);


  /* =======================================================
     모달리티별 건수
     ======================================================= */

  const modalityCounts =
    useMemo(
      () => {

        return {

          ALL:
            studies.length,

          CT:
            studies.filter(
              (study) =>
                study.modality ===
                "CT",
            ).length,

          MRI:
            studies.filter(
              (study) =>
                study.modality ===
                "MRI",
            ).length,

          MRA:
            studies.filter(
              (study) =>
                study.modality ===
                "MRA",
            ).length,

        };

      },
      [
        studies,
      ],
    );


  /* =======================================================
     필터 적용
     ======================================================= */

  const filteredStudies =
    useMemo(
      () => {

        return studies.filter(
          (study) => {

            /* 모달리티 */

            const matchesModality =
              modalityFilter ===
                "ALL" ||
              study.modality ===
                modalityFilter;


            if (
              !matchesModality
            ) {

              return false;

            }


            /* 전체 기간 */

            if (
              dateFilter ===
              "ALL"
            ) {

              return true;

            }


            /* 기간 필터 */

            const studyDate =
              new Date(
                study.study_at,
              );


            const cutoffDate =
              new Date();


            if (
              dateFilter ===
              "7D"
            ) {

              cutoffDate.setDate(
                cutoffDate.getDate() -
                  7,
              );

            }


            if (
              dateFilter ===
              "30D"
            ) {

              cutoffDate.setDate(
                cutoffDate.getDate() -
                  30,
              );

            }


            return (
              studyDate >=
              cutoffDate
            );

          },
        );

      },
      [
        studies,
        modalityFilter,
        dateFilter,
      ],
    );


  /* =======================================================
     페이지네이션
     ======================================================= */

  const totalPages =
    Math.max(
      1,
      Math.ceil(
        filteredStudies.length /
          pageSize,
      ),
    );


  const visibleStudies =
    filteredStudies.slice(
      (currentPage - 1) *
        pageSize,

      currentPage *
        pageSize,
    );


  /* =======================================================
     선택된 영상
     ======================================================= */

  const selectedStudy =
    studies.find(
      (study) =>
        study.id ===
        selectedStudyId,
    ) ?? null;


  /* =======================================================
     모달리티 변경
     ======================================================= */

  const handleModalityChange = (
    value: ImagingFilter,
  ) => {

    setModalityFilter(
      value,
    );


    setCurrentPage(
      1,
    );


    setSelectedStudyId(
      null,
    );


    setSelectedAnalysis(
      "",
    );

  };


  /* =======================================================
     영상 선택
     ======================================================= */

  const handleStudySelect = (
    study: ImagingStudy,
  ) => {

    if (
      selectedStudyId ===
      study.id
    ) {

      setSelectedStudyId(
        null,
      );


      setSelectedAnalysis(
        "",
      );


      return;

    }


    setSelectedStudyId(
      study.id,
    );


    setSelectedAnalysis(
      study.recommended_analysis,
    );

  };


  /* =======================================================
     AI 분석 실행 가능 여부
     ======================================================= */

  const canStartAnalysis =
    selectedStudy !== null &&
    selectedStudy.status ===
      "READY" &&
    selectedAnalysis !== "" &&
    selectedAnalysis ===
      selectedStudy
        .recommended_analysis;


  /* =======================================================
     AI 분석 시작

     현재는 UI까지만 구현.
     실제 POST는 Backend API 연결 시 추가.
     ======================================================= */

  const handleStartAnalysis =
    () => {

      if (
        !canStartAnalysis
      ) {

        return;

      }


      console.info(
        "AI analysis API is not connected yet.",
      );

    };


  /* =======================================================
     마지막 조회 시간
     ======================================================= */

  const lastLoadedText =
    lastLoadedAt === null
      ? "—"
      : lastLoadedAt.toLocaleString(
          "ko-KR",
          {
            year: "numeric",
            month: "2-digit",
            day: "2-digit",
            hour: "2-digit",
            minute: "2-digit",
          },
        );


  /* =======================================================
     화면
     ======================================================= */

  return (

    <section className="imaging-page">


      {/* ===================================================
          제목
          =================================================== */}

      <div className="imaging-heading">

        <h2>
          검사 · 분석
        </h2>


        <p>
          의료영상을 불러오고 AI 분석을 시작합니다.
        </p>

      </div>


      {/* ===================================================
          영상 목록 Card
          =================================================== */}

      <section className="imaging-list-card">


        {/* ===============================================
            영상 목록 Header
            =============================================== */}

        <div className="imaging-list-header">

          <div className="imaging-list-heading">

            <h3>
              영상 목록
            </h3>


            <p>
              등록된 영상 목록에서 분석할 검사를 선택하세요.
            </p>

          </div>


          {/* Orthanc 상태 */}

          <div className="imaging-server-status">

            <div className="imaging-server-info">

              <span
                className={
                  error
                    ? "server-dot error"
                    : "server-dot connected"
                }
              />


              <strong>

                {loading
                  ? "Orthanc DICOM Server 확인 중"
                  : error
                    ? "Orthanc DICOM Server 연결 확인 필요"
                    : "Orthanc DICOM Server 연결됨"}

              </strong>


              <span className="server-divider">
                |
              </span>


              <span className="last-loaded">

                마지막 조회:{" "}
                {lastLoadedText}

              </span>

            </div>


            <button
              type="button"
              className="imaging-refresh-button"
              onClick={() =>
                void loadStudies()
              }
              disabled={loading}
            >

              {loading
                ? "불러오는 중"
                : "새로고침"}

            </button>

          </div>

        </div>


        {/* ===============================================
            CT / MRI / MRA Tabs
            =============================================== */}

        <div className="imaging-tabs">

          {(
            [
              "ALL",
              "CT",
              "MRI",
              "MRA",
            ] as ImagingFilter[]
          ).map(
            (filter) => (

              <button
                key={filter}
                type="button"
                className={
                  modalityFilter ===
                  filter
                    ? "imaging-tab active"
                    : "imaging-tab"
                }
                onClick={() =>
                  handleModalityChange(
                    filter,
                  )
                }
              >

                {filter ===
                "ALL"
                  ? "전체"
                  : filter}


                <span>

                  (
                  {
                    modalityCounts[
                      filter
                    ]
                  }
                  )

                </span>

              </button>

            ),
          )}

        </div>


        {/* ===============================================
            Filters
            =============================================== */}

        <div className="imaging-filters">

          <label>

            <span>
              기간:
            </span>


            <select
              value={dateFilter}
              onChange={(
                event,
              ) => {

                setDateFilter(
                  event.target
                    .value as DateFilter,
                );


                setCurrentPage(
                  1,
                );

              }}
            >

              <option value="7D">
                최근 7일
              </option>

              <option value="30D">
                최근 30일
              </option>

              <option value="ALL">
                전체 기간
              </option>

            </select>

          </label>

        </div>


        {/* ===============================================
            Loading / Error
            =============================================== */}

        {loading && (

          <div className="imaging-message">

            영상 목록을 불러오는 중입니다.

          </div>

        )}


        {!loading &&
          error && (

            <div className="imaging-message error">

              {error}

            </div>

          )}


        {/* ===============================================
            Table
            =============================================== */}

        {!loading &&
          !error && (

            <div className="imaging-table-wrapper">

              <table className="imaging-table">

                <thead>

                  <tr>

                    <th aria-label="선택" />

                    <th>
                      검사일시
                    </th>

                    <th>
                      환자명
                    </th>

                    <th>
                      환자 등록번호
                    </th>

                    <th>
                      모달리티
                    </th>

                    <th>
                      시리즈
                    </th>

                    <th>
                      추천 분석
                    </th>

                    <th>
                      상태
                    </th>

                  </tr>

                </thead>


                <tbody>

                  {visibleStudies
                    .length ===
                  0 ? (

                    <tr>

                      <td
                        colSpan={8}
                        className="imaging-empty"
                      >

                        조건에 해당하는 영상이 없습니다.

                      </td>

                    </tr>

                  ) : (

                    visibleStudies.map(
                      (
                        study,
                      ) => (

                        <tr
                          key={
                            study.id
                          }
                          className={
                            selectedStudyId ===
                            study.id
                              ? "selected"
                              : ""
                          }
                        >

                          <td>

                            <input
                              type="checkbox"
                              checked={
                                selectedStudyId ===
                                study.id
                              }
                              onChange={() =>
                                handleStudySelect(
                                  study,
                                )
                              }
                              aria-label={`${study.patient_name} 영상 선택`}
                            />

                          </td>


                          <td>

                            {new Date(
                              study.study_at,
                            ).toLocaleString(
                              "ko-KR",
                            )}

                          </td>


                          <td>

                            {
                              study.patient_name
                            }

                          </td>


                          <td>

                            {
                              study.patient_no
                            }

                          </td>


                          <td>

                            {
                              study.modality
                            }

                          </td>


                          <td>

                            {
                              study.series
                            }

                          </td>


                          <td>

                            {
                              analysisLabels[
                                study
                                  .recommended_analysis
                              ]
                            }

                          </td>


                          <td>

                            <span
                              className={`imaging-status imaging-status-${study.status.toLowerCase()}`}
                            >

                              {
                                statusLabels[
                                  study.status
                                ]
                              }

                            </span>

                          </td>

                        </tr>

                      ),
                    )

                  )}

                </tbody>

              </table>

            </div>

          )}


        {/* ===============================================
            Pagination
            =============================================== */}

        {!loading &&
          !error && (

            <div className="imaging-pagination">

              <span>

                총{" "}
                {
                  filteredStudies.length
                }
                건

              </span>


              <div>

                <button
                  type="button"
                  disabled={
                    currentPage ===
                    1
                  }
                  onClick={() =>
                    setCurrentPage(
                      (page) =>
                        Math.max(
                          1,
                          page - 1,
                        ),
                    )
                  }
                >

                  ‹

                </button>


                <span className="current-page">

                  {currentPage}

                </span>


                <button
                  type="button"
                  disabled={
                    currentPage ===
                    totalPages
                  }
                  onClick={() =>
                    setCurrentPage(
                      (page) =>
                        Math.min(
                          totalPages,
                          page + 1,
                        ),
                    )
                  }
                >

                  ›

                </button>

              </div>

            </div>

          )}

      </section>


      {/* ===================================================
          AI 분석 실행
          =================================================== */}

      <section className="imaging-analysis-bar">

        <div className="analysis-selected-info">

          <div className="analysis-info-icon">
            i
          </div>


          <div>

            <strong>

              {selectedStudy
                ? `${selectedStudy.series} 영상이 확인되었습니다`
                : "분석할 영상을 선택하세요"}

            </strong>


            <p>

              추천 분석:{" "}

              {selectedStudy
                ? analysisLabels[
                    selectedStudy
                      .recommended_analysis
                  ]
                : "—"}

            </p>

          </div>

        </div>


        <div className="analysis-controls">

          <label>

            <span>
              분석 종류:
            </span>


            <select
              value={
                selectedAnalysis
              }
              disabled={
                !selectedStudy
              }
              onChange={(
                event,
              ) =>
                setSelectedAnalysis(
                  event.target
                    .value as AnalysisType,
                )
              }
            >

              <option value="">
                분석 종류 선택
              </option>

              <option value="HEMORRHAGE">
                뇌출혈
              </option>

              <option value="ISCHEMIA">
                뇌경색
              </option>

              <option value="ANEURYSM">
                뇌동맥류
              </option>

            </select>

          </label>


          <button
            type="button"
            className="analysis-start-button"
            disabled={
              !canStartAnalysis
            }
            onClick={
              handleStartAnalysis
            }
          >

            AI 분석 시작

          </button>

        </div>

      </section>

    </section>

  );

}