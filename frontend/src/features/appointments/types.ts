export type AppointmentStatus =
  | "REQUESTED"
  | "CONFIRMED"
  | "IN_PROGRESS"
  | "COMPLETED"
  | "CANCELLED"
  | "REJECTED"
  | string;

export interface EntitySummary {
  id: string;
  name: string;
  patient_no?: string;
}

export interface HospitalListResponse {
  count: number;
  results: Array<{
    id: string;
    name: string;
  }>;
}

export interface HospitalDetailResponse {
  id: string;
  name: string;
  departments: Array<{
    id: string;
    code: string;
    name: string;
  }>;
}

export interface StaffAppointment {
  appointment_id: string;
  patient?: EntitySummary;
  patient_id?: string;
  hospital?: EntitySummary;
  hospital_id?: string;
  department?: EntitySummary;
  department_id?: string;
  clinician?: EntitySummary;
  clinician_id?: string;

  slot?: {
    id: string;
    start_at?: string;
    end_at?: string;
    status?: string;
  };

  slot_id?: string;

  requested_slot?: {
    id: string;
    start_at?: string;
    status?: string;
  } | null;

  requested_slot_id?: string | null;

  status: AppointmentStatus;
  request_type?: string;

  start_at?: string;
  end_at?: string;

  requested_at?: string;
  reschedule_requested_at?: string | null;

  confirmed_at?: string | null;

  rejection_reason?: string | null;

  cancel_reason?: string | null;
  cancelled_at?: string | null;

  completed_at?: string | null;

  handled_by?: EntitySummary | null;
  handled_by_id?: string | null;
}

export interface StaffAppointmentsResponse {
  from?: string;
  to?: string;
  clinician?: EntitySummary;

  appointments?: StaffAppointment[];

  count?: number;
  next?: string | number | null;
  previous?: string | number | null;

  results?: Array<
    StaffAppointment & {
      id?: string;
    }
  >;
}

export interface AppointmentRequestResponse {
  count: number;

  next?: string | null;
  previous?: string | null;

  results: Array<
    StaffAppointment & {
      id?: string;
    }
  >;
}

export interface ScheduleRule {
  id?: string;
  clinician_id?: string;

  weekday: number;

  start_time: string;
  end_time: string;

  slot_minutes: number;

  effective_from: string;
  effective_to: string | null;

  is_active: boolean;
}

export interface ScheduleResponse {
  clinician?: EntitySummary;

  rules?: ScheduleRule[];
  results?: ScheduleRule[];

  generated_slot_count?: number;
  preserved_occupied_slot_count?: number;

  updated_at?: string;

  count?: number;
}

export interface AppointmentActionResponse {
  id?: string;
  appointment_id?: string;

  status: AppointmentStatus;

  completed_at?: string | null;
  rejected_at?: string | null;
  confirmed_at?: string | null;
}

/* =========================================================
 * 예약 상태 정정
 * ---------------------------------------------------------
 * [API 추가 요청 필요]
 *
 * 상태 오처리 시 정정 API에서 사용할 요청 타입.
 * 실제 정정 가능 상태 전이는 백엔드 계약에서 제한한다.
 * ======================================================= */

export interface AppointmentCorrectionRequest {
  target_status: AppointmentStatus;
  reason: string;
}

/*
 * 현재 정정 API 응답 명세가 확정되지 않았으므로
 * 기존 AppointmentActionResponse 형식을 기준으로 사용한다.
 *
 * 백엔드에서 previous_status, corrected_at 등
 * 추가 응답 필드가 확정될 경우 이후 확장한다.
 */
export type AppointmentCorrectionResponse =
  AppointmentActionResponse;
