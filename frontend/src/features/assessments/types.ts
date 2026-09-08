/* =========================================================
   Triage / Initial Assessment Types
   ========================================================= */


/**
 * API-ASM-002
 * 초기평가 시작 Request
 */
export interface StartAssessmentRequest {
  encounter_id: string;
}


/**
 * API-ASM-002
 * 초기평가 시작 Response
 */
export interface StartAssessmentResponse {
  assessment_id: string;
  encounter_id: string;
  status: string;
  created_at: string;
}


/* =========================================================
   Assessment Item
   ---------------------------------------------------------
   FAST / Vital 등 초기평가 항목
   ========================================================= */

export interface AssessmentItem {
  item_code: string;

  /**
   * 상세 조회 Mock에서 사용
   */
  value?: boolean | number | string;

  /**
   * 임시저장에서 문자열 값 사용
   *
   * 예:
   * FAST_FACE = ABNORMAL
   */
  value_text?: string;

  /**
   * 임시저장에서 수치 값 사용
   *
   * 예:
   * BP_SYS = 160
   */
  value_numeric?: number;

  /**
   * 단위
   *
   * 예:
   * mmHg
   */
  unit?: string;

  /**
   * 서버에서 계산된 점수
   */
  score?: number;

  /**
   * Red Flag 여부
   */
  is_red_flag?: boolean;
}


/* =========================================================
   API-ASM-003
   초기평가 상세 조회 Response
   ========================================================= */

export interface AssessmentDetailResponse {
  assessment_id: string;

  status: string;

  total_score: number | null;

  triage_priority: string | null;

  assigned_neurologist?: {
    id: string;
    name: string;
  } | null;

  items: AssessmentItem[];
}


/* =========================================================
   API-ASM-004
   초기평가 입력 / 임시저장
   ========================================================= */

export interface UpdateAssessmentRequest {
  onset_at: string | null;

  lkw_at: string | null;

  symptom_note: string;

  items: AssessmentItem[];
}


export interface UpdateAssessmentResponse {
  assessment_id: string;

  status: string;

  updated_at: string;

  items: AssessmentItem[];
}


/* =========================================================
   API-ASM-005
   초기평가 완료 + 담당 신경과 지정
   ========================================================= */

export interface CompleteAssessmentRequest {
  assigned_neurologist_id: string;
}


export interface CompleteAssessmentResponse {
  assessment_id: string;

  status: string;

  total_score: number;

  triage_priority: string;

  assigned_neurologist_id: string;

  emergency_event_id: string | null;

  completed_at: string;
}


/* =========================================================
   진료과별 의료진 목록
   GET /api/v1/departments/{department_id}/clinicians
   ========================================================= */

export interface Clinician {
  id: string;
  name: string;
  specialty: string | null;
  license_no: string | null;
  is_active: boolean;
}

export interface ClinicianListResponse {
  department: {
    id: string;
    name: string;
  };

  clinicians: Clinician[];
}


/* =========================================================
   Assessment Worklist Types
   ========================================================= */

/**
 * API-ASM-001
 * Worklist 한 건
 */
export interface AssessmentWorklistItem {
  assessment_id: string | null;
  encounter_id: string;
  patient_summary: Record<string, unknown>;
  status: string;
  triage_priority: string | null;
  created_at: string | null;
}


/**
 * API-ASM-001
 * GET /api/v1/assessments/worklist
 * Response
 */
export interface AssessmentWorklistResponse {
  count: number;
  next: string | null;
  previous: string | null;
  results: AssessmentWorklistItem[];
}