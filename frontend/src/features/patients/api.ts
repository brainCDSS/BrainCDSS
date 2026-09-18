import { apiRequest } from "../../api/client";

import type {
  Patient,
  PatientDetail,
  PatientListResponse,
} from "./types";

export interface PatientTimelineEvent {
  id: string;
  at: string;
  title: string;
  detail: string;
  tone: "assessment" | "note" | "imaging" | "ai" | "ai_review" | "consultation" | "radiology" | "prescription";
}

export interface PatientTimelineResponse {
  count: number;
  results: PatientTimelineEvent[];
}


/**
 * 환자 목록 조회
 *
 * GET /api/v1/patients
 */
export function getPatients(
  search?: string,
  page = 1,
  scope?: "all" | "mine",
): Promise<PatientListResponse> {
  const query =
    new URLSearchParams();

  if (search?.trim()) {
    query.set(
      "search",
      search.trim(),
    );
  }

  if (scope) {
    query.set(
      "scope",
      scope,
    );
  }

  query.set(
    "page",
    String(page),
  );

  return apiRequest<PatientListResponse>(
    `/api/v1/patients?${query.toString()}`,
  );
}


/**
 * 환자 신규 등록
 */
export function createPatient(
  payload: {
    name: string;
    birth_date: string;
    sex: "M" | "F" | "U";
    phone: string;
  },
): Promise<Patient> {
  return apiRequest<Patient>(
    "/api/v1/patients",
    {
      method: "POST",
      headers: {
        "Content-Type":
          "application/json",
      },
      body: JSON.stringify(
        payload,
      ),
    },
  );
}

/** GET /api/v1/patients/{patient_id} */
export function getPatient(patientId: string): Promise<PatientDetail> {
  return apiRequest<PatientDetail>(
    `/api/v1/patients/${encodeURIComponent(patientId)}`,
  );
}

export function getPatientTimeline(patientId: string): Promise<PatientTimelineResponse> {
  return apiRequest<PatientTimelineResponse>(
    `/api/v1/patients/${encodeURIComponent(patientId)}/timeline`,
  );
}
