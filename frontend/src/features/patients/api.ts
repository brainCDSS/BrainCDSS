import { apiRequest } from "../../api/client";
import type { PatientListResponse } from "./types";

/**
 * 환자 목록 조회 API
 *
 * GET /api/v1/patients
 *
 * 현재는 VITE_BACKEND_URL이 Postman Mock Server를 가리키므로
 * Mock 데이터를 받아온다.
 *
 * 나중에 Django Backend가 완성되면
 * VITE_BACKEND_URL만 Django 주소로 변경하면 된다.
 */
export function getPatients(): Promise<PatientListResponse> {
  return apiRequest<PatientListResponse>("/api/v1/patients"); //api호출부분
}