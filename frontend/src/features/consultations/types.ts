/* =========================================================
   Consultation Types
   ========================================================= */


/* =========================================================
   협진 상태
   ========================================================= */

export type ConsultationStatus =
  | "REQUESTED"
  | "ACCEPTED"
  | "IN_PROGRESS"
  | "RESPONDED"
  | "CLOSED"
  | "REJECTED"
  | "CANCELLED"
  | "EXPIRED";


/* =========================================================
   협진 유형
   ========================================================= */

export type ConsultationType =
  | "RADIOLOGY"
  | "NEUROSURGERY";


/* =========================================================
   협진 우선순위
   ========================================================= */

export type ConsultationPriority =
  | "ROUTINE"
  | "URGENT"
  | "STAT";


/* =========================================================
   현재 로그인 의료진과 협진의 관계
   ========================================================= */

export type ConsultationViewerRelation =
  | "REQUESTED_BY"
  | "ASSIGNED_TO";


/* =========================================================
   의료진 요약
   ========================================================= */

export interface ConsultationUserSummary {
  id: string;
  name: string;
  department: string;
}


/* =========================================================
   환자 요약
   ========================================================= */

export interface ConsultationPatientSummary {
  id: string;
  patient_no: string;
  name: string;
  birth_date: string | null;
  estimated_age: number | null;
  sex: string | null;
}


/* =========================================================
   협진 목록 / 상세 기본 데이터
   ========================================================= */

export interface ConsultationListItem {
  consultation_id: string;
  encounter_id: string;

  patient_summary: ConsultationPatientSummary;

  type: ConsultationType;
  priority: ConsultationPriority;
  status: ConsultationStatus;

  requested_by: ConsultationUserSummary;

  assigned_to:
    | ConsultationUserSummary
    | null;

  requested_at: string;

  accepted_at: string | null;
  started_at: string | null;
  completed_at: string | null;
  response_viewed_at: string | null;

  viewer_relation: ConsultationViewerRelation;

  ui_status: string;

  allowed_actions: string[];
}


/* =========================================================
   CON-002 협진 목록 조회 Response
   ========================================================= */

export interface ConsultationListResponse {
  count: number;
  results: ConsultationListItem[];
}