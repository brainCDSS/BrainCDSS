import { apiRequest } from "../../api/client";

import type {
  ConsultationListItem,
  ConsultationListResponse,
  ConsultationMessage,
  ConsultationMessageListResponse,
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

const consultationAction = (consultationId: string, action: string, payload?: unknown) => apiRequest<ConsultationListItem>(`/api/v1/consultations/${encodeURIComponent(consultationId)}/${action}`, { method: "POST", headers: payload === undefined ? undefined : { "Content-Type": "application/json" }, body: payload === undefined ? undefined : JSON.stringify(payload) });
export function createConsultation(payload: { encounter_id: string; consultation_type: "RADIOLOGY" | "NEUROSURGERY"; assigned_to_id: string; priority: "ROUTINE" | "URGENT" | "STAT"; reason: string }) { return apiRequest<ConsultationListItem>("/api/v1/consultations", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload) }); }
export function acceptConsultation(id: string) { return consultationAction(id, "accept"); }
export function rejectConsultation(id: string, reason: string) { return consultationAction(id, "reject", { reason }); }
export function startConsultation(id: string) { return consultationAction(id, "start"); }
export function respondConsultation(id: string, payload: { final_opinion: string; treatment_plan?: string }) { return consultationAction(id, "respond", payload); }
export function cancelConsultation(id: string, reason: string) { return consultationAction(id, "cancel", { reason }); }
export function markConsultationResponseViewed(id: string) { return consultationAction(id, "view-response"); }


/* =========================================================
   협진 실시간 메시지
   GET/POST /api/v1/consultations/{consultation_id}/messages
   ========================================================= */

export function getConsultationMessages(
  consultationId: string,
  options: { after?: string; signal?: AbortSignal } = {},
): Promise<ConsultationMessageListResponse> {
  const query = options.after
    ? `?after=${encodeURIComponent(options.after)}`
    : "";
  return apiRequest<ConsultationMessageListResponse>(
    `/api/v1/consultations/${encodeURIComponent(consultationId)}/messages${query}`,
    { signal: options.signal },
  );
}

export function sendConsultationMessage(
  consultationId: string,
  content: string,
): Promise<ConsultationMessage> {
  return apiRequest<ConsultationMessage>(
    `/api/v1/consultations/${encodeURIComponent(consultationId)}/messages`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ content }),
    },
  );
}
