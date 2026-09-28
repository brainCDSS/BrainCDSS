import { apiRequest } from "../../api/client";

import type {
  AppointmentActionResponse,
  AvailableSlotsResponse,
  AppointmentCorrectionRequest,
  AppointmentCorrectionResponse,
  AppointmentRequestResponse,
  HospitalDetailResponse,
  HospitalListResponse,
  ScheduleResponse,
  ScheduleRule,
  StaffAppointment,
  StaffAppointmentsResponse,
} from "./types";

export function getAvailableSlots(clinicianId: string, date: string) {
  return apiRequest<AvailableSlotsResponse>(
    `/api/v1/clinicians/${encodeURIComponent(clinicianId)}/slots${queryString({ date })}`,
  );
}

export function createStaffAppointment(patientId: string, slotId: string) {
  return apiRequest<StaffAppointment>("/api/v1/staff/appointment-bookings", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ patient_id: patientId, slot_id: slotId }),
  });
}

export function getActiveHospitals() {
  return apiRequest<HospitalListResponse>(
    "/api/v1/hospitals?page=1",
  );
}

export function getHospitalDetail(hospitalId: string) {
  return apiRequest<HospitalDetailResponse>(
    `/api/v1/hospitals/${encodeURIComponent(hospitalId)}`,
  );
}

function queryString(values: Record<string, string | number | undefined>) {
  const query = new URLSearchParams();

  Object.entries(values).forEach(([key, value]) => {
    if (value !== undefined && value !== "") {
      query.set(key, String(value));
    }
  });

  const text = query.toString();

  return text ? `?${text}` : "";
}

/* =========================================================
 * 의료진 예약 목록
 * ======================================================= */

export function getStaffAppointments(filters: {
  date?: string;
  from?: string;
  to?: string;
  clinicianId?: string;
  status?: string;
  page?: number;
  pageSize?: number;
}) {
  return apiRequest<StaffAppointmentsResponse>(
    `/api/v1/staff/appointments${queryString({
      date: filters.date,
      from: filters.from,
      to: filters.to,
      clinician_id: filters.clinicianId,
      status: filters.status,
      page: filters.page,
      page_size: filters.pageSize,
    })}`,
  );
}

/* =========================================================
 * 예약 상세
 * ======================================================= */

export function getAppointmentDetail(appointmentId: string) {
  return apiRequest<StaffAppointment & { id?: string }>(
    `/api/v1/appointments/${encodeURIComponent(appointmentId)}`,
  );
}

/* =========================================================
 * 진료 완료
 * ======================================================= */

export function completeAppointment(appointmentId: string) {
  return apiRequest<AppointmentActionResponse>(
    `/api/v1/appointments/${encodeURIComponent(appointmentId)}/complete`,
    {
      method: "POST",
    },
  );
}

/* =========================================================
 * 간호사 예약 요청 목록
 * ======================================================= */

export function getAppointmentRequests(filters: {
  date?: string;
  clinicianId?: string;
  page?: number;
  pageSize?: number;
}) {
  return apiRequest<AppointmentRequestResponse>(
    `/api/v1/nurse/appointments/requests${queryString({
      date: filters.date,
      clinician_id: filters.clinicianId,
      page: filters.page,
      page_size: filters.pageSize,
    })}`,
  );
}

/* =========================================================
 * 예약 승인
 * ======================================================= */

export function acceptAppointment(
  appointmentId: string,
  memo?: string,
) {
  return apiRequest<AppointmentActionResponse>(
    `/api/v1/appointments/${encodeURIComponent(appointmentId)}/accept`,
    {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(memo ? { memo } : {}),
    },
  );
}

/* =========================================================
 * 예약 거절
 * ======================================================= */

export function rejectAppointment(
  appointmentId: string,
  rejectionReason: string,
) {
  return apiRequest<AppointmentActionResponse>(
    `/api/v1/appointments/${encodeURIComponent(appointmentId)}/reject`,
    {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        rejection_reason: rejectionReason,
      }),
    },
  );
}

/* =========================================================
 * 예약 상태 정정
 * ---------------------------------------------------------
 * [API 추가 요청 필요]
 *
 * 예정 계약:
 * POST /api/v1/appointments/{appointment_id}/correct
 *
 * Request:
 * {
 *   target_status: string,
 *   reason: string
 * }
 *
 * 백엔드 API 계약 확정 시 endpoint / request body를
 * 최종 명세에 맞춰 확인해야 한다.
 * ======================================================= */

export function correctAppointment(
  appointmentId: string,
  payload: AppointmentCorrectionRequest,
) {
  return apiRequest<AppointmentCorrectionResponse>(
    `/api/v1/appointments/${encodeURIComponent(appointmentId)}/correct`,
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
 * 의료진 스케줄 조회
 * ======================================================= */

export function getClinicianSchedule(
  clinicianId: string,
  from?: string,
  to?: string,
) {
  return apiRequest<ScheduleResponse>(
    `/api/v1/clinicians/${encodeURIComponent(clinicianId)}/schedule${queryString({
      from,
      to,
    })}`,
  );
}

/* =========================================================
 * 의료진 스케줄 저장
 * ======================================================= */

export function saveClinicianSchedule(
  clinicianId: string,
  schedules: ScheduleRule[],
) {
  return apiRequest<ScheduleResponse>(
    `/api/v1/clinicians/${encodeURIComponent(clinicianId)}/schedule`,
    {
      method: "PUT",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        schedules,
      }),
    },
  );
}
