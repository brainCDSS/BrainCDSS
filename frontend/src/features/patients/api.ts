import { apiRequest } from "../../api/client";
import { filterAssessmentItemsForDisplay } from "../assessments/viewModel";

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

export type AllergySeverity = "MILD" | "MODERATE" | "SEVERE";

export interface PatientAllergy {
  id: string;
  patient_id?: string;
  ingredient?: {
    id: string;
    code: string;
    name: string;
  } | null;
  substance: string | null;
  reaction: string | null;
  severity: AllergySeverity;
  status: "ACTIVE" | "INACTIVE";
  created_at: string;
  updated_at?: string;
}

export interface PatientAllergyListResponse {
  results: PatientAllergy[];
}

export function getPatientAllergies(patientId: string): Promise<PatientAllergyListResponse> {
  return apiRequest<PatientAllergyListResponse>(
    `/api/v1/patients/${encodeURIComponent(patientId)}/allergies`,
  );
}

export function createPatientAllergy(
  patientId: string,
  payload: {
    substance: string;
    reaction?: string;
    severity: AllergySeverity;
  },
): Promise<PatientAllergy> {
  return apiRequest<PatientAllergy>(
    `/api/v1/patients/${encodeURIComponent(patientId)}/allergies`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    },
  );
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
export async function getPatient(
  patientId: string,
): Promise<PatientDetail> {
  const response =
    await apiRequest<PatientDetail>(
      `/api/v1/patients/${encodeURIComponent(patientId)}`,
    );

  if (!response.latest_assessment) {
    return response;
  }

  return {
    ...response,
    latest_assessment: {
      ...response.latest_assessment,
      items:
        filterAssessmentItemsForDisplay(
          response.latest_assessment.items,
        ),
    },
  };
}

export function getPatientTimeline(patientId: string): Promise<PatientTimelineResponse> {
  return apiRequest<PatientTimelineResponse>(
    `/api/v1/patients/${encodeURIComponent(patientId)}/timeline`,
  );
}
