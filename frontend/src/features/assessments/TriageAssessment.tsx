import { useState } from "react";

import {
  getAssessmentDetail,
  updateAssessment,
} from "./api";

import type {
  AssessmentDetailResponse,
  AssessmentItem,
  UpdateAssessmentRequest,
} from "./types";

import TriageResult from "./TriageResult";

import "./css/triage_assessment.css";


/* =========================================================
   Props
   ---------------------------------------------------------
   Worklist → AppShell → TriageAssessment

   흐름으로 전달되는 현재 평가 정보
   ========================================================= */

interface TriageAssessmentProps {
  assessmentId?: string | null;
  encounterId?: string | null;
}


/* =========================================================
   정상 / 이상 선택값
   ========================================================= */

type AssessmentChoice =
  | ""
  | "NORMAL"
  | "ABNORMAL";


/* =========================================================
   위험 문진 문항

   실제 문항 / item_code는
   Backend Rule 계약 후 연결한다.
   ========================================================= */

interface RiskQuestion {
  id: string;
  itemCode: string;
  title: string;
  description?: string;
}


/**
 * 현재 Rule API 미연동
 */
const riskQuestions: RiskQuestion[] = [];


/* =========================================================
   Triage Assessment
   ========================================================= */

export default function TriageAssessment({
  assessmentId,
  encounterId,
}: TriageAssessmentProps) {


  /* ========================================================
     결과 화면 표시 여부
     ======================================================== */

  const [
    showResult,
    setShowResult,
  ] = useState(false);


  /* ========================================================
     Backend에서 조회한 Assessment 결과
     ======================================================== */

  const [
    assessmentResult,
    setAssessmentResult,
  ] = useState<AssessmentDetailResponse | null>(
    null,
  );


  /* ========================================================
     API 처리 중 상태
     ======================================================== */

  const [
    saving,
    setSaving,
  ] = useState(false);


  const [
    apiError,
    setApiError,
  ] = useState<string | null>(
    null,
  );


  /* ========================================================
     1. 증상 발생 정보
     ======================================================== */

  const [
    onsetAt,
    setOnsetAt,
  ] = useState("");


  const [
    lkwAt,
    setLkwAt,
  ] = useState("");


  /* ========================================================
     2. FAST
     ======================================================== */

  const [
    fastFace,
    setFastFace,
  ] = useState<AssessmentChoice>("");


  const [
    fastArm,
    setFastArm,
  ] = useState<AssessmentChoice>("");


  const [
    fastSpeech,
    setFastSpeech,
  ] = useState<AssessmentChoice>("");


  /* ========================================================
     3. 의식 / 신경학적 상태
     ======================================================== */

  const [
    consciousnessState,
    setConsciousnessState,
  ] = useState<AssessmentChoice>("");


  /* ========================================================
     4. Vital
     ======================================================== */

  const [
    bpSys,
    setBpSys,
  ] = useState("");


  const [
    bpDia,
    setBpDia,
  ] = useState("");


  const [
    heartRate,
    setHeartRate,
  ] = useState("");


  const [
    temperature,
    setTemperature,
  ] = useState("");


  /* ========================================================
     5. 위험 문진
     ======================================================== */

  const [
    riskAnswers,
    setRiskAnswers,
  ] = useState<
    Record<string, AssessmentChoice>
  >({});


  /* ========================================================
     6. 추가 메모
     ======================================================== */

  const [
    symptomNote,
    setSymptomNote,
  ] = useState("");


  /* ========================================================
     날짜 입력 제한
     --------------------------------------------------------
     YYYY-MM-DDTHH:mm

     연도가 4자리를 넘어가는 입력을 막는다.
     ======================================================== */

  function handleDateTimeChange(
    value: string,
    setter: (value: string) => void,
  ) {

    if (value === "") {
      setter("");
      return;
    }


    const validDateTimePattern =
      /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}$/;


    if (!validDateTimePattern.test(value)) {
      return;
    }


    setter(value);

  }


  /* ========================================================
     FAST 응답 개수

     임상 점수가 아니다.
     화면 진행 표시용이다.
     ======================================================== */

  const completedFastCount = [
    fastFace,
    fastArm,
    fastSpeech,
  ].filter(Boolean).length;


  /* ========================================================
     위험 문진 응답
     ======================================================== */

  function handleRiskAnswer(
    itemCode: string,
    value: AssessmentChoice,
  ) {

    setRiskAnswers(
      (previous) => ({
        ...previous,
        [itemCode]: value,
      }),
    );

  }


  /* ========================================================
     PATCH Payload 생성
     --------------------------------------------------------

     중요:

     현재 문서에서 확실하게 확인된 item_code만
     실제 API Payload에 넣는다.

     확인된 코드:
     - FAST_FACE
     - FAST_ARM
     - BP_SYS
     - HEART_RATE

     아직 정확한 코드가 확인되지 않은:
     - Speech
     - 의식상태
     - 이완기혈압
     - 체온

     은 UI 상태로만 유지한다.

     프론트에서 임의 item_code를 만들지 않는다.
     ======================================================== */

  function buildUpdatePayload():
  UpdateAssessmentRequest {

    const items: AssessmentItem[] = [];


    /* FAST - Face */

    if (fastFace !== "") {

      items.push({
        item_code: "FAST_FACE",
        value_text: fastFace,
      });

    }


    /* FAST - Arm */

    if (fastArm !== "") {

      items.push({
        item_code: "FAST_ARM",
        value_text: fastArm,
      });

    }


    /* 수축기 혈압 */

    if (bpSys !== "") {

      items.push({
        item_code: "BP_SYS",
        value_numeric:
          Number(bpSys),
        unit: "mmHg",
      });

    }


    /* 심박수 */

    if (heartRate !== "") {

      items.push({
        item_code: "HEART_RATE",
        value_numeric:
          Number(heartRate),
        unit: "bpm",
      });

    }


    /* Backend Rule에서 받은 위험 문진 */

    riskQuestions.forEach(
      (question) => {

        const value =
          riskAnswers[
            question.itemCode
          ];


        if (!value) {
          return;
        }


        items.push({
          item_code:
            question.itemCode,

          value_text:
            value,
        });

      },
    );


    return {

      onset_at:
        onsetAt
          ? new Date(
              onsetAt,
            ).toISOString()
          : null,

      lkw_at:
        lkwAt
          ? new Date(
              lkwAt,
            ).toISOString()
          : null,

      symptom_note:
        symptomNote,

      items,

    };

  }


  /* ========================================================
     임시저장
     --------------------------------------------------------

     PATCH
     /api/v1/assessments/{assessment_id}
     ======================================================== */

  async function handleDraftCheck() {

    if (!assessmentId) {

      console.warn(
        "Assessment ID가 없어 임시저장을 호출할 수 없습니다.",
      );

      setApiError(
        "Worklist에서 초기평가를 선택한 뒤 다시 시도해 주세요.",
      );

      return;

    }


    try {

      setSaving(
        true,
      );

      setApiError(
        null,
      );


      const payload =
        buildUpdatePayload();


      const response =
        await updateAssessment(
          assessmentId,
          payload,
        );


      console.log(
        "Triage 임시저장 완료:",
        {
          assessmentId,
          encounterId,
          response,
        },
      );

    } catch (requestError) {

      console.error(
        "Triage 임시저장 실패:",
        requestError,
      );


      setApiError(
        "초기평가 임시저장에 실패했습니다.",
      );

    } finally {

      setSaving(
        false,
      );

    }

  }


  /* ========================================================
     다음
     --------------------------------------------------------

     1. 현재 내용 PATCH
     2. Assessment GET
     3. 결과 화면 표시
     ======================================================== */

  async function handleNextCheck() {

    /*
     * Sidebar에서 Triage를 직접 열어
     * assessmentId가 없는 경우
     *
     * UI 확인은 가능하도록 결과 화면은 이동한다.
     */
    if (!assessmentId) {

      setAssessmentResult(
        null,
      );

      setShowResult(
        true,
      );

      return;

    }


    try {

      setSaving(
        true,
      );

      setApiError(
        null,
      );


      /* -----------------------------------------------
         1. 현재 작성 내용 저장
         ----------------------------------------------- */

      const payload =
        buildUpdatePayload();


      await updateAssessment(
        assessmentId,
        payload,
      );


      /* -----------------------------------------------
         2. Backend 결과 조회

         GET
         /api/v1/assessments/{assessment_id}
         ----------------------------------------------- */

      const response =
        await getAssessmentDetail(
          assessmentId,
        );


      setAssessmentResult(
        response,
      );


      console.log(
        "Triage 결과 조회 완료:",
        response,
      );


      /* -----------------------------------------------
         3. 결과 화면
         ----------------------------------------------- */

      setShowResult(
        true,
      );

    } catch (requestError) {

      console.error(
        "Triage 결과 조회 실패:",
        requestError,
      );


      setApiError(
        "초기평가 결과를 불러오지 못했습니다.",
      );

    } finally {

      setSaving(
        false,
      );

    }

  }


  /* ========================================================
     결과 화면
     ======================================================== */

  if (showResult) {

    return (
      <TriageResult
        result={
          assessmentResult
        }

        onBack={() =>
          setShowResult(
            false,
          )
        }
      />
    );

  }


  /* ========================================================
     Main
     ======================================================== */

  return (

    <div className="triage-assessment">


      {/* ===================================================
          Header
          =================================================== */}

      <header className="triage-assessment__header">

        <div>

          <p className="triage-assessment__eyebrow">
            INITIAL ASSESSMENT
          </p>


          <h1>
            초기평가 / Triage
          </h1>


          <p>
            환자의 초기 상태를 항목별로 확인하고
            평가 결과를 기록합니다.
          </p>

        </div>

      </header>


      {/* ===================================================
          API Error
          =================================================== */}

      {apiError && (

        <div className="triage-question-card">

          <div className="triage-question-content">

            <strong>
              요청 처리 실패
            </strong>

            <span>
              {apiError}
            </span>

          </div>

        </div>

      )}


      {/* ===================================================
          1. 증상 발생 정보
          =================================================== */}

      <section className="triage-assessment__section">

        <div className="triage-section-heading">

          <div className="triage-section-number">
            1
          </div>


          <div>

            <h2>
              증상 발생 정보
            </h2>


            <p>
              증상 발생 시각과 Last Known Well을 확인합니다.
            </p>

          </div>

        </div>


        <div
          className="
            triage-assessment__grid
            triage-grid-two
          "
        >

          <label>

            <span>
              증상 발생 시각
            </span>


            <input
              type="datetime-local"

              min="1900-01-01T00:00"
              max="2100-12-31T23:59"

              value={
                onsetAt
              }

              onChange={(event) =>
                handleDateTimeChange(
                  event.target.value,
                  setOnsetAt,
                )
              }
            />

          </label>


          <label>

            <span>
              Last Known Well (LKW)
            </span>


            <input
              type="datetime-local"

              min="1900-01-01T00:00"
              max="2100-12-31T23:59"

              value={
                lkwAt
              }

              onChange={(event) =>
                handleDateTimeChange(
                  event.target.value,
                  setLkwAt,
                )
              }
            />

          </label>

        </div>

      </section>


      {/* ===================================================
          2. FAST
          =================================================== */}

      <section className="triage-assessment__section">

        <div className="triage-section-heading">

          <div className="triage-section-number">
            2
          </div>


          <div className="triage-section-heading-text">

            <h2>
              FAST 평가
            </h2>


            <p>
              각 항목을 확인한 뒤 정상 또는 이상을 선택합니다.
            </p>

          </div>


          <div className="triage-section-progress">
            {completedFastCount} / 3 응답
          </div>

        </div>


        <div className="triage-question-list">


          {/* Face */}

          <div className="triage-question-card">

            <div className="triage-question-content">

              <strong>
                Face
              </strong>

              <span>
                안면 비대칭 여부를 확인합니다.
              </span>

            </div>


            <div className="triage-choice-group">

              <button
                type="button"

                className={
                  fastFace === "NORMAL"
                    ? "triage-choice active"
                    : "triage-choice"
                }

                onClick={() =>
                  setFastFace(
                    "NORMAL",
                  )
                }
              >
                정상
              </button>


              <button
                type="button"

                className={
                  fastFace === "ABNORMAL"
                    ? "triage-choice active abnormal"
                    : "triage-choice"
                }

                onClick={() =>
                  setFastFace(
                    "ABNORMAL",
                  )
                }
              >
                이상
              </button>

            </div>

          </div>


          {/* Arm */}

          <div className="triage-question-card">

            <div className="triage-question-content">

              <strong>
                Arm
              </strong>

              <span>
                상지 움직임 상태를 확인합니다.
              </span>

            </div>


            <div className="triage-choice-group">

              <button
                type="button"

                className={
                  fastArm === "NORMAL"
                    ? "triage-choice active"
                    : "triage-choice"
                }

                onClick={() =>
                  setFastArm(
                    "NORMAL",
                  )
                }
              >
                정상
              </button>


              <button
                type="button"

                className={
                  fastArm === "ABNORMAL"
                    ? "triage-choice active abnormal"
                    : "triage-choice"
                }

                onClick={() =>
                  setFastArm(
                    "ABNORMAL",
                  )
                }
              >
                이상
              </button>

            </div>

          </div>


          {/* Speech */}

          <div className="triage-question-card">

            <div className="triage-question-content">

              <strong>
                Speech
              </strong>

              <span>
                언어 및 발화 상태를 확인합니다.
              </span>

            </div>


            <div className="triage-choice-group">

              <button
                type="button"

                className={
                  fastSpeech === "NORMAL"
                    ? "triage-choice active"
                    : "triage-choice"
                }

                onClick={() =>
                  setFastSpeech(
                    "NORMAL",
                  )
                }
              >
                정상
              </button>


              <button
                type="button"

                className={
                  fastSpeech === "ABNORMAL"
                    ? "triage-choice active abnormal"
                    : "triage-choice"
                }

                onClick={() =>
                  setFastSpeech(
                    "ABNORMAL",
                  )
                }
              >
                이상
              </button>

            </div>

          </div>

        </div>

      </section>


      {/* ===================================================
          3. 의식 / 신경학적 상태
          =================================================== */}

      <section className="triage-assessment__section">

        <div className="triage-section-heading">

          <div className="triage-section-number">
            3
          </div>


          <div>

            <h2>
              의식 / 신경학적 상태
            </h2>


            <p>
              환자의 초기 의식상태를 확인합니다.
            </p>

          </div>

        </div>


        <div className="triage-question-list">

          <div className="triage-question-card">

            <div className="triage-question-content">

              <strong>
                의식상태
              </strong>


              <span>
                현재 환자의 의식 및 반응 상태를 확인합니다.
              </span>

            </div>


            <div className="triage-choice-group">

              <button
                type="button"

                className={
                  consciousnessState === "NORMAL"
                    ? "triage-choice active"
                    : "triage-choice"
                }

                onClick={() =>
                  setConsciousnessState(
                    "NORMAL",
                  )
                }
              >
                정상
              </button>


              <button
                type="button"

                className={
                  consciousnessState === "ABNORMAL"
                    ? "triage-choice active abnormal"
                    : "triage-choice"
                }

                onClick={() =>
                  setConsciousnessState(
                    "ABNORMAL",
                  )
                }
              >
                이상
              </button>

            </div>

          </div>

        </div>

      </section>


      {/* ===================================================
          4. Vital Sign
          =================================================== */}

      <section className="triage-assessment__section">

        <div className="triage-section-heading">

          <div className="triage-section-number">
            4
          </div>


          <div>

            <h2>
              Vital Sign
            </h2>


            <p>
              초기 측정된 생체징후를 입력합니다.
            </p>

          </div>

        </div>


        <div className="triage-assessment__grid">


          {/* 수축기 혈압 */}

          <label>

            <span>
              수축기 혈압
            </span>


            <div className="triage-input-with-unit">

              <input
                type="number"

                value={
                  bpSys
                }

                onChange={(event) =>
                  setBpSys(
                    event.target.value,
                  )
                }
              />


              <span>
                mmHg
              </span>

            </div>

          </label>


          {/* 이완기 혈압 */}

          <label>

            <span>
              이완기 혈압
            </span>


            <div className="triage-input-with-unit">

              <input
                type="number"

                value={
                  bpDia
                }

                onChange={(event) =>
                  setBpDia(
                    event.target.value,
                  )
                }
              />


              <span>
                mmHg
              </span>

            </div>

          </label>


          {/* 심박수 */}

          <label>

            <span>
              심박수
            </span>


            <div className="triage-input-with-unit">

              <input
                type="number"

                value={
                  heartRate
                }

                onChange={(event) =>
                  setHeartRate(
                    event.target.value,
                  )
                }
              />


              <span>
                bpm
              </span>

            </div>

          </label>


          {/* 체온 */}

          <label>

            <span>
              체온
            </span>


            <div className="triage-input-with-unit">

              <input
                type="number"

                step="0.1"

                value={
                  temperature
                }

                onChange={(event) =>
                  setTemperature(
                    event.target.value,
                  )
                }
              />


              <span>
                ℃
              </span>

            </div>

          </label>

        </div>

      </section>


      {/* ===================================================
          5. 주요 증상 / 위험 문진
          =================================================== */}

      <section className="triage-assessment__section">

        <div className="triage-section-heading">

          <div className="triage-section-number">
            5
          </div>


          <div>

            <h2>
              주요 증상 / 위험 문진
            </h2>


            <p>
              주요 증상과 위험 문진 항목을 확인합니다.
            </p>

          </div>

        </div>


        <div className="triage-question-list">

          {riskQuestions.length === 0 ? (

            <div className="triage-question-card">

              <div className="triage-question-content">

                <strong>
                  위험 문진 항목
                </strong>


                <span>
                  Triage Rule 연동 후
                  체크리스트 문항이 표시됩니다.
                </span>

              </div>

            </div>

          ) : (

            riskQuestions.map(
              (question) => {

                const answer =
                  riskAnswers[
                    question.itemCode
                  ] ?? "";


                return (

                  <div
                    key={
                      question.id
                    }

                    className="triage-question-card"
                  >

                    <div className="triage-question-content">

                      <strong>
                        {question.title}
                      </strong>


                      {question.description && (

                        <span>
                          {question.description}
                        </span>

                      )}

                    </div>


                    <div className="triage-choice-group">

                      <button
                        type="button"

                        className={
                          answer === "NORMAL"
                            ? "triage-choice active"
                            : "triage-choice"
                        }

                        onClick={() =>
                          handleRiskAnswer(
                            question.itemCode,
                            "NORMAL",
                          )
                        }
                      >
                        정상
                      </button>


                      <button
                        type="button"

                        className={
                          answer === "ABNORMAL"
                            ? "triage-choice active abnormal"
                            : "triage-choice"
                        }

                        onClick={() =>
                          handleRiskAnswer(
                            question.itemCode,
                            "ABNORMAL",
                          )
                        }
                      >
                        이상
                      </button>

                    </div>

                  </div>

                );

              },
            )

          )}

        </div>

      </section>


      {/* ===================================================
          6. 추가 메모
          =================================================== */}

      <section className="triage-assessment__section">

        <div className="triage-section-heading">

          <div className="triage-section-number">
            6
          </div>


          <div>

            <h2>
              추가 메모
            </h2>


            <p>
              체크리스트 외에 추가로 확인된 증상이나
              특이사항을 기록합니다.
            </p>

          </div>

        </div>


        <textarea
          value={
            symptomNote
          }

          onChange={(event) =>
            setSymptomNote(
              event.target.value,
            )
          }

          placeholder="환자의 추가 증상 및 특이사항을 입력하세요."

          rows={5}
        />

      </section>


      {/* ===================================================
          하단 Action
          =================================================== */}

      <div className="triage-assessment__actions">

        <button
          type="button"

          className="triage-draft-button"

          disabled={
            saving
          }

          onClick={
            handleDraftCheck
          }
        >
          {saving
            ? "저장 중..."
            : "임시저장"}
        </button>


        <button
          type="button"

          className="triage-complete-button"

          disabled={
            saving
          }

          onClick={
            handleNextCheck
          }
        >
          {saving
            ? "처리 중..."
            : "다음"}
        </button>

      </div>

    </div>

  );

}