import { apiRequest } from "../../api/client";

import type {
  AssessmentDetailResponse,
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

export function getAssessmentWorklist():
Promise<AssessmentWorklistResponse> {

  return apiRequest<AssessmentWorklistResponse>(
    "/api/v1/assessments/worklist",
  );
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
   - Score 계산
   - Red Flag 확인
   - 긴급 / 응급 / 비응급 결정
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
