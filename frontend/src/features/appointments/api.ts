import { apiRequest } from "../../api/client";
import type {
  AppointmentActionResponse,
  AppointmentRequestResponse,
  ScheduleResponse,
  ScheduleRule,
  StaffAppointment,
  StaffAppointmentsResponse,
} from "./types";

function queryString(values: Record<string, string | number | undefined>) {
  const query = new URLSearchParams();
  Object.entries(values).forEach(([key, value]) => {
    if (value !== undefined && value !== "") query.set(key, String(value));
  });
  const text = query.toString();
  return text ? `?${text}` : "";
}

export function getStaffAppointments(filters: { date?: string; clinicianId?: string; status?: string; page?: number; pageSize?: number }) {
  return apiRequest<StaffAppointmentsResponse>(`/api/v1/staff/appointments${queryString({
    date: filters.date,
    clinician_id: filters.clinicianId,
    status: filters.status,
    page: filters.page,
    page_size: filters.pageSize,
  })}`);
}

export function getAppointmentDetail(appointmentId: string) {
  return apiRequest<StaffAppointment & { id?: string }>(`/api/v1/appointments/${encodeURIComponent(appointmentId)}`);
}

export function completeAppointment(appointmentId: string) {
  return apiRequest<AppointmentActionResponse>(`/api/v1/appointments/${encodeURIComponent(appointmentId)}/complete`, { method: "POST" });
}

export function getAppointmentRequests(filters: { date?: string; clinicianId?: string }) {
  return apiRequest<AppointmentRequestResponse>(`/api/v1/nurse/appointments/requests${queryString({ date: filters.date, clinician_id: filters.clinicianId })}`);
}

export function acceptAppointment(appointmentId: string, memo?: string) {
  return apiRequest<AppointmentActionResponse>(`/api/v1/appointments/${encodeURIComponent(appointmentId)}/accept`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(memo ? { memo } : {}),
  });
}

export function rejectAppointment(appointmentId: string, rejectionReason: string) {
  return apiRequest<AppointmentActionResponse>(`/api/v1/appointments/${encodeURIComponent(appointmentId)}/reject`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ rejection_reason: rejectionReason }),
  });
}

export function getClinicianSchedule(clinicianId: string, from?: string, to?: string) {
  return apiRequest<ScheduleResponse>(`/api/v1/clinicians/${encodeURIComponent(clinicianId)}/schedule${queryString({ from, to })}`);
}

export function saveClinicianSchedule(clinicianId: string, schedules: ScheduleRule[]) {
  return apiRequest<ScheduleResponse>(`/api/v1/clinicians/${encodeURIComponent(clinicianId)}/schedule`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ schedules }),
  });
}
