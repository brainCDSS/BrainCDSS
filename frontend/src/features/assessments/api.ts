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
} from "./types";


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

export function startAssessment(
  payload: StartAssessmentRequest,
): Promise<StartAssessmentResponse> {

  return apiRequest<StartAssessmentResponse>(
    "/api/v1/assessments",
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
   Assessment 상세 / 결과 조회
   ---------------------------------------------------------
   현재 저장된 초기평가와
   Backend 계산 결과를 조회한다.

   GET /api/v1/assessments/{assessment_id}
   ========================================================= */

export function getAssessmentDetail(
  assessmentId: string,
): Promise<AssessmentDetailResponse> {

  return apiRequest<AssessmentDetailResponse>(
    `/api/v1/assessments/${
      encodeURIComponent(assessmentId)
    }`,
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

export function updateAssessment(
  assessmentId: string,
  payload: UpdateAssessmentRequest,
): Promise<UpdateAssessmentResponse> {

  return apiRequest<UpdateAssessmentResponse>(
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