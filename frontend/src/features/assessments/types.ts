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

  note?: string;
}


/* =========================================================
   API-ASM-003
   초기평가 상세 조회 Response
   ========================================================= */

export type TriagePriority =
  | "EMERGENCY"
  | "URGENT"
  | "NON_EMERGENCY";


export interface AssessmentDetailResponse {
  assessment_id: string;

  encounter_id: string;

  neurology_department_id?: string | null;

  status: string;

  total_score: number | null;

  triage_priority: TriagePriority | null;

  onset_at?: string | null;

  lkw_at?: string | null;

  symptom_note?: string | null;

  created_at?: string | null;

  updated_at?: string | null;

  assigned_neurologist?: {
    id: string;
    name: string;
  } | null;

  items: AssessmentItem[];
}

export interface AssessmentEncounterListResponse {
  count: number;
  results: AssessmentDetailResponse[];
}

export interface CreateEncounterRequest {
  patient_id: string;
  encounter_type: "OUTPATIENT" | "EMERGENCY";
  appointment_id?: string;
}

export interface EncounterResponse {
  encounter_id: string;
  encounter_no: string;
  patient_id: string;
  appointment_id?: string | null;
  encounter_type: "OUTPATIENT" | "EMERGENCY";
  status: string;
  arrived_at: string;
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
  triage_priority: TriagePriority;
}


export interface CompleteAssessmentResponse {
  assessment_id: string;

  status: string;

  total_score: number;

  triage_priority: TriagePriority;

  assigned_neurologist_id: string;

  emergency_event_id: string | null;

  completed_at: string;
}


/* =========================================================
   Reference API
   소속 기관 / 진료과
   ========================================================= */

export interface HospitalListItem {
  id: string;
  name: string;
  address: string;
  phone: string | null;
  latitude: string | null;
  longitude: string | null;
  distance_km: number | null;
  is_favorite: boolean;
}

export interface HospitalListResponse {
  count: number;
  next: string | null;
  previous: string | null;
  results: HospitalListItem[];
}

export interface DepartmentItem {
  id: string;
  code: string;
  name: string;
}

export interface HospitalDepartmentResponse {
  hospital: {
    id: string;
    name: string;
  };
  departments: DepartmentItem[];
}


/* =========================================================
   진료과별 의료진 목록
   GET /api/v1/departments/{department_id}/clinicians
   ========================================================= */

export interface Clinician {
  id: string;
  user_id: string;
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
  /** Generic serializer 응답 호환용 원본 PK */
  id?: string;
  assessment_id: string | null;
  encounter_id: string;
  encounter_type?: string | null;
  patient_summary?: Record<string, unknown> | null;
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

// [추가] 신경과 응급 Worklist 연결
export interface EmergencyPatientSummary {
  patient_id?: string;
  id?: string;
  patient_no?: string;
  name?: string;
  sex?: string | null;
  age?: number | null;
  estimated_age?: number | null;
}

export interface EmergencyWorklistItem {
  assessment_id: string;
  encounter_id: string;
  patient_summary: EmergencyPatientSummary;
  total_score: number | null;
  triage_priority: string;
  lkw_at: string | null;
  event: {
    id: string;
    status: string;
    notified_at: string | null;
    acknowledged_at: string | null;
  };
}

export interface EmergencyWorklistResponse {
  count: number;
  next: string | null;
  previous: string | null;
  results: EmergencyWorklistItem[];
}
// [추가 끝] 신경과 응급 Worklist 연결



export interface TriageReview {
  review_id: string;
  assessment_id: string;
  priority: TriagePriority;
  reason: string;
  reviewer: {
    id: string;
    name: string;
  };
  reviewer_role: string;
  created_at: string;
}

export interface TriageReviewListResponse {
  initial_priority: TriagePriority | null;
  effective_priority: TriagePriority | null;
  latest_review: TriageReview | null;
  reviews: TriageReview[];
}

export interface CreateTriageReviewRequest {
  priority: TriagePriority;
  reason: string;
}
