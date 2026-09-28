import { apiRequest } from "../../api/client";

import type {
  ConsultationListItem,
  ConsultationListResponse,
  ConsultationMessage,
  ConsultationMessageListResponse,
  ConsultationMessagePresence,
} from "./types";


/* =========================================================
   CON-002 협진 목록 조회
   GET /api/v1/consultations
   ========================================================= */

export function getConsultations():
Promise<ConsultationListResponse> {
  return apiRequest<ConsultationListResponse>(
    "/api/v1/consultations",
  );
}


/* =========================================================
   협진 Presence 조회
   GET /api/v1/consultations/{consultation_id}/presence
   ========================================================= */

export function getConsultationMessagePresence(
  consultationId: string,
  signal?: AbortSignal,
): Promise<ConsultationMessagePresence> {
  return apiRequest<ConsultationMessagePresence>(
    `/api/v1/consultations/${encodeURIComponent(consultationId)}/presence`,
    signal ? { signal } : {},
  );
}


/* =========================================================
   협진 Presence 갱신
   PUT /api/v1/consultations/{consultation_id}/presence
   ========================================================= */

export function updateConsultationMessagePresence(
  consultationId: string,
  isTyping: boolean,
): Promise<ConsultationMessagePresence> {
  return apiRequest<ConsultationMessagePresence>(
    `/api/v1/consultations/${encodeURIComponent(consultationId)}/presence`,
    {
      method: "PUT",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        is_typing: isTyping,
      }),
    },
  );
}


/* =========================================================
   CON-003 협진 상세 조회
   GET /api/v1/consultations/{consultation_id}
   ========================================================= */

export function getConsultationDetail(
  consultationId: string,
): Promise<ConsultationListItem> {
  return apiRequest<ConsultationListItem>(
    `/api/v1/consultations/${encodeURIComponent(
      consultationId,
    )}`,
  );
}


/* =========================================================
   협진 상태 변경 공통
   ========================================================= */

const consultationAction = (
  consultationId: string,
  action: string,
  payload?: unknown,
) =>
  apiRequest<ConsultationListItem>(
    `/api/v1/consultations/${encodeURIComponent(
      consultationId,
    )}/${action}`,
    {
      method: "POST",
      headers:
        payload === undefined
          ? undefined
          : {
              "Content-Type": "application/json",
            },
      body:
        payload === undefined
          ? undefined
          : JSON.stringify(payload),
    },
  );


/* =========================================================
   CON-001 협진 생성
   POST /api/v1/consultations
   ========================================================= */

export function createConsultation(payload: {
  encounter_id: string;
  consultation_type:
    | "RADIOLOGY"
    | "NEUROSURGERY";
  assigned_to_id: string;
  priority:
    | "ROUTINE"
    | "URGENT"
    | "STAT";
  reason: string;
}) {
  return apiRequest<ConsultationListItem>(
    "/api/v1/consultations",
    {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(payload),
    },
  );
}


/* =========================================================
   CON-004 협진 수락
   ========================================================= */

export function acceptConsultation(
  id: string,
) {
  return consultationAction(
    id,
    "accept",
  );
}


/* =========================================================
   CON-008 협진 거절
   ========================================================= */

export function rejectConsultation(
  id: string,
  reason: string,
) {
  return consultationAction(
    id,
    "reject",
    {
      reason,
    },
  );
}


/* =========================================================
   CON-005 협진 시작
   ========================================================= */

export function startConsultation(
  id: string,
) {
  return consultationAction(
    id,
    "start",
  );
}


/* =========================================================
   CON-006 협진 회신
   ========================================================= */

export function respondConsultation(
  id: string,
  payload: {
    final_opinion: string;
    treatment_plan?: string;
  },
) {
  return consultationAction(
    id,
    "respond",
    payload,
  );
}


/* =========================================================
   CON-009 협진 취소
   ========================================================= */

export function cancelConsultation(
  id: string,
  reason: string,
) {
  return consultationAction(
    id,
    "cancel",
    {
      reason,
    },
  );
}


/* =========================================================
   CON-007 협진 회신 확인
   ========================================================= */

export function markConsultationResponseViewed(
  id: string,
) {
  return consultationAction(
    id,
    "view-response",
  );
}


/* =========================================================
   협진 실시간 메시지 목록 조회
   GET /api/v1/consultations/{consultation_id}/messages
   ========================================================= */

export function getConsultationMessages(
  consultationId: string,
  options: {
    after?: string;
    signal?: AbortSignal;
  } = {},
): Promise<ConsultationMessageListResponse> {
  const query = options.after
    ? `?after=${encodeURIComponent(
        options.after,
      )}`
    : "";

  return apiRequest<ConsultationMessageListResponse>(
    `/api/v1/consultations/${encodeURIComponent(
      consultationId,
    )}/messages${query}`,
    {
      signal: options.signal,
    },
  );
}


/* =========================================================
   협진 실시간 메시지 전송
   POST /api/v1/consultations/{consultation_id}/messages
   ========================================================= */

export function sendConsultationMessage(
  consultationId: string,
  content: string,
): Promise<ConsultationMessage> {
  return apiRequest<ConsultationMessage>(
    `/api/v1/consultations/${encodeURIComponent(
      consultationId,
    )}/messages`,
    {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        content,
      }),
    },
  );
}