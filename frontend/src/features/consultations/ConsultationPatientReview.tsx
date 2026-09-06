import {
  useEffect,
  useState,
} from "react";

import {
  getConsultationDetail,
} from "./api";

import type {
  ConsultationListItem,
  ConsultationPriority,
  ConsultationStatus,
  ConsultationType,
} from "./types";

import "./css/consultation_patient_review.css";


/* =========================================================
   Props
   ========================================================= */

interface ConsultationPatientReviewProps {
  consultationId: string;

  onBack?: () => void;

  onOpenDetail?: (
    consultationId: string,
  ) => void;
}


/* =========================================================
   환자 데이터 Tab
   ========================================================= */

type PatientReviewTab =
  | "clinical"
  | "imaging"
  | "ai"
  | "radiology"
  | "cdss";


/* =========================================================
   화면 표시 Label
   ========================================================= */

const STATUS_LABEL: Record<
  ConsultationStatus,
  string
> = {
  REQUESTED: "요청됨",
  ACCEPTED: "수락됨",
  IN_PROGRESS: "검토 중",
  RESPONDED: "회신 완료",
  CLOSED: "종결",
  REJECTED: "거절",
  CANCELLED: "취소",
  EXPIRED: "만료",
};


const PRIORITY_LABEL: Record<
  ConsultationPriority,
  string
> = {
  STAT: "긴급",
  URGENT: "응급",
  ROUTINE: "일반",
};


const TYPE_LABEL: Record<
  ConsultationType,
  string
> = {
  RADIOLOGY: "영상의학과",
  NEUROSURGERY: "신경외과",
};


/* =========================================================
   협진 진행 단계
   ========================================================= */

const CONSULTATION_PROGRESS_STEPS = [
  {
    key: "REQUESTED",
    label: "협진 요청",
  },
  {
    key: "ACCEPTED",
    label: "수락",
  },
  {
    key: "IN_PROGRESS",
    label: "검토 중",
  },
  {
    key: "RESPONDED",
    label: "회신 완료",
  },
] as const;


/* =========================================================
   현재 진행 단계
   ========================================================= */

function getConsultationProgressIndex(
  status: ConsultationStatus,
): number {

  if (status === "REQUESTED") {
    return 0;
  }

  if (status === "ACCEPTED") {
    return 1;
  }

  if (status === "IN_PROGRESS") {
    return 2;
  }

  if (
    status === "RESPONDED" ||
    status === "CLOSED"
  ) {
    return 3;
  }

  return -1;
}


/* =========================================================
   날짜 표시
   ========================================================= */

function formatProgressTime(
  value: string | null,
): string {

  if (!value) {
    return "";
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


  const month =
    String(
      date.getMonth() + 1,
    ).padStart(
      2,
      "0",
    );


  const day =
    String(
      date.getDate(),
    ).padStart(
      2,
      "0",
    );


  const hour =
    String(
      date.getHours(),
    ).padStart(
      2,
      "0",
    );


  const minute =
    String(
      date.getMinutes(),
    ).padStart(
      2,
      "0",
    );


  return `${month}.${day} ${hour}:${minute}`;
}


/* =========================================================
   성별 표시
   ========================================================= */

function formatSex(
  value: string | null,
): string {

  if (value === "M") {
    return "남";
  }

  if (value === "F") {
    return "여";
  }

  return value || "—";
}


/* =========================================================
   WEB-NS-003
   Consultation Patient Review
   ========================================================= */

export default function ConsultationPatientReview({
  consultationId,
  onBack,
  onOpenDetail,
}: ConsultationPatientReviewProps) {


  /* ========================================================
     협진 데이터
     ======================================================== */

  const [
    consultation,
    setConsultation,
  ] = useState<ConsultationListItem | null>(
    null,
  );


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
    activeTab,
    setActiveTab,
  ] = useState<PatientReviewTab>(
    "clinical",
  );


  /* ========================================================
     CON-003
     ======================================================== */

  useEffect(() => {

    let cancelled = false;


    async function loadConsultation() {

      try {

        setLoading(true);
        setError(null);


        const response =
          await getConsultationDetail(
            consultationId,
          );


        if (!cancelled) {

          setConsultation(
            response,
          );

        }

      } catch {

        if (!cancelled) {

          setError(
            "협진 상세 정보를 불러오지 못했습니다.",
          );

        }

      } finally {

        if (!cancelled) {

          setLoading(false);

        }

      }

    }


    void loadConsultation();


    return () => {

      cancelled = true;

    };

  }, [
    consultationId,
  ]);


  /* ========================================================
     Loading
     ======================================================== */

  if (loading) {

    return (
      <section className="consultation-review">

        <div className="consultation-review__message">
          협진 정보를 불러오는 중입니다.
        </div>

      </section>
    );

  }


  /* ========================================================
     Error
     ======================================================== */

  if (
    error ||
    !consultation
  ) {

    return (
      <section className="consultation-review">

        <div
          className="
            consultation-review__message
            consultation-review__message--error
          "
        >
          {
            error ||
            "협진 정보를 확인할 수 없습니다."
          }
        </div>

      </section>
    );

  }


  const patient =
    consultation.patient_summary;


  const progressIndex =
    getConsultationProgressIndex(
      consultation.status,
    );


  const isExceptionalStatus =
    consultation.status === "REJECTED" ||
    consultation.status === "CANCELLED" ||
    consultation.status === "EXPIRED";


  const progressTimes: Array<
    string | null
  > = [
    consultation.requested_at,
    consultation.accepted_at,
    consultation.started_at,
    consultation.completed_at,
  ];


  /* ========================================================
     환자 데이터 Tab Content
     ======================================================== */

  function renderPatientData() {


    if (activeTab === "clinical") {

      return (
        <div className="consultation-review__data-content">

          <div className="consultation-review__data-title">

            <span>
              +
            </span>

            <div>

              <strong>
                임상 정보
              </strong>

              <small>
                Triage · Vital · Lab
              </small>

            </div>

          </div>


          <div className="consultation-review__pending">

            <strong>
              임상 정보 API 연동 예정
            </strong>

            <span>
              Triage, Vital, Lab 등 환자의 임상 정보가
              이 영역에 표시됩니다.
            </span>

          </div>

        </div>
      );

    }


    if (activeTab === "imaging") {

      return (
        <div className="consultation-review__data-content">

          <div className="consultation-review__data-title">

            <span>
              ◫
            </span>

            <div>

              <strong>
                PACS 원본 영상
              </strong>

              <small>
                CT · MRI · MRA
              </small>

            </div>

          </div>


          <div className="consultation-review__pending">

            <strong>
              Imaging API 연동 예정
            </strong>

            <span>
              원본 영상 및 PACS Viewer 연결 영역입니다.
            </span>

          </div>

        </div>
      );

    }


    if (activeTab === "ai") {

      return (
        <div className="consultation-review__data-content">

          <div className="consultation-review__data-title">

            <span>
              AI
            </span>

            <div>

              <strong>
                AI 분석 결과
              </strong>

              <small>
                AI · XAI
              </small>

            </div>

          </div>


          <div className="consultation-review__pending">

            <strong>
              AI 분석 API 연동 예정
            </strong>

            <span>
              AI 분석 결과 및 XAI 근거 정보가
              이 영역에 표시됩니다.
            </span>

          </div>

        </div>
      );

    }


    if (activeTab === "radiology") {

      return (
        <div className="consultation-review__data-content">

          <div className="consultation-review__data-title">

            <span>
              R
            </span>

            <div>

              <strong>
                최종 판독
              </strong>

              <small>
                Final Radiology Report
              </small>

            </div>

          </div>


          <div className="consultation-review__pending">

            <strong>
              판독 API 연동 예정
            </strong>

            <span>
              영상의학과 Final 판독 결과가
              이 영역에 표시됩니다.
            </span>

          </div>

        </div>
      );

    }


    return (
      <div className="consultation-review__data-content">

        <div className="consultation-review__data-title">

          <span>
            C
          </span>

          <div>

            <strong>
              CDSS 결과
            </strong>

            <small>
              Risk · Alert · Rule
            </small>

          </div>

        </div>


        <div className="consultation-review__pending">

          <strong>
            CDSS API 연동 예정
          </strong>

          <span>
            CDSS 위험도, Alert 및 적용 Rule 근거가
            이 영역에 표시됩니다.
          </span>

        </div>

      </div>
    );

  }


  /* ========================================================
     Render
     ======================================================== */

  return (
    <section className="consultation-review">


      {/* =====================================================
          PAGE HEADER
          ===================================================== */}

      <header className="consultation-review__header">

        <div>

          <span className="consultation-review__eyebrow">
            CONSULTATION REVIEW
          </span>

          <h1>
            협진 Patient Review
          </h1>

          <p>
            협진 요청과 환자 정보를 함께 검토합니다.
          </p>

        </div>


        {onBack && (

          <button
            type="button"
            className="consultation-review__back-button"
            onClick={
              onBack
            }
          >
            ← 목록으로
          </button>

        )}

      </header>


      {/* =====================================================
          PATIENT SUMMARY
          ===================================================== */}

      <section className="consultation-review__patient-card">


        <div className="consultation-review__patient-main">

          <span className="consultation-review__section-label">
            PATIENT
          </span>


          <div className="consultation-review__patient-name">

            <strong>
              {
                patient.name
              }
            </strong>

            <span>
              {
                patient.patient_no
              }
            </span>

          </div>


          <div className="consultation-review__patient-meta">

            <span>
              {
                patient.birth_date ||
                "생년월일 —"
              }
            </span>

            <span>
              {
                patient.estimated_age !== null
                  ? `${patient.estimated_age}세`
                  : "연령 —"
              }
            </span>

            <span>
              {
                formatSex(
                  patient.sex,
                )
              }
            </span>

            <span>
              {
                consultation.encounter_id
              }
            </span>

          </div>

        </div>


        <div className="consultation-review__patient-summary">


          <div className="consultation-review__patient-priority">

            <div
              className={
                `consultation-review__priority consultation-review__priority--${consultation.priority.toLowerCase()}`
              }
            >
              {
                PRIORITY_LABEL[
                  consultation.priority
                ]
              }
            </div>

          </div>


          <div className="consultation-review__patient-field">

            <span>
              협진 상태
            </span>

            <strong>
              {
                consultation.ui_status ||
                STATUS_LABEL[
                  consultation.status
                ]
              }
            </strong>

          </div>


          <div className="consultation-review__patient-field">

            <span>
              협진 유형
            </span>

            <strong>
              {
                TYPE_LABEL[
                  consultation.type
                ]
              }
            </strong>

          </div>

        </div>

      </section>


      {/* =====================================================
          CONSULTATION REQUEST
          ===================================================== */}

      <section className="consultation-review__request-card">


        <div className="consultation-review__panel-header">

          <div className="consultation-review__panel-title">

            <span className="consultation-review__panel-icon">
              ↔
            </span>

            <h2>
              협진 요청 정보
            </h2>

          </div>


          <span className="consultation-review__consultation-id">
            {
              consultation.consultation_id
            }
          </span>

        </div>


        {/* ===================================================
            요청 의료진 | 진행 상태 | 배정 의료진
            =================================================== */}

        <div className="consultation-review__request-overview">


          {/* 요청 의료진 */}

          <div
            className="
              consultation-review__clinician-card
              consultation-review__clinician-card--requester
            "
          >

            <div className="consultation-review__clinician-avatar">

              <span className="consultation-review__avatar-head" />

              <span className="consultation-review__avatar-body" />

            </div>


            <div className="consultation-review__clinician">

            <span>
                요청 의료진
            </span>

            <div className="consultation-review__clinician-main">

                <strong>
                {consultation.requested_by.name}
                </strong>

                <span className="consultation-review__clinician-divider">
                |
                </span>

                <small>
                {consultation.requested_by.department}
                </small>

                </div>
            </div>

          </div>


          {/* =================================================
              진행 상태
              ================================================= */}

          <div className="consultation-review__progress">

            <div className="consultation-review__progress-header">

              <strong>
                진행 상태
              </strong>


              {isExceptionalStatus && (

                <span className="consultation-review__progress-exception">
                  {
                    STATUS_LABEL[
                      consultation.status
                    ]
                  }
                </span>

              )}

            </div>


            {!isExceptionalStatus && (

              <div className="consultation-review__progress-steps">

                {CONSULTATION_PROGRESS_STEPS.map(
                  (
                    step,
                    index,
                  ) => {

                    const completed =
                      index < progressIndex;

                    const current =
                      index === progressIndex;

                    const stepTime =
                      progressTimes[
                        index
                      ];


                    return (

                      <div
                        key={
                          step.key
                        }
                        className={
                          [
                            "consultation-review__progress-step",

                            completed
                              ? "completed"
                              : "",

                            current
                              ? "current"
                              : "",
                          ]
                            .filter(Boolean)
                            .join(" ")
                        }
                      >

                        <div className="consultation-review__progress-track">

                          <span className="consultation-review__progress-number">
                            {
                              index + 1
                            }
                          </span>


                          {
                            index <
                            CONSULTATION_PROGRESS_STEPS.length - 1 && (

                              <span className="consultation-review__progress-line" />

                            )
                          }

                        </div>


                        <div className="consultation-review__progress-label">

                          <div className="consultation-review__progress-name">

                            <strong>
                              {
                                step.label
                              }
                            </strong>


                            {current && (

                              <span>
                                현재
                              </span>

                            )}

                          </div>


                          {stepTime && (

                            <small className="consultation-review__progress-time">
                              {
                                formatProgressTime(
                                  stepTime,
                                )
                              }
                            </small>

                          )}

                        </div>

                      </div>

                    );

                  },
                )}

              </div>

            )}

          </div>


          {/* 배정 의료진 */}

          <div
            className="
              consultation-review__clinician-card
              consultation-review__clinician-card--assignee
            "
          >

            <div className="consultation-review__clinician-avatar">

              <span className="consultation-review__avatar-head" />

              <span className="consultation-review__avatar-body" />

            </div>


            <div className="
                consultation-review__clinician
                consultation-review__clinician--assignee
            "
            >

            <span>
                배정 의료진
            </span>

            <div className="consultation-review__clinician-main">

                <strong>
                {
                    consultation.assigned_to?.name ||
                    "미배정"
                }
                </strong>

                <span className="consultation-review__clinician-divider">
                |
                </span>

                <small>
                {
                    consultation.assigned_to?.department ||
                    "—"
                }
                </small>

            </div>

            </div>

          </div>

        </div>


        {/* ===================================================
            협진 요청 사유
            =================================================== */}

        <div className="consultation-review__reason">

          <div className="consultation-review__reason-title">

            <strong>
              협진 요청 사유
            </strong>

          </div>


          <div className="consultation-review__reason-content">
            API 필드 연동 예정
          </div>

        </div>

      </section>


      {/* =====================================================
          LOWER WORKSPACE
          ===================================================== */}

      <div className="consultation-review__workspace">


        {/* ===================================================
            환자 데이터
            =================================================== */}

        <section className="consultation-review__patient-data">

          <div className="consultation-review__panel-title">

            <span className="consultation-review__panel-icon">
              +
            </span>

            <h2>
              환자 데이터
            </h2>

          </div>


          <div
            className="consultation-review__tabs"
            role="tablist"
            aria-label="환자 데이터"
          >

            <button
              type="button"
              className={
                activeTab === "clinical"
                  ? "consultation-review__tab active"
                  : "consultation-review__tab"
              }
              onClick={() =>
                setActiveTab(
                  "clinical",
                )
              }
            >
              임상 정보
            </button>


            <button
              type="button"
              className={
                activeTab === "imaging"
                  ? "consultation-review__tab active"
                  : "consultation-review__tab"
              }
              onClick={() =>
                setActiveTab(
                  "imaging",
                )
              }
            >
              영상
            </button>


            <button
              type="button"
              className={
                activeTab === "ai"
                  ? "consultation-review__tab active"
                  : "consultation-review__tab"
              }
              onClick={() =>
                setActiveTab(
                  "ai",
                )
              }
            >
              AI 분석 결과
            </button>


            <button
              type="button"
              className={
                activeTab === "radiology"
                  ? "consultation-review__tab active"
                  : "consultation-review__tab"
              }
              onClick={() =>
                setActiveTab(
                  "radiology",
                )
              }
            >
              최종 판독
            </button>


            <button
              type="button"
              className={
                activeTab === "cdss"
                  ? "consultation-review__tab active"
                  : "consultation-review__tab"
              }
              onClick={() =>
                setActiveTab(
                  "cdss",
                )
              }
            >
              CDSS 결과
            </button>

          </div>


          <div className="consultation-review__patient-data-content">
            {renderPatientData()}
          </div>

        </section>


        {/* ===================================================
            실시간 협진 메시지
            =================================================== */}

        <section className="consultation-review__message-card">

          <div className="consultation-review__message-header">

            <div>

              <h2>
                실시간 협진 메시지
              </h2>

              <span>
                의료진 간 협진 커뮤니케이션
              </span>

            </div>


            <span className="consultation-review__connection-status">
              연동 예정
            </span>

          </div>


          <div className="consultation-review__chat-body">

            <div className="consultation-review__chat-empty">

              <strong>
                실시간 메시지 API 연동 예정
              </strong>

              <span>
                의료진 간 메시지와 추가 확인 요청이
                이 영역에 표시됩니다.
              </span>

            </div>

          </div>


          <div className="consultation-review__chat-input">

            <input
              type="text"
              placeholder="메시지 기능 연동 예정"
              disabled
            />

            <button
              type="button"
              disabled
            >
              전송
            </button>

          </div>

        </section>

      </div>


      {/* =====================================================
          CONSULTATION DETAIL
          ===================================================== */}

      <button
        type="button"
        className="consultation-review__detail-button"
        disabled={
          !onOpenDetail
        }
        onClick={() => {

          onOpenDetail?.(
            consultation.consultation_id,
          );

        }}
      >
        협진 상세로 이동

        <span aria-hidden="true">
          →
        </span>

      </button>

    </section>
  );

}