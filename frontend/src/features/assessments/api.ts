import { apiRequest } from "../../api/client";

import type {
  AssessmentDetailResponse,
  AssessmentEncounterListResponse,
  AssessmentWorklistResponse,
  CompleteAssessmentRequest,
  CompleteAssessmentResponse,
  StartAssessmentRequest,
  StartAssessmentResponse,
  UpdateAssessmentRequest,
  UpdateAssessmentResponse,
  ClinicianListResponse,
  CreateEncounterRequest,
  EncounterResponse,
  HospitalDepartmentResponse,
  HospitalListResponse,
  // [추가] 신경과 응급 Worklist 연결
  EmergencyWorklistResponse,
  // [추가 끝] 신경과 응급 Worklist 연결
} from "./types";

export async function createEncounter(payload: CreateEncounterRequest): Promise<EncounterResponse> {
  const response = await apiRequest<EncounterResponse & { id?: string }>("/api/v1/encounters", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  return { ...response, encounter_id: response.encounter_id ?? response.id ?? "" };
}


/* =========================================================
   Assessment Worklist
   ---------------------------------------------------------
   초기평가 대기 환자 목록 조회
   ========================================================= */

export async function getAssessmentWorklist(
  status?: "WAITING" | "DRAFT" | "COMPLETED",
  date?: string,
): Promise<AssessmentWorklistResponse> {
  const query = new URLSearchParams();

  if (status) {
    query.set("status", status);
  }
  if (date) {
    query.set("date", date);
  }

  const suffix = query.toString()
    ? `?${query.toString()}`
    : "";

  const response = await apiRequest<AssessmentWorklistResponse>(
    `/api/v1/assessments/worklist${suffix}`,
  );

  return {
    ...response,
    results: (response.results ?? []).map(
      (item) => ({
        ...item,
        assessment_id:
          item.assessment_id ??
          item.id ??
          null,
      }),
    ),
  };
}


/* =========================================================
   Assessment 시작
   ---------------------------------------------------------
   Encounter에 대한 InitialAssessment 생성

   POST /api/v1/assessments
   ========================================================= */

export async function startAssessment(
  payload: StartAssessmentRequest,
): Promise<StartAssessmentResponse> {
  const response = await apiRequest<StartAssessmentResponse & { id?: string }>(
    "/api/v1/assessments",
    {
      method: "POST",

      headers: {
        "Content-Type": "application/json",
      },

      body: JSON.stringify(payload),
    },
  );
  return { ...response, assessment_id: response.assessment_id ?? response.id ?? "" };
}


/* =========================================================
   Assessment 상세 / 결과 조회
   ---------------------------------------------------------
   현재 저장된 초기평가와
   Backend 계산 결과를 조회한다.

   GET /api/v1/assessments/{assessment_id}
   ========================================================= */

export async function getAssessmentDetail(
  assessmentId: string,
): Promise<AssessmentDetailResponse> {
  const response = await apiRequest<AssessmentDetailResponse & { id?: string }>(
    `/api/v1/assessments/${
      encodeURIComponent(assessmentId)
    }`,
  );
  return { ...response, assessment_id: response.assessment_id ?? response.id ?? "", items: response.items ?? [] };
}

export function getAssessmentsByEncounter(
  encounterId: string,
): Promise<AssessmentEncounterListResponse> {
  return apiRequest<AssessmentEncounterListResponse>(
    `/api/v1/assessments?encounter_id=${encodeURIComponent(encounterId)}`,
  );
}


/* =========================================================
   Assessment 임시저장
   ---------------------------------------------------------
   작성 중인 Triage 체크리스트 저장

   PATCH /api/v1/assessments/{assessment_id}

   중요:
   - 점수 계산은 프론트에서 하지 않는다.
   - item_code는 Backend 계약에 맞춰 전달한다.
   ========================================================= */

export async function updateAssessment(
  assessmentId: string,
  payload: UpdateAssessmentRequest,
): Promise<UpdateAssessmentResponse> {

  const response = await apiRequest<UpdateAssessmentResponse & { id?: string }>(
    `/api/v1/assessments/${
      encodeURIComponent(assessmentId)
    }`,
    {
      method: "PATCH",

      headers: {
        "Content-Type": "application/json",
      },

      body: JSON.stringify(payload),
    },
  );
  return { ...response, assessment_id: response.assessment_id ?? response.id ?? "", items: response.items ?? [] };
}


/* =========================================================
   Assessment 완료
   ---------------------------------------------------------
   담당 신경과 지정 후 Triage 완료

   POST
   /api/v1/assessments/{assessment_id}/complete

   Backend 처리:
   - 필수항목 검증
   - Initial Screening Score 계산
   - 간호사가 선택한 triage_priority 검증 / 저장
   - 담당 신경과 저장
   - 긴급 / 응급일 경우 응급 이벤트 생성
   ========================================================= */

export function completeAssessment(
  assessmentId: string,
  payload: CompleteAssessmentRequest,
): Promise<CompleteAssessmentResponse> {

  return apiRequest<CompleteAssessmentResponse>(
    `/api/v1/assessments/${
      encodeURIComponent(assessmentId)
    }/complete`,
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
   소속 기관 목록 조회
   ---------------------------------------------------------
   GET /api/v1/hospitals
   ========================================================= */

export function getHospitals():
Promise<HospitalListResponse> {

  return apiRequest<HospitalListResponse>(
    "/api/v1/hospitals",
  );
}


/* =========================================================
   병원별 진료과 목록 조회
   ---------------------------------------------------------
   GET /api/v1/hospitals/{hospital_id}/departments
   ========================================================= */

export function getHospitalDepartments(
  hospitalId: string,
): Promise<HospitalDepartmentResponse> {

  return apiRequest<HospitalDepartmentResponse>(
    `/api/v1/hospitals/${
      encodeURIComponent(hospitalId)
    }/departments`,
  );
}


/* =========================================================
   의료진 목록 조회
   ---------------------------------------------------------
   선택한 진료과의 활성 의료진 목록을 조회한다.

   GET /api/v1/departments/{department_id}/clinicians
   ========================================================= */

export function getClinicians(
  departmentId: string,
): Promise<ClinicianListResponse> {

  return apiRequest<ClinicianListResponse>(
    `/api/v1/departments/${
      encodeURIComponent(departmentId)
    }/clinicians`,
  );
}

export function acknowledgeEmergencyEvent(eventId: string): Promise<{ event_id: string; status: string; acknowledged_at: string }> {
  return apiRequest(`/api/v1/emergency-events/${encodeURIComponent(eventId)}/acknowledge`, { method: "POST" });
}

// [추가] 신경과 응급 Worklist 연결
export function getEmergencyWorklist(): Promise<EmergencyWorklistResponse> {
  return apiRequest<EmergencyWorklistResponse>(
    "/api/v1/neurology/emergency-worklist",
  );
}
// [추가 끝] 신경과 응급 Worklist 연결
