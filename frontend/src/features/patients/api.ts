import { apiRequest } from "../../api/client";

import type {
  Patient,
  PatientListResponse,
} from "./types";


/**
 * 환자 목록 조회
 *
 * GET /api/v1/patients
 */
export function getPatients(
  search?: string,
  page = 1,
): Promise<PatientListResponse> {
  const query =
    new URLSearchParams();

  if (search?.trim()) {
    query.set(
      "search",
      search.trim(),
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