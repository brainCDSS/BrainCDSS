import {
  useEffect,
  useState,
} from "react";

import {
  getAssessmentWorklist,
  startAssessment,
} from "./api";

import type {
  AssessmentWorklistItem,
  AssessmentWorklistResponse,
} from "./types";

import "./css/assessment_worklist.css";


/* =========================================================
   Assessment Worklist Props
   ---------------------------------------------------------
   Worklist에서 Triage를 시작할 때

   assessment_id
   encounter_id

   를 상위 화면(AppShell)에 전달한다.
   ========================================================= */

interface AssessmentWorklistProps {

  onOpenTriage?: (
    assessmentId: string,
    encounterId: string,
    readOnly?: boolean,
  ) => void;

}


/* =========================================================
   Assessment Worklist
   ---------------------------------------------------------
   간호사 초기평가 대기 Worklist 화면

   API

   GET
   /api/v1/assessments/worklist

   POST
   /api/v1/assessments

   흐름

   Worklist 항목 선택
        ↓
   assessment_id 존재?
        ↓
   YES → 기존 assessment_id 사용

   NO
        ↓
   encounter_id로 초기평가 생성
        ↓
   assessment_id 반환
        ↓
   Triage 화면으로 전달

   중요:
   patient_summary 상세 필드는
   Backend 계약 확정 전이므로
   임의 필드를 사용하지 않는다.
   ========================================================= */

export default function AssessmentWorklist({
  onOpenTriage,
}: AssessmentWorklistProps) {


  /* ========================================================
     1. Worklist 데이터
     ======================================================== */

  const [
    worklist,
    setWorklist,
  ] = useState<AssessmentWorklistResponse | null>(
    null,
  );


  /* ========================================================
     2. Loading 상태
     ======================================================== */

  const [
    loading,
    setLoading,
  ] = useState(true);


  /* ========================================================
     3. Worklist 조회 Error
     ======================================================== */

  const [
    error,
    setError,
  ] = useState<string | null>(
    null,
  );


  /* ========================================================
     4. Triage 시작 상태
     --------------------------------------------------------
     어떤 Encounter의 Assessment 생성 요청이
     진행 중인지 저장한다.
     ======================================================== */

  const [
    startingEncounterId,
    setStartingEncounterId,
  ] = useState<string | null>(
    null,
  );


  /* ========================================================
     5. Triage 시작 Error
     ======================================================== */

  const [
    startError,
    setStartError,
  ] = useState<string | null>(
    null,
  );

  const [activeTab, setActiveTab] = useState<"WAITING" | "COMPLETED">("WAITING");


  /* ========================================================
     6. Worklist 조회
     ======================================================== */

  useEffect(() => {

    /**
     * 컴포넌트가 화면에서 제거된 뒤
     * 비동기 응답이 돌아왔을 때
     * state를 변경하지 않도록 사용한다.
     */
    let active = true;


    async function loadWorklist() {

      try {

        setLoading(true);

        setError(null);


        /**
         * API-ASM-001
         *
         * GET
         * /api/v1/assessments/worklist
         */
        const response =
          await getAssessmentWorklist();


        if (!active) {
          return;
        }


        setWorklist(
          response,
        );

      } catch (requestError) {

        if (!active) {
          return;
        }


        console.error(
          "Assessment Worklist 조회 실패:",
          requestError,
        );


        setError(
          "Worklist를 불러오지 못했습니다.",
        );

      } finally {

        if (active) {

          setLoading(
            false,
          );

        }

      }

    }


    loadWorklist();


    return () => {

      active = false;

    };

  }, []);


  /* ========================================================
     7. Triage 열기
     --------------------------------------------------------

     CASE 1
     assessment_id가 이미 존재

     → 진행 중이던 Assessment이므로
       기존 assessment_id 사용


     CASE 2
     assessment_id가 null

     → 아직 초기평가가 만들어지지 않은 Encounter

     → POST /api/v1/assessments

     → assessment_id 생성

     → 생성된 ID를 Triage 화면으로 전달
     ======================================================== */

  async function handleOpenTriage(
    item: AssessmentWorklistItem,
  ) {

    setStartError(
      null,
    );


    /* -------------------------------------------------------
       이미 Assessment가 존재하는 경우
       ------------------------------------------------------- */

    if (item.assessment_id) {

      onOpenTriage?.(
        item.assessment_id,
        item.encounter_id,
      );

      return;

    }


    /* -------------------------------------------------------
       Assessment가 아직 없는 경우
       ------------------------------------------------------- */

    try {

      setStartingEncounterId(
        item.encounter_id,
      );


      /**
       * API-ASM-002
       *
       * POST
       * /api/v1/assessments
       *
       * Request
       *
       * {
       *   encounter_id: "..."
       * }
       */
      const response =
        await startAssessment({
          encounter_id:
            item.encounter_id,
        });


      /**
       * Backend가 반환한 assessment_id를
       * Triage 화면으로 전달한다.
       */
      onOpenTriage?.(
        response.assessment_id,
        item.encounter_id,
      );

    } catch (requestError) {

      console.error(
        "초기평가 시작 실패:",
        requestError,
      );


      setStartError(
        "초기평가를 시작하지 못했습니다.",
      );

    } finally {

      setStartingEncounterId(
        null,
      );

    }

  }


  /* ========================================================
     8. Loading
     ======================================================== */

  if (loading) {

    return (

      <div className="assessment-worklist">

        <div className="assessment-worklist-state">

          <div className="assessment-worklist-state-icon">
            …
          </div>


          <strong>
            Worklist를 불러오는 중입니다.
          </strong>


          <span>
            잠시만 기다려 주세요.
          </span>

        </div>

      </div>

    );

  }


  /* ========================================================
     9. Error
     ======================================================== */

  if (error) {

    return (

      <div className="assessment-worklist">

        <div className="assessment-worklist-state">

          <div className="assessment-worklist-state-icon">
            !
          </div>


          <strong>
            Worklist 조회에 실패했습니다.
          </strong>


          <span>
            {error}
          </span>

        </div>

      </div>

    );

  }


  /* ========================================================
     10. API 응답이 없는 경우
     ======================================================== */

  if (!worklist) {

    return (

      <div className="assessment-worklist">

        <div className="assessment-worklist-state">

          <div className="assessment-worklist-state-icon">
            —
          </div>


          <strong>
            Worklist 정보가 없습니다.
          </strong>


          <span>
            조회 결과를 확인할 수 없습니다.
          </span>

        </div>

      </div>

    );

  }

  const waitingItems = worklist.results.filter((item) => item.status !== "COMPLETED");
  const completedItems = worklist.results.filter((item) => item.status === "COMPLETED");
  const displayedItems = activeTab === "WAITING" ? waitingItems : completedItems;


  /* ========================================================
     11. Main 화면
     ======================================================== */

  return (

    <div className="assessment-worklist">


      {/* ===================================================
          화면 제목
          =================================================== */}

      <header className="assessment-worklist-page-heading">

        <span className="assessment-worklist-label">
          ASSESSMENT WORKLIST
        </span>


        <h1>
          접수 Worklist
        </h1>


        <p>
          초기평가 대기 환자를 확인하고
          Triage 업무를 진행합니다.
        </p>

      </header>


      {/* ===================================================
          Worklist Card
          =================================================== */}

      <section className="assessment-worklist-card">

        <div className="assessment-worklist-tabs" role="tablist" aria-label="초기평가 목록">
          <button type="button" role="tab" aria-selected={activeTab === "WAITING"} className={activeTab === "WAITING" ? "is-active" : ""} onClick={() => setActiveTab("WAITING")}>
            초기평가 대기 ({waitingItems.length})
          </button>
          <button type="button" role="tab" aria-selected={activeTab === "COMPLETED"} className={activeTab === "COMPLETED" ? "is-active" : ""} onClick={() => setActiveTab("COMPLETED")}>
            평가 완료 ({completedItems.length})
          </button>
        </div>


        {/* -------------------------------------------------
            Card Header
            ------------------------------------------------- */}

        <div className="assessment-worklist-card-header">

          <div>

            <h2>
              초기평가 대기
            </h2>


            <p>
              접수 후 초기평가가 필요한
              환자 목록입니다.
            </p>

          </div>


          {/* 전체 건수 */}

          <div className="assessment-worklist-count">

            <span>
              전체
            </span>


            <strong>
              {worklist.count}
            </strong>


            <span>
              건
            </span>

          </div>

        </div>


        {/* =================================================
            Triage 시작 오류
            ================================================= */}

        {startError && (

          <div className="assessment-worklist-state">

            <div className="assessment-worklist-state-icon">
              !
            </div>


            <strong>
              Triage 시작에 실패했습니다.
            </strong>


            <span>
              {startError}
            </span>

          </div>

        )}


        {/* =================================================
            Empty State
            ================================================= */}

        {displayedItems.length === 0 ? (

          <div className="assessment-worklist-empty">

            <div className="assessment-worklist-empty-icon">
              ✓
            </div>


            <strong>
              {activeTab === "WAITING"
                ? "현재 초기평가 대기 환자가 없습니다."
                : "완료된 초기평가를 조회할 수 없습니다."}
            </strong>

            <p>
              {activeTab === "WAITING"
                ? "새로운 환자가 접수되면 Worklist에 표시됩니다."
                : "현재 worklist API는 완료 Assessment를 반환하지 않습니다."}
            </p>

          </div>

        ) : (

          /* =================================================
             Worklist 데이터

             현재 확정된 필드만 사용한다.

             - encounter_id
             - assessment_id
             - status
             - triage_priority
             - created_at

             patient_summary 내부 필드는
             임의로 꺼내지 않는다.
             ================================================= */

          <div className="assessment-worklist-data">


            {displayedItems.map((item) => {

              const starting =
                startingEncounterId ===
                item.encounter_id;


              return (

                <div
                  key={item.encounter_id}
                  className="assessment-worklist-item"
                >

                  <div>

                    <strong>
                      Encounter
                    </strong>


                    <p>
                      {item.encounter_id}
                    </p>


                    <span>
                      상태: {item.status}
                    </span>

                  </div>


                  {activeTab === "COMPLETED" ? (
                    <button
                      type="button"
                      disabled={!item.assessment_id}
                      onClick={() => item.assessment_id && onOpenTriage?.(
                        item.assessment_id,
                        item.encounter_id,
                        true,
                      )}
                    >
                      초기평가 보기
                    </button>
                  ) : (
                    <button
                      type="button"
                      disabled={starting}
                      onClick={() => handleOpenTriage(item)}
                    >
                      {starting ? "시작 중..." : item.assessment_id ? "Triage 계속" : "Triage 시작"}
                    </button>
                  )}

                </div>

              );

            })}

          </div>

        )}

      </section>

    </div>

  );

}
