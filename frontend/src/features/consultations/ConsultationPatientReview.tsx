import {
  useEffect,
  useMemo,
  useState,
} from "react";

import { getAIAnalyses, getAIAnalysisResult } from "../ai-analysis/api";
import type { AIAnalysisItem, AIAnalysisResult } from "../ai-analysis/types";
import { getImagingStudies } from "../imaging/api";
import type { ImagingStudy } from "../imaging/types";
import { getRadiologyReport } from "../radiology/api";
import type { RadiologyReport } from "../radiology/types";

import {
  acceptConsultation,
  cancelConsultation,
  getConsultationDetail,
  markConsultationResponseViewed,
  rejectConsultation,
  respondConsultation,
  startConsultation,
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

  const [actionBusy, setActionBusy] = useState(false);
  const [actionError, setActionError] = useState<string | null>(null);
  const [isReplyPanelOpen, setIsReplyPanelOpen] = useState(false);
  const [finalOpinion, setFinalOpinion] = useState("");
  const [treatmentPlan, setTreatmentPlan] = useState("");
  const [studies, setStudies] = useState<ImagingStudy[]>([]);
  const [analyses, setAnalyses] = useState<AIAnalysisItem[]>([]);
  const [analysisResults, setAnalysisResults] = useState<AIAnalysisResult[]>([]);
  const [reports, setReports] = useState<RadiologyReport[]>([]);
  const [clinicalDataLoading, setClinicalDataLoading] = useState(false);
  const [clinicalDataError, setClinicalDataError] = useState<string | null>(null);

  async function runAction(action: string) {
    if (!consultation || actionBusy) return;
    setActionBusy(true); setActionError(null);
    try {
      if (action === "ACCEPT") await acceptConsultation(consultation.consultation_id);
      else if (action === "START") await startConsultation(consultation.consultation_id);
      else if (action === "VIEW_RESPONSE") await markConsultationResponseViewed(consultation.consultation_id);
      else if (action === "REJECT" || action === "CANCEL") {
        const reason = globalThis.prompt("사유를 입력해 주세요.")?.trim();
        if (!reason) return;
        if (action === "REJECT") await rejectConsultation(consultation.consultation_id, reason);
        else await cancelConsultation(consultation.consultation_id, reason);
      }
      setConsultation(await getConsultationDetail(consultation.consultation_id));
    } catch { setActionError("협진 상태 변경에 실패했습니다."); }
    finally { setActionBusy(false); }
  }

  function closeReplyPanel() {
    if (actionBusy) return;
    setIsReplyPanelOpen(false);
    setActionError(null);
  }

  async function submitConsultationResponse() {
    if (!consultation || actionBusy) return;

    const opinion = finalOpinion.trim();
    const plan = treatmentPlan.trim();
    if (!opinion) {
      setActionError("협진 소견을 입력해 주세요.");
      return;
    }

    setActionBusy(true);
    setActionError(null);
    try {
      const updatedConsultation = await respondConsultation(
        consultation.consultation_id,
        {
          final_opinion: opinion,
          ...(plan ? { treatment_plan: plan } : {}),
        },
      );
      setConsultation(updatedConsultation);
      setFinalOpinion("");
      setTreatmentPlan("");
      setIsReplyPanelOpen(false);
    } catch {
      setActionError("협진 회신 저장에 실패했습니다.");
    } finally {
      setActionBusy(false);
    }
  }


  /* ========================================================
     CON-003
     ======================================================== */

  useEffect(() => {

    let cancelled = false;

    setIsReplyPanelOpen(false);
    setFinalOpinion("");
    setTreatmentPlan("");
    setActionError(null);


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

  useEffect(() => {
    if (!consultation) return;
    let cancelled = false;

    async function loadPatientData() {
      setClinicalDataLoading(true);
      setClinicalDataError(null);
      try {
        const patientStudies = await getImagingStudies({
          patientId: consultation!.patient_summary.id,
        });
        const studyIds = new Set(patientStudies.map((study) => study.id));
        const analysisResponse = await getAIAnalyses();
        const patientAnalyses = analysisResponse.results.filter((item) =>
          studyIds.has(item.study_id),
        );
        const completedResults = await Promise.allSettled(
          patientAnalyses
            .filter((item) => item.status === "COMPLETED")
            .map((item) => getAIAnalysisResult(item.analysis_id)),
        );
        const reportResults = await Promise.allSettled(
          patientStudies
            .map((study) =>
              study.current_report &&
              ["FINAL", "AMENDED"].includes(study.current_report.status)
                ? study.current_report.report_id
                : null,
            )
            .filter((id): id is string => Boolean(id))
            .map(getRadiologyReport),
        );
        if (cancelled) return;
        setStudies(patientStudies);
        setAnalyses(patientAnalyses);
        setAnalysisResults(
          completedResults.flatMap((result) =>
            result.status === "fulfilled" ? [result.value] : [],
          ),
        );
        setReports(
          reportResults.flatMap((result) =>
            result.status === "fulfilled" ? [result.value] : [],
          ),
        );
      } catch {
        if (!cancelled) {
          setClinicalDataError("환자 영상·분석 데이터를 불러오지 못했습니다.");
          setStudies([]);
          setAnalyses([]);
          setAnalysisResults([]);
          setReports([]);
        }
      } finally {
        if (!cancelled) setClinicalDataLoading(false);
      }
    }

    void loadPatientData();
    return () => { cancelled = true; };
  }, [consultation]);

  const analysisResultById = useMemo(
    () => new Map(analysisResults.map((result) => [result.analysis_id, result])),
    [analysisResults],
  );


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
              {clinicalDataLoading
                ? "영상검사를 불러오는 중입니다."
                : clinicalDataError
                  ? clinicalDataError
                  : studies.length
                    ? `${studies.length}건의 영상검사`
                    : "연결된 영상검사가 없습니다."}
            </strong>

            <span>
              {studies.length
                ? studies.map((study) => `${study.modality || "-"} · ${study.status}`).join(" / ")
                : "환자 ID 기준 Imaging Study 조회 결과입니다."}
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
              {clinicalDataLoading
                ? "AI 분석 결과를 불러오는 중입니다."
                : clinicalDataError
                  ? clinicalDataError
                  : analyses.length
                    ? `${analyses.length}건의 AI 분석`
                    : "AI 분석 결과가 없습니다."}
            </strong>

            <span>
              {analyses.length
                ? analyses.map((analysis) => {
                    const result = analysisResultById.get(analysis.analysis_id);
                    const confidence = result?.confidence == null
                      ? ""
                      : ` · 신뢰도 ${Math.round(result.confidence * 100)}%`;
                    return `${analysis.analysis_type} · ${analysis.status}${confidence}`;
                  }).join(" / ")
                : "환자의 영상검사와 연결된 AI 분석만 표시합니다."}
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
              {clinicalDataLoading
                ? "최종 판독을 불러오는 중입니다."
                : clinicalDataError
                  ? clinicalDataError
                  : reports.length
                    ? `${reports.length}건의 판독문`
                    : "조회 가능한 판독문이 없습니다."}
            </strong>

            <span>
              {reports.length
                ? reports.map((report) =>
                    `${report.status} · ${report.impression || report.findings || "판독 내용 없음"}`,
                  ).join(" / ")
                : "Imaging Study의 현재 판독문을 기준으로 조회합니다."}
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

            <span className="consultation-review__requester-label">
              요청 의료진
            </span>

            <div className="consultation-review__requester-person">

            <div className="consultation-review__clinician-avatar">

              <span className="consultation-review__avatar-head" />

              <span className="consultation-review__avatar-body" />

            </div>


            <div className="consultation-review__clinician">

            <div className="consultation-review__clinician-main">

                <strong>
                {`${consultation.requested_by.department} ${consultation.requested_by.name}`}
                </strong>

                </div>

                <small>
                {consultation.requested_by.department}
                </small>
            </div>

            </div>

          </div>

          <div className="consultation-review__reason">

            <div className="consultation-review__reason-title">

              <strong>
                협진 요청 사유
              </strong>

            </div>


            <div className="consultation-review__reason-content">
              {(consultation as ConsultationListItem & { reason?: string | null }).reason || "-"}
            </div>

          </div>


          <div className="consultation-review__request-actions">
            {consultation.allowed_actions.includes("ACCEPT") && (
              <button
                className="clinical-action"
                disabled={actionBusy}
                onClick={() => void runAction("ACCEPT")}
                type="button"
              >
                수락
              </button>
            )}

            {consultation.allowed_actions.includes("REJECT") && (
              <button
                className="consultation-review__reject-action"
                disabled={actionBusy}
                onClick={() => void runAction("REJECT")}
                type="button"
              >
                거절
              </button>
            )}
          </div>


        </div>

      </section>


      {/* =====================================================
          LOWER WORKSPACE
          ===================================================== */}

      <div
        className={
          isReplyPanelOpen
            ? "consultation-review__workspace consultation-review__workspace--reply-open"
            : "consultation-review__workspace"
        }
      >


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

        {isReplyPanelOpen && (
          <aside
            className="consultation-review__reply-panel"
            aria-labelledby="consultation-reply-title"
          >
            <div className="consultation-review__reply-header">
              <div>
                <h2 id="consultation-reply-title">협진 회신 작성</h2>
                <p>
                  환자 데이터와 실시간 메시지를 참고해 최종 협진 의견을 작성합니다.
                </p>
              </div>
              <button
                type="button"
                className="consultation-review__reply-close"
                aria-label="협진 회신 작성 닫기"
                disabled={actionBusy}
                onClick={closeReplyPanel}
              >
                ×
              </button>
            </div>

            <div className="consultation-review__reply-body">
              <label className="consultation-review__reply-field">
                <span>협진 소견 *</span>
                <textarea
                  value={finalOpinion}
                  disabled={actionBusy}
                  placeholder="환자 상태와 검사 결과에 대한 최종 소견을 입력하세요."
                  onChange={(event) => setFinalOpinion(event.target.value)}
                />
              </label>

              <label className="consultation-review__reply-field">
                <span>권고사항 / 계획</span>
                <textarea
                  value={treatmentPlan}
                  disabled={actionBusy}
                  placeholder="권고 치료, 추가 검사, 추후 계획 등을 입력하세요."
                  onChange={(event) => setTreatmentPlan(event.target.value)}
                />
              </label>

              {actionError && (
                <div className="consultation-review__reply-error" role="alert">
                  {actionError}
                </div>
              )}

              <p className="consultation-review__reply-note">
                실시간 메시지는 협의 과정이며, 이 회신은 최종 공식 협진 의견으로 저장됩니다.
              </p>
            </div>

            <div className="consultation-review__reply-actions">
              <button
                type="button"
                disabled={actionBusy}
                onClick={closeReplyPanel}
              >
                취소
              </button>
              <button
                type="button"
                className="consultation-review__reply-submit"
                disabled={actionBusy || !finalOpinion.trim()}
                onClick={() => void submitConsultationResponse()}
              >
                {actionBusy ? "저장 중..." : "회신 완료"}
              </button>
            </div>
          </aside>
        )}

      </div>


      {/* =====================================================
          CONSULTATION DETAIL
          ===================================================== */}

      <div className="clinical-action-bar">
        {consultation.allowed_actions.includes("START") && <button className="clinical-action" disabled={actionBusy} onClick={() => void runAction("START")} type="button">협진 시작</button>}
        {consultation.allowed_actions.includes("CANCEL") && <button className="clinical-action" disabled={actionBusy} onClick={() => void runAction("CANCEL")} type="button">협진 취소</button>}
        {consultation.allowed_actions.includes("RESPOND") && !isReplyPanelOpen && <button className="clinical-action" disabled={actionBusy} onClick={() => { setActionError(null); setIsReplyPanelOpen(true); }} type="button">협진 회신 작성</button>}
      </div>
      {actionError && !isReplyPanelOpen && <div className="clinical-state clinical-state--error" role="alert">{actionError}</div>}

    </section>
  );

}
