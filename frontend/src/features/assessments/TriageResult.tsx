import {
  useEffect,
  useState,
} from "react";

import {
  completeAssessment,
  getClinicians,
} from "./api";

import type {
  AssessmentDetailResponse,
  Clinician,
  CompleteAssessmentResponse,
  TriagePriority,
} from "./types";

import "./css/triage_assessment.css";


interface TriageSummary {
  fastCompleted: number;
  fastAbnormal: number;
  screeningTotal: number;
  screeningCompleted: number;
  bpSys: string;
  bpDia: string;
  lkwAt: string;
}


interface Props {
  result: AssessmentDetailResponse | null;
  readOnly?: boolean;
  summary: TriageSummary;
  onBack: () => void;
  onComplete: () => void;
}


function priorityLabel(
  priority: string | null,
) {
  if (priority === "URGENT") {
    return "긴급";
  }

  if (priority === "EMERGENCY") {
    return "응급";
  }

  if (priority === "NON_EMERGENCY") {
    return "비응급";
  }

  return "-";
}


export default function TriageResult({
  result,
  readOnly = false,
  summary,
  onBack,
  onComplete,
}: Props) {

  const [
    clinicians,
    setClinicians,
  ] = useState<Clinician[]>([]);


  const [
    selectedUserId,
    setSelectedUserId,
  ] = useState("");

  const [
    selectedPriority,
    setSelectedPriority,
  ] = useState<TriagePriority | "">(
    result?.triage_priority ?? "",
  );


  const [
    loadingClinicians,
    setLoadingClinicians,
  ] = useState(false);


  const [
    completing,
    setCompleting,
  ] = useState(false);


  const [
    error,
    setError,
  ] = useState<string | null>(
    null,
  );


  const [
    completed,
    setCompleted,
  ] = useState<CompleteAssessmentResponse | null>(
    null,
  );


  const [
    showCompleteModal,
    setShowCompleteModal,
  ] = useState(false);

  const existingFinalized =
    readOnly ||
    Boolean(
      result &&
      result.status !== "DRAFT",
    );

  const finalized =
    completed !== null ||
    existingFinalized;


  /* ========================================================
     평가 결과
     ======================================================== */

  const redFlags =
    result?.items.filter(
      (item) =>
        item.is_red_flag,
    ) ?? [];


  const departmentId =
    result?.neurology_department_id ??
    null;


  const selectedClinician =
    clinicians.find(
      (clinician) =>
        clinician.user_id ===
        selectedUserId,
    ) ?? null;


  const finalScore =
    completed?.total_score ??
    result?.total_score ??
    (summary.screeningCompleted === 6
      ? summary.screeningTotal
      : null);


  const finalPriority =
    completed?.triage_priority ??
    result?.triage_priority ??
    selectedPriority ??
    null;

  const fastStatus =
    summary.fastCompleted === 3
      ? summary.fastAbnormal > 0
        ? "POSITIVE"
        : "NEGATIVE"
      : "INCOMPLETE";


  /* ========================================================
     담당 신경과 의료진 조회
     ======================================================== */

  useEffect(
    () => {
      let active =
        true;


      setClinicians(
        [],
      );

      setSelectedUserId(
        "",
      );

      setError(
        null,
      );


      if (
        existingFinalized ||
        !departmentId
      ) {
        return () => {
          active =
            false;
        };
      }


      setLoadingClinicians(
        true,
      );


      getClinicians(
        departmentId,
      )
        .then(
          (response) => {
            if (!active) {
              return;
            }

            setClinicians(
              response.clinicians.filter(
                (item) =>
                  item.is_active,
              ),
            );
          },
        )
        .catch(
          () => {
            if (!active) {
              return;
            }

            setError(
              "담당 신경과 의료진 목록을 불러오지 못했습니다.",
            );
          },
        )
        .finally(
          () => {
            if (active) {
              setLoadingClinicians(
                false,
              );
            }
          },
        );


      return () => {
        active =
          false;
      };
    },
    [
      departmentId,
      existingFinalized,
    ],
  );


  /* ========================================================
     평가 완료 + 담당 신경과 배정
     ======================================================== */

  async function handleComplete() {
    if (
      existingFinalized ||
      !result?.assessment_id ||
      !selectedUserId ||
      !selectedPriority ||
      completing
    ) {
      return;
    }


    try {
      setCompleting(
        true,
      );

      setError(
        null,
      );


      const response =
        await completeAssessment(
          result.assessment_id,
          {
            assigned_neurologist_id:
              selectedUserId,
            triage_priority:
              selectedPriority,
          },
        );


      setCompleted(
        response,
      );


      /*
       * API가 성공했을 때만
       * 완료 팝업을 표시한다.
       */
      setShowCompleteModal(
        true,
      );

    } catch {
      setError(
        "초기평가 완료 및 담당의 배정에 실패했습니다. 입력 항목과 담당의를 확인해 주세요.",
      );

    } finally {
      setCompleting(
        false,
      );
    }
  }


  return (
    <section className="triage-step-panel triage-result-step">

      {/* ====================================================
          Step Header
          ==================================================== */}

      <div className="triage-step-heading">

        <div>

          <span>
            STEP 4
          </span>


          <h2>
            {
              finalized
                ? "초기평가 완료"
                : "결과 · 담당 신경과 지정"
            }
          </h2>


          <p>
            {
              finalized
                ? "초기평가 및 담당 신경과 의료진 배정이 완료되었습니다."
                : "FAST, 선별점수, LKW를 확인해 우선순위와 담당 의료진을 지정합니다."
            }
          </p>

        </div>

      </div>


      {/* ====================================================
          평가 결과 + Summary
          ==================================================== */}

      <div className="triage-result-overview">

        <section className="triage-result-card">

          <div>

            <span className="triage-result-label">
              {
                finalized
                  ? "ASSESSMENT COMPLETED"
                  : "ASSESSMENT RESULT"
              }
            </span>


            <strong>
              {
                finalized
                  ? "최종 초기평가 결과"
                  : "초기평가 결과"
              }
            </strong>


            <p>
              {
                finalized
                  ? "초기 선별점수와 간호사 초기분류 결과입니다."
                  : "선별점수와 FAST/LKW를 확인한 뒤 초기평가 우선순위를 선택해 주세요."
              }
            </p>

          </div>


          <div className="triage-result-values">

            <div>

              <span>
                Total Score
              </span>

              <strong>
                {
                  finalScore ?? "-"
                }
                <small>
                  {" / 30"}
                </small>
              </strong>

            </div>


            <div>

              <span>
                Priority
              </span>

              <strong>
                {
                  priorityLabel(
                    finalPriority,
                  )
                }
              </strong>


              {
                !finalized && (
                  <small>
                    {
                      finalPriority ??
                      "결과 없음"
                    }
                  </small>
                )
              }

            </div>

          </div>

        </section>


        {/* ==================================================
            주요 입력 Summary
            ================================================== */}

        <section className="triage-input-summary">

          <h3>
            주요 입력 Summary
          </h3>


          <dl>

            <div>

              <dt>
                FAST
              </dt>

              <dd>
                <strong>
                  {fastStatus}
                </strong>

                <small>
                  {summary.fastCompleted}/3 응답 · 이상 {summary.fastAbnormal}개
                </small>
              </dd>

            </div>


            <div>

              <dt>
                BP
              </dt>

              <dd>
                {
                  summary.bpSys ||
                  "-"
                }
                {" / "}
                {
                  summary.bpDia ||
                  "-"
                }
              </dd>

            </div>


            <div>

              <dt>
                LKW
              </dt>

              <dd>
                {
                  summary.lkwAt
                    ? summary.lkwAt.replace(
                        "T",
                        " ",
                      )
                    : "-"
                }
              </dd>

            </div>


          </dl>

        </section>

      </div>


      {/* ====================================================
          Red Flag + 담당 신경과
          ==================================================== */}

      <div className="triage-result-columns">

        {/* ==================================================
            Red Flag
            ================================================== */}

        <section className="triage-result-subcard">

          <h3>
            Red Flag
          </h3>


          {
            redFlags.length === 0
              ? (
                <div className="triage-result-empty">
                  {
                    result
                      ? "확인된 Red Flag 항목이 없습니다."
                      : "평가 결과 연동 정보가 없습니다."
                  }
                </div>
              )
              : (
                <ul>

                  {
                    redFlags.map(
                      (item) => (
                        <li
                          key={
                            item.item_code
                          }
                        >

                          <strong>
                            {
                              item.item_code
                            }
                          </strong>


                          <span>
                            Red Flag
                          </span>

                        </li>
                      ),
                    )
                  }

                </ul>
              )
          }

        </section>


        {/* ==================================================
            초기평가 우선순위 + 담당 신경과
            ================================================== */}

        <section className="triage-result-subcard">

          <h3>
            초기평가 우선순위
          </h3>

          {
            finalized
              ? (
                <div className="triage-priority-completed">
                  <strong>{priorityLabel(finalPriority)}</strong>
                  <span>{finalPriority ?? "-"}</span>
                </div>
              )
              : (
                <label className="triage-priority-select">
                  <span>
                    간호사 초기분류
                  </span>

                  <select
                    value={selectedPriority}
                    onChange={(event) =>
                      setSelectedPriority(
                        event.target.value as TriagePriority | "",
                      )
                    }
                  >
                    <option value="">
                      우선순위를 선택하세요
                    </option>
                    <option value="EMERGENCY">
                      응급 (EMERGENCY)
                    </option>
                    <option value="URGENT">
                      긴급 (URGENT)
                    </option>
                    <option value="NON_EMERGENCY">
                      비응급 (NON_EMERGENCY)
                    </option>
                  </select>

                  <small>
                    FAST, 선별점수, LKW를 참고해 초기평가 우선순위를 선택합니다.
                  </small>
                </label>
              )
          }

          <div className="triage-assignment-divider" />

          <h3>
            {
              finalized
                ? "담당 신경과"
                : "담당 신경과 선택"
            }
          </h3>

          {
            finalized
              ? (
                <>

                  <p>
                    초기평가 완료 후 배정된 담당 의료진입니다.
                  </p>


                  <div className="triage-assignment-success">

                    <strong>
                      {
                        selectedClinician?.name ??
                        result?.assigned_neurologist?.name ??
                        "담당 의료진"
                      }
                    </strong>


                    <span>
                      담당 의료진 배정 완료
                    </span>

                  </div>

                </>
              )
              : (
                <>

                  <p>
                    {
                      departmentId
                        ? "활성 상태인 신경과 의료진을 선택해 주세요."
                        : "응답에 신경과 department_id가 없습니다."
                    }
                  </p>


                  <label>

                    <span>
                      담당 신경과
                    </span>


                    <select
                      value={
                        selectedUserId
                      }
                      disabled={
                        !departmentId ||
                        loadingClinicians
                      }
                      onChange={
                        (event) =>
                          setSelectedUserId(
                            event.target.value,
                          )
                      }
                    >

                      <option value="">
                        {
                          loadingClinicians
                            ? "의료진 조회 중..."
                            : clinicians.length
                              ? "담당 의료진을 선택하세요"
                              : "선택 가능한 의료진이 없습니다"
                        }
                      </option>


                      {
                        clinicians.map(
                          (clinician) => (
                            <option
                              key={
                                clinician.id
                              }
                              value={
                                clinician.user_id
                              }
                            >
                              {
                                clinician.name
                              }
                            </option>
                          ),
                        )
                      }

                    </select>

                  </label>

                </>
              )
          }


          {
            error && (
              <div
                className="triage-assignment-error"
                role="alert"
              >
                {
                  error
                }
              </div>
            )
          }

        </section>

      </div>


      {/* ====================================================
          Bottom Action
          ==================================================== */}

      <footer className="triage-wizard-actions triage-result-actions">

        {
          finalized
            ? (
              <>
                <div />

                <div>

                  <button
                    type="button"
                    className="triage-complete-button"
                    onClick={
                      onBack
                    }
                  >
                    목록으로
                  </button>

                </div>
              </>
            )
            : (
              <>

                <div>

                  <button
                    type="button"
                    className="triage-draft-button"
                    onClick={
                      onBack
                    }
                    disabled={
                      completing
                    }
                  >
                    이전
                  </button>

                </div>


                <div>

                  <button
                    type="button"
                    className="triage-complete-button"
                    disabled={
                      !selectedUserId ||
                      !selectedPriority ||
                      completing
                    }
                    onClick={
                      () =>
                        void handleComplete()
                    }
                  >
                    {
                      completing
                        ? "배정 중..."
                        : "평가 완료 및 담당의 배정"
                    }
                  </button>

                </div>

              </>
            )
        }

      </footer>


      {/* ====================================================
          평가 완료 팝업
          ==================================================== */}

      {
        showCompleteModal && (
          <div
            className="triage-complete-modal-backdrop"
            role="presentation"
          >

            <div
              className="triage-complete-modal"
              role="dialog"
              aria-modal="true"
              aria-labelledby="triage-complete-title"
            >

              <div className="triage-complete-modal-icon">
                ✓
              </div>


              <h3 id="triage-complete-title">
                초기평가가 완료되었습니다
              </h3>


              <p>
                초기평가와 담당 신경과 의료진
                배정이 완료되었습니다.
              </p>


              {
                selectedClinician && (
                  <div className="triage-complete-modal-doctor">

                    <span>
                      담당 신경과
                    </span>


                    <strong>
                      {
                        selectedClinician.name
                      }
                    </strong>

                  </div>
                )
              }


              <button
                type="button"
                className="triage-complete-modal-confirm"
                onClick={
                  onComplete
                }
              >
                확인
              </button>

            </div>

          </div>
        )
      }

    </section>
  );
}