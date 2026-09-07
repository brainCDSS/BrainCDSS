import type {
  AssessmentDetailResponse,
} from "./types";

import "./css/triage_assessment.css";


interface TriageResultProps {

  result:
    AssessmentDetailResponse | null;

  onBack: () => void;

}


/* =========================================================
   Priority 화면 표시명
   ---------------------------------------------------------
   Backend 상태값을 화면용 한글로만 변환한다.

   임상 판단 로직이 아니다.
   ========================================================= */

function getPriorityLabel(
  priority: string | null,
) {

  switch (priority) {

    case "URGENT":
      return "긴급";

    case "EMERGENCY":
      return "응급";

    case "NON_EMERGENCY":
      return "비응급";

    default:
      return "—";

  }

}


export default function TriageResult({
  result,
  onBack,
}: TriageResultProps) {


  /* ========================================================
     Red Flag 항목

     Backend에서 is_red_flag=true로 반환한
     항목만 표시한다.
     ======================================================== */

  const redFlagItems =
    result?.items.filter(
      (item) =>
        item.is_red_flag === true,
    ) ?? [];


  return (

    <div className="triage-assessment">


      {/* ===================================================
          Header
          =================================================== */}

      <header className="triage-assessment__header">

        <div>

          <p className="triage-assessment__eyebrow">
            TRIAGE RESULT
          </p>


          <h1>
            Triage 결과 · 의사 지정
          </h1>


          <p>
            초기평가 결과를 확인하고
            담당 신경과 의사를 지정합니다.
          </p>

        </div>

      </header>


      {/* ===================================================
          평가 결과
          =================================================== */}

      <section className="triage-result-card">

        <div>

          <span className="triage-result-label">
            ASSESSMENT RESULT
          </span>


          <strong>
            초기평가 결과
          </strong>


          <p>
            점수와 처리 우선순위는
            서버에서 계산된 결과를 표시합니다.
          </p>

        </div>


        <div className="triage-result-values">

          <div>

            <span>
              Total Score
            </span>


            <strong>
              {result?.total_score ?? "—"}
            </strong>

          </div>


          <div>

            <span>
              Priority
            </span>


            <strong>
              {getPriorityLabel(
                result?.triage_priority ?? null,
              )}
            </strong>

          </div>

        </div>

      </section>


      {/* ===================================================
          1. 주요 위험항목
          =================================================== */}

      <section className="triage-assessment__section">

        <div className="triage-section-heading">

          <div className="triage-section-number">
            1
          </div>


          <div>

            <h2>
              주요 위험항목
            </h2>


            <p>
              초기평가에서 확인된
              Red Flag 항목을 표시합니다.
            </p>

          </div>

        </div>


        <div className="triage-question-list">

          {redFlagItems.length === 0 ? (

            <div className="triage-question-card">

              <div className="triage-question-content">

                <strong>
                  확인된 위험항목
                </strong>


                <span>
                  {result
                    ? "확인된 Red Flag 항목이 없습니다."
                    : "평가 결과 연동 정보가 없습니다."}
                </span>

              </div>

            </div>

          ) : (

            redFlagItems.map(
              (item) => (

                <div
                  key={
                    item.item_code
                  }

                  className="triage-question-card"
                >

                  <div className="triage-question-content">

                    <strong>
                      {item.item_code}
                    </strong>


                    <span>
                      Red Flag
                    </span>

                  </div>

                </div>

              ),
            )

          )}

        </div>

      </section>


      {/* ===================================================
          2. 담당 신경과 지정
          ---------------------------------------------------
          현재 NURSE가 사용할 수 있는
          담당 신경과 목록 API 계약이 확인되지 않았다.

          따라서 임의 의사 목록을 만들지 않는다.
          =================================================== */}

      <section className="triage-assessment__section">

        <div className="triage-section-heading">

          <div className="triage-section-number">
            2
          </div>


          <div>

            <h2>
              담당 신경과 지정
            </h2>


            <p>
              Triage 제출 전
              담당 신경과 의사를 선택합니다.
            </p>

          </div>

        </div>


        <label>

          <span>
            담당 신경과
          </span>


          <select
            defaultValue=""
            disabled
          >

            <option value="">
              담당 신경과 목록 API 확인 필요
            </option>

          </select>

        </label>

      </section>


      {/* ===================================================
          하단 Action
          =================================================== */}

      <div className="triage-assessment__actions">

        <button
          type="button"

          className="triage-draft-button"

          onClick={
            onBack
          }
        >
          이전
        </button>


        {/*
          completeAssessment API 함수 자체는 api.ts에 있음.

          하지만 담당 신경과 ID를 얻는
          NURSE용 목록 API가 확인되기 전에는
          임의 ID를 POST하지 않는다.
        */}

        <button
          type="button"

          className="triage-complete-button"

          disabled
        >
          Triage 제출
        </button>

      </div>

    </div>

  );

}