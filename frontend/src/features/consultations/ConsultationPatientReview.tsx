import { formatPatientAge } from "../../lib/patientAge";
import {
  useEffect,
  useMemo,
  useRef,
  useState,
} from "react";

import { getAIAnalyses, getAIAnalysisResult } from "../ai-analysis/api";
import type { AIAnalysisItem, AIAnalysisResult } from "../ai-analysis/types";
import { getInitialAssessmentsByEncounter } from "../clinical-notes/api";
import type { InitialAssessment } from "../clinical-notes/types";
import { getImagingStudies } from "../imaging/api";
import type { ImagingStudy } from "../imaging/types";
import { getRadiologyReport } from "../radiology/api";
import type { RadiologyReport } from "../radiology/types";

import {
  acceptConsultation,
  cancelConsultation,
  getConsultationDetail,
  getConsultationMessagePresence,
  getConsultationMessages,
  markConsultationResponseViewed,
  rejectConsultation,
  respondConsultation,
  sendConsultationMessage,
  startConsultation,
  updateConsultationMessagePresence,
} from "./api";
import ConsultationReasonModal from "./ConsultationReasonModal";

import type {
  ConsultationListItem,
  ConsultationMessage,
  ConsultationMessagePresence,
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

const ASSESSMENT_ITEM_LABEL: Record<string, string> = {
  FAST_FACE: "안면", FACE: "안면",
  FAST_ARM: "상지", ARM: "상지",
  FAST_SPEECH: "언어", SPEECH: "언어",
  EYES: "시야", CONSCIOUSNESS: "의식상태",
  BP_SYS: "수축기 혈압", SBP: "수축기 혈압",
  BP_DIA: "이완기 혈압", DBP: "이완기 혈압",
  HEART_RATE: "심박수", HR: "심박수",
  SPO2: "산소포화도",
  BODY_TEMP: "체온", TEMPERATURE: "체온", BT: "체온",
};

function assessmentItemSection(code: string): "neurological" | "vitals" | "additional" {
  const normalized = code.toUpperCase();
  if (["FAST_FACE", "FACE", "FAST_ARM", "ARM", "FAST_SPEECH", "SPEECH", "EYES", "CONSCIOUSNESS"].includes(normalized)) {
    return "neurological";
  }
  if (["BP_SYS", "SBP", "BP_DIA", "DBP", "HEART_RATE", "HR", "SPO2", "BODY_TEMP", "TEMPERATURE", "BT"].includes(normalized)) {
    return "vitals";
  }
  return "additional";
}

/* =========================================================
   실시간 협진 메시지 설정
   ========================================================= */

const CHAT_MESSAGE_POLL_MS = 1000;
const CHAT_PRESENCE_POLL_MS = 1000;
const CHAT_TYPING_REFRESH_MS = 1000;
const CHAT_TYPING_IDLE_MS = 2500;

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
  const [reasonAction, setReasonAction] = useState<"REJECT" | "CANCEL" | null>(null);
  const [isReplyPanelOpen, setIsReplyPanelOpen] = useState(false);
  const [finalOpinion, setFinalOpinion] = useState("");
  const [treatmentPlan, setTreatmentPlan] = useState("");
  const [studies, setStudies] = useState<ImagingStudy[]>([]);
  const [analyses, setAnalyses] = useState<AIAnalysisItem[]>([]);
  const [analysisResults, setAnalysisResults] = useState<AIAnalysisResult[]>([]);
  const [reports, setReports] = useState<RadiologyReport[]>([]);
  const [clinicalDataLoading, setClinicalDataLoading] = useState(false);
  const [clinicalDataError, setClinicalDataError] = useState<string | null>(null);
  const [initialAssessments, setInitialAssessments] = useState<InitialAssessment[]>([]);
  const [initialAssessmentsLoading, setInitialAssessmentsLoading] = useState(false);
  const [initialAssessmentsError, setInitialAssessmentsError] = useState<string | null>(null);
  const [chatMessages, setChatMessages] = useState<ConsultationMessage[]>([]);
  const [chatDraft, setChatDraft] = useState("");
  const [chatLoading, setChatLoading] = useState(true);
  const [chatSending, setChatSending] = useState(false);
  const [chatConnected, setChatConnected] = useState(false);
  const [chatError, setChatError] = useState<string | null>(null);
  const [chatPresence, setChatPresence] = useState<ConsultationMessagePresence | null>(null);


  const chatBodyRef = useRef<HTMLDivElement | null>(null);

  const chatTypingTimerRef =
    useRef<ReturnType<typeof setTimeout> | null>(null);

  const chatTypingRef = useRef(false);

  const chatTypingLastPublishedAtRef = useRef(0);

  async function runAction(action: string, reason?: string) {
    if (!consultation || actionBusy) return;
    if ((action === "REJECT" || action === "CANCEL") && reason === undefined) {
      setReasonAction(action);
      return;
    }
    setActionBusy(true); setActionError(null);
    try {
      if (action === "ACCEPT") await acceptConsultation(consultation.consultation_id);
      else if (action === "START") await startConsultation(consultation.consultation_id);
      else if (action === "VIEW_RESPONSE") await markConsultationResponseViewed(consultation.consultation_id);
      else if (action === "REJECT" || action === "CANCEL") {
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
      await respondConsultation(
        consultation.consultation_id,
        {
          final_opinion: opinion,
          ...(plan ? { treatment_plan: plan } : {}),
        },
      );

      let refreshedConsultation: ConsultationListItem;
      try {
        refreshedConsultation = await getConsultationDetail(
          consultation.consultation_id,
        );
      } catch {
        setActionError("협진 상세 정보를 다시 불러오지 못했습니다.");
        return;
      }

      setConsultation(refreshedConsultation);
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

  useEffect(() => {
    const encounterId = consultation?.encounter_id;
    if (!encounterId) {
      setInitialAssessments([]);
      setInitialAssessmentsLoading(false);
      setInitialAssessmentsError(null);
      return;
    }

    const assessmentEncounterId = encounterId;

    let cancelled = false;

    async function loadInitialAssessments() {
      setInitialAssessmentsLoading(true);
      setInitialAssessmentsError(null);
      try {
        const response = await getInitialAssessmentsByEncounter(assessmentEncounterId);
        if (!cancelled) setInitialAssessments(response.results);
      } catch {
        if (!cancelled) {
          setInitialAssessments([]);
          setInitialAssessmentsError("초기평가 정보를 불러오지 못했습니다.");
        }
      } finally {
        if (!cancelled) setInitialAssessmentsLoading(false);
      }
    }

    void loadInitialAssessments();
    return () => { cancelled = true; };
  }, [consultation?.encounter_id]);

  useEffect(() => {
    if (!consultation) return;
    const activeConsultationId: string = consultation.consultation_id;

    let cancelled = false;
    let cursor: string | undefined;
    let timer: ReturnType<typeof setTimeout> | undefined;
    let controller: AbortController | undefined;

    setChatMessages([]);
    setChatDraft("");
    setChatLoading(true);
    setChatConnected(false);
    setChatError(null);
    setChatPresence(null);

    const mergeMessages = (incoming: ConsultationMessage[]) => {
      setChatMessages((current) => {
        const byId = new Map(current.map((message) => [message.message_id, message]));
        incoming.forEach((message) => byId.set(message.message_id, message));
        return [...byId.values()].sort(
          (left, right) =>
            new Date(left.created_at).getTime() - new Date(right.created_at).getTime(),
        );
      });
    };

    async function pollMessages() {
      controller = new AbortController();
      try {
        const response = await getConsultationMessages(activeConsultationId, {
          ...(cursor ? { after: cursor } : {}),
          signal: controller.signal,
        });
        if (cancelled) return;
        mergeMessages(response.results);

        if (response.next_cursor) {
          cursor = response.next_cursor;
        }

        setChatConnected(true);
        setChatError(null);
        setChatLoading(false);

        timer = setTimeout(
          pollMessages,
          response.has_more
            ? 0
            : CHAT_MESSAGE_POLL_MS,
        );
      } catch (pollError) {
        if (cancelled || (pollError instanceof DOMException && pollError.name === "AbortError")) {
          return;
        }
        setChatConnected(false);
        setChatError("메시지 연결이 끊겼습니다. 자동으로 다시 연결합니다.");
        setChatLoading(false);
        timer = setTimeout(pollMessages, 3000);
      }
    }

    void pollMessages();
    return () => {
      cancelled = true;
      controller?.abort();
      if (timer) clearTimeout(timer);
    };
  }, [consultation?.consultation_id]);

  useEffect(() => {
    if (!consultation) return;

    const consultationId = consultation.consultation_id;
    let disposed = false;

    const publish = async (isTyping: boolean) => {
      try {
        const presence = await updateConsultationMessagePresence(
          consultationId,
          isTyping,
        );

        if (!disposed) {
          setChatPresence(presence);
        }
      } catch {
        // Presence heartbeat 실패만으로 메시지 polling을 중단하지 않는다.
      }
    };

    const isChatActivelyVisible = () =>
      document.visibilityState === "visible"
      && document.hasFocus();

    const publishIfActive = () => {
      if (!isChatActivelyVisible()) {
        return;
      }

      void publish(
        chatTypingRef.current,
      );
    };

    publishIfActive();

    const heartbeat = setInterval(
      publishIfActive,
      2000,
    );

    const handleVisibilityChange = () => {
      if (
        document.visibilityState
        === "visible"
      ) {
        publishIfActive();
      }
    };

    const handleWindowFocus = () => {
      publishIfActive();
    };

    document.addEventListener(
      "visibilitychange",
      handleVisibilityChange,
    );

    window.addEventListener(
      "focus",
      handleWindowFocus,
    );

    return () => {
      disposed = true;
      clearInterval(heartbeat);

      document.removeEventListener(
        "visibilitychange",
        handleVisibilityChange,
      );

      window.removeEventListener(
        "focus",
        handleWindowFocus,
      );

      if (chatTypingTimerRef.current) {
        clearTimeout(
          chatTypingTimerRef.current,
        );
        chatTypingTimerRef.current = null;
      }

      chatTypingRef.current = false;
      chatTypingLastPublishedAtRef.current = 0;
    };
  }, [consultation?.consultation_id]);

  useEffect(() => {
    if (!consultation) return;

    const consultationId = consultation.consultation_id;
    let disposed = false;
    let timer: ReturnType<typeof setTimeout> | null = null;
    let controller: AbortController | null = null;

    const pollPresence = async () => {
      controller = new AbortController();

      try {
        const presence = await getConsultationMessagePresence(
          consultationId,
          controller.signal,
        );

        if (!disposed) {
          setChatPresence(presence);
        }
      } catch (pollError) {
        if (
          disposed ||
          (
            pollError instanceof DOMException &&
            pollError.name === "AbortError"
          )
        ) {
          return;
        }

        // Presence 조회 실패만으로 전체 채팅 연결을 실패 처리하지 않는다.
      }

      if (!disposed) {
        timer = setTimeout(
          pollPresence,
          CHAT_PRESENCE_POLL_MS,
        );
      }
    };

    void pollPresence();

    return () => {
      disposed = true;
      controller?.abort();

      if (timer) {
        clearTimeout(timer);
      }
    };
  }, [consultation?.consultation_id]);

  function handleChatDraftChange(value: string) {
    setChatDraft(value);

    if (!consultation) {
      return;
    }

    const consultationId = consultation.consultation_id;

    if (!value.trim()) {
      if (chatTypingTimerRef.current) {
        clearTimeout(chatTypingTimerRef.current);
        chatTypingTimerRef.current = null;
      }

      const wasTyping = chatTypingRef.current;

      chatTypingRef.current = false;
      chatTypingLastPublishedAtRef.current = 0;

      if (wasTyping) {
        void updateConsultationMessagePresence(
          consultationId,
          false,
        )
          .then(setChatPresence)
          .catch(() => undefined);
      }

      return;
    }

    const now = Date.now();
    const shouldPublishTyping =
      !chatTypingRef.current ||
      now - chatTypingLastPublishedAtRef.current >=
        CHAT_TYPING_REFRESH_MS;

    chatTypingRef.current = true;

    if (shouldPublishTyping) {
      chatTypingLastPublishedAtRef.current = now;

      void updateConsultationMessagePresence(
        consultationId,
        true,
      )
        .then(setChatPresence)
        .catch(() => {
          chatTypingLastPublishedAtRef.current = 0;
        });
    }

    if (chatTypingTimerRef.current) {
      clearTimeout(chatTypingTimerRef.current);
    }

    chatTypingTimerRef.current = setTimeout(() => {
      chatTypingRef.current = false;
      chatTypingLastPublishedAtRef.current = 0;
      chatTypingTimerRef.current = null;

      void updateConsultationMessagePresence(
        consultationId,
        false,
      )
        .then(setChatPresence)
        .catch(() => undefined);
    }, CHAT_TYPING_IDLE_MS);
  }

  useEffect(() => {
    const body = chatBodyRef.current;
    if (body) body.scrollTop = body.scrollHeight;
  }, [chatMessages.length]);

  async function submitChatMessage() {
    if (!consultation || chatSending) return;
    const content = chatDraft.trim();
    if (!content) return;

    setChatSending(true);
    setChatError(null);
    try {
      const message = await sendConsultationMessage(
        consultation.consultation_id,
        content,
      );
      setChatMessages((current) =>
        current.some((item) => item.message_id === message.message_id)
          ? current
          : [...current, message],
      );
      setChatDraft("");

      if (chatTypingTimerRef.current) {
        clearTimeout(chatTypingTimerRef.current);
        chatTypingTimerRef.current = null;
      }

      chatTypingRef.current = false;
      chatTypingLastPublishedAtRef.current = 0;

      void updateConsultationMessagePresence(
        consultation.consultation_id,
        false,
      )
        .then(setChatPresence)
        .catch(() => undefined);

      setChatConnected(true);
    } catch {
      setChatError("메시지를 전송하지 못했습니다. 잠시 후 다시 시도해 주세요.");
    } finally {
      setChatSending(false);
    }
  }

  const analysisResultById = useMemo(
    () => new Map(analysisResults.map((result) => [result.analysis_id, result])),
    [analysisResults],
  );

  const canSendChatMessage = consultation
    ? ["REQUESTED", "ACCEPTED", "IN_PROGRESS"].includes(consultation.status)
    : false;

  const formatMessageTime = (value: string) =>
    new Intl.DateTimeFormat("ko-KR", {
      month: "2-digit",
      day: "2-digit",
      hour: "2-digit",
      minute: "2-digit",
    }).format(new Date(value));


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

      const assessment = initialAssessments[0] ?? null;

      if (assessment && !initialAssessmentsLoading && !initialAssessmentsError) {
        const hasValue = (value: unknown) => (
          value !== null && value !== undefined && value !== ""
        );
        const symptomNote = assessment.symptom_note?.trim() ?? "";
        const overviewFields = [
          { label: "상태", value: assessment.status },
          { label: "총점", value: assessment.total_score },
          { label: "Triage", value: assessment.triage_priority },
          { label: "증상 시작", value: assessment.onset_at },
          { label: "마지막 정상 시각", value: assessment.lkw_at },
          { label: "담당 신경과", value: assessment.assigned_neurologist?.name },
        ].filter((field) => hasValue(field.value));
        const formatDateTime = (
          value: string | number | null | undefined,
        ): string | number | null | undefined => {
          if (typeof value !== "string") return value;
          const date = new Date(value);
          return Number.isNaN(date.getTime())
            ? value
            : date.toLocaleString("ko-KR", {
              dateStyle: "short",
              timeStyle: "short",
            });
        };
        const summaryFields = overviewFields.map((field) => ({
          ...field,
          value: field.value === assessment.onset_at || field.value === assessment.lkw_at
            ? formatDateTime(field.value)
            : field.value,
        }));
        type AssessmentItemDisplayField = {
          label: string;
          value: string;
          kind: "value" | "unit" | "score" | "flag" | "note";
        };
        const additionalItemLabels: Record<string, string> = {
          HEIGHT_CM: "키",
          WEIGHT_KG: "체중",
          BALANCE: "균형",
        };

        const displayItemRows = assessment.items.map((item) => {
          const value = item.value_text ?? item.value_numeric ?? item.value;
          const fields = [
            hasValue(value) ? { label: "값", value: String(value), kind: "value" as const } : null,
            item.unit?.trim() ? { label: "단위", value: item.unit.trim(), kind: "unit" as const } : null,
            hasValue(item.score) ? { label: "점수", value: String(item.score), kind: "score" as const } : null,
            item.is_red_flag ? { label: "Red flag", value: "Y", kind: "flag" as const } : null,
            item.note?.trim() ? { label: "메모", value: item.note.trim(), kind: "note" as const } : null,
          ].filter((field): field is AssessmentItemDisplayField => field !== null);

          return {
            itemCode: item.item_code,
            label:
              ASSESSMENT_ITEM_LABEL[item.item_code.toUpperCase()]
              ?? additionalItemLabels[item.item_code.toUpperCase()]
              ?? item.item_code,
            section: assessmentItemSection(item.item_code),
            fields,
            isRedFlag: Boolean(item.is_red_flag),
          };
        }).filter((item) => item.fields.length > 0);
        const itemSections = [
          { key: "additional", title: "기타정보" },
          { key: "neurological", title: "신경학적 평가" },
          { key: "vitals", title: "활력징후" },
        ] as const;
        const hasAssessmentDetail = (
          summaryFields.length > 1 ||
          displayItemRows.length > 0
        );

        return (
          <div className="consultation-review__data-content consultation-review__clinical-content">
            <section className="consultation-review__assessment-section">
              <h3>초기평가</h3>
              {hasAssessmentDetail ? (
                <>
                  <dl className="consultation-review__assessment-summary">
                    {summaryFields.map((field) => (
                      <div key={field.label}>
                        <dt>{field.label}</dt>
                        <dd>{field.value}</dd>
                      </div>
                    ))}
                  </dl>

                  {symptomNote && (
                    <div className="consultation-review__assessment-note">
                      <strong>증상 메모</strong>
                      <p>{symptomNote}</p>
                    </div>
                  )}

                  {displayItemRows.length > 0 && (
                    <section className="consultation-review__assessment-items">
                      <h4>평가 항목</h4>
                      {itemSections.map((section) => {
                        const rows = displayItemRows.filter((item) => item.section === section.key);
                        if (!rows.length) return null;
                        return (
                          <div
                            key={section.key}
                            className={`consultation-review__assessment-group consultation-review__assessment-group--${section.key}`}
                          >
                            <h5>{section.title}</h5>
                            {rows.map((item) => (
                              <article key={item.itemCode} className={item.isRedFlag ? "is-red-flag" : undefined}>
                                <strong>{item.label}</strong>
                                <dl>
                                  {item.fields.map((field) => (
                                    <div key={field.label}>
                                      <dt>{field.label}</dt>
                                      <dd className={field.kind === "note" ? "consultation-review__assessment-item-note" : undefined}>{field.value}</dd>
                                    </div>
                                  ))}
                                </dl>
                              </article>
                            ))}
                          </div>
                        );
                      })}
                    </section>
                  )}
                </>
              ) : (
                <p className="consultation-review__assessment-empty-detail">
                  초기평가 정보는 존재하지만 등록된 상세 정보가 없습니다.
                </p>
              )}
            </section>
          </div>
        );
      }

      return (
        <div className="consultation-review__data-content consultation-review__clinical-content">
          <div className="consultation-review__data-title">
            <span>+</span>
            <div>
              <strong>임상 정보</strong>
              <small>Triage · 초기평가</small>
            </div>
          </div>

          {initialAssessmentsLoading ? (
            <div className="consultation-review__pending">
              <strong>초기평가 정보를 불러오는 중입니다.</strong>
            </div>
          ) : initialAssessmentsError ? (
            <div className="consultation-review__pending">
              <strong>{initialAssessmentsError}</strong>
            </div>
          ) : !assessment ? (
            <div className="consultation-review__pending">
              <strong>초기평가 정보가 없습니다.</strong>
            </div>
          ) : (
            <>
              <div className="consultation-review__pending">
                <strong>초기평가</strong>
                <span>
                  평가 ID: {assessment.assessment_id} · 상태: {assessment.status} · 총점: {assessment.total_score ?? "-"} · Triage: {assessment.triage_priority ?? "-"}
                </span>
                <span>
                  증상 시작: {assessment.onset_at ?? "-"} · 마지막 정상 시각: {assessment.lkw_at ?? "-"} · 담당 신경과: {assessment.assigned_neurologist?.name ?? "-"}
                </span>
                <span>증상 메모: {assessment.symptom_note ?? "-"}</span>
              </div>

              <div className="consultation-review__pending">
                <strong>평가 항목</strong>
                {assessment.items.length ? assessment.items.map((item) => (
                  <span key={item.item_code}>
                    {item.item_code}: {item.value_text ?? item.value_numeric ?? item.value ?? "-"}{item.unit ? ` ${item.unit}` : ""} · 점수: {item.score ?? "-"} · Red flag: {item.is_red_flag ? "Y" : "N"} · 메모: {item.note ?? "-"}
                  </span>
                )) : <span>등록된 평가 항목이 없습니다.</span>}
              </div>
            </>
          )}
        </div>
      );

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
          <div className="consultation-review__patient-avatar" aria-hidden="true">
            {patient.name.trim().slice(0, 1) || "-"}
          </div>

          <div className="consultation-review__patient-identity">
            <span className="consultation-review__section-label">PATIENT</span>

            <div className="consultation-review__patient-name">
              <strong>{patient.name}</strong>
              <span>
                {patient.sex ? formatSex(patient.sex) : "성별 정보 없음"}
                {` / ${formatPatientAge(patient)}`}
              </span>
            </div>

            <div className="consultation-review__patient-meta">
              <span>환자번호 {patient.patient_no || "-"}</span>
              <span>생년월일 {patient.birth_date || "-"}</span>
              <span>성별 {patient.sex ? formatSex(patient.sex) : "-"}</span>
            </div>
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
                {`${consultation.requested_by.department ?? "진료과 미확인"} ${consultation.requested_by.name}`}
                </strong>

                </div>

                <small>
                {consultation.requested_by.department ?? "진료과 미확인"}
                </small>
            </div>

            </div>

          </div>

          <div className="consultation-review__direction" aria-hidden="true">→</div>

          <div className="consultation-review__clinician-card consultation-review__clinician-card--assignee">
            <span className="consultation-review__requester-label">협진 의료진</span>
            <div className="consultation-review__requester-person">
              <div className="consultation-review__clinician-avatar">
                <span className="consultation-review__avatar-head" />
                <span className="consultation-review__avatar-body" />
              </div>
              <div className="consultation-review__clinician consultation-review__clinician--assignee">
                <div className="consultation-review__clinician-main">
                  <strong>
                    {consultation.assigned_to
                      ? `${consultation.assigned_to.department ?? "진료과 미확인"} ${consultation.assigned_to.name}`
                      : "담당자 미배정"}
                  </strong>
                </div>
                <small>{consultation.assigned_to?.department ?? "배정 대기"}</small>
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
              {consultation.reason || "-"}
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


            <span
              className={`consultation-review__connection-status${
                chatConnected ? " is-connected" : ""
              }`}
            >
              {chatConnected ? "실시간 연결" : "연결 중"}
            </span>

            {chatPresence ? (
              <div className="consultation-review__chat-presence" aria-live="polite">
                <span>{chatPresence.active_count}명 참여 중</span>
                {chatPresence.participants
                  .filter((participant) => !participant.is_mine && participant.is_typing)
                  .map((participant) => <strong key={participant.id}>{participant.name}님이 입력 중…</strong>)}
              </div>
            ) : null}

          </div>


          <div className="consultation-review__chat-body" ref={chatBodyRef}>
            {chatLoading && chatMessages.length === 0 ? (
              <div className="consultation-review__chat-empty">
                <strong>메시지를 불러오는 중입니다.</strong>
              </div>
            ) : chatMessages.length === 0 ? (
              <div className="consultation-review__chat-empty">
                <strong>아직 메시지가 없습니다.</strong>
                <span>협진 내용을 입력하면 상대 의료진에게 실시간으로 표시됩니다.</span>
              </div>
            ) : (
              <div className="consultation-review__chat-list" aria-live="polite">
                {chatMessages.map((message) => (
                  <article
                    className={`consultation-review__chat-message${
                      message.is_mine ? " is-mine" : ""
                    }`}
                    key={message.message_id}
                  >
                    <div className="consultation-review__chat-meta">
                      <strong>{message.is_mine ? "나" : message.sender.name}</strong>
                      {!message.is_mine && message.sender.department && (
                        <span>{message.sender.department}</span>
                      )}
                      <time dateTime={message.created_at}>
                        {formatMessageTime(message.created_at)}
                      </time>
                    </div>
                    <p>{message.content}</p>
                  </article>
                ))}
              </div>
            )}
          </div>

          {chatError && (
            <div className="consultation-review__chat-error" role="alert">
              {chatError}
            </div>
          )}


          <div className="consultation-review__chat-input">

            <input
              type="text"
              value={chatDraft}
              maxLength={2000}
              placeholder={
                canSendChatMessage
                  ? "협진 메시지를 입력하세요"
                  : "종료된 협진에는 메시지를 보낼 수 없습니다"
              }
              disabled={!canSendChatMessage || chatSending}
              onChange={(event) => handleChatDraftChange(event.target.value)}
              onKeyDown={(event) => {
                if (
                  event.key === "Enter" &&
                  !event.nativeEvent.isComposing &&
                  chatDraft.trim()
                ) {
                  event.preventDefault();
                  void submitChatMessage();
                }
              }}
            />

            <button
              type="button"
              disabled={!canSendChatMessage || chatSending || !chatDraft.trim()}
              onClick={() => void submitChatMessage()}
            >
              {chatSending ? "전송 중" : "전송"}
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

      {reasonAction && (
        <ConsultationReasonModal
          title={reasonAction === "REJECT" ? "협진 거절" : "협진 취소"}
          description={reasonAction === "REJECT" ? "협진 요청을 거절하는 사유를 입력해 주세요." : "협진 요청을 취소하는 사유를 입력해 주세요."}
          placeholder={reasonAction === "REJECT" ? "거절 사유를 입력하세요." : "취소 사유를 입력하세요."}
          confirmLabel={reasonAction === "REJECT" ? "거절" : "취소"}
          busy={actionBusy}
          onClose={() => setReasonAction(null)}
          onConfirm={(reason) => {
            const action = reasonAction;
            setReasonAction(null);
            void runAction(action, reason);
          }}
        />
      )}

    </section>
  );

}
