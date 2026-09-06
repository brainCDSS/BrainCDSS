import { apiRequest } from "../../api/client";

import type {
  ConsultationListItem,
  ConsultationListResponse,
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