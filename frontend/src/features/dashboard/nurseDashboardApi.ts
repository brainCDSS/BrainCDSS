import { apiRequest } from "../../api/client";

import type {
  AssessmentWorklistResponse,
} from "../assessments/types";

import type {
  StaffAppointmentsResponse,
} from "../appointments/types";


function buildQuery(
  values: Record<
    string,
    string | number | undefined
  >,
) {
  const query = new URLSearchParams();

  Object.entries(values).forEach(
    ([key, value]) => {
      if (
        value !== undefined &&
        value !== ""
      ) {
        query.set(
          key,
          String(value),
        );
      }
    },
  );

  const text = query.toString();

  return text
    ? `?${text}`
    : "";
}


/**
 * 간호사 Dashboard
 * 선택 날짜 초기평가 Worklist
 *
 * GET /api/v1/assessments/worklist
 */
export function getNurseAssessmentWorklist(
  date: string,
) {
  return apiRequest<AssessmentWorklistResponse>(
    `/api/v1/assessments/worklist${buildQuery({
      date,
    })}`,
  );
}


/**
 * 간호사 Dashboard
 * 선택 날짜 예약 목록
 *
 * GET /api/v1/staff/appointments
 */
export function getNurseDashboardAppointments(
  date: string,
) {
  return apiRequest<StaffAppointmentsResponse>(
    `/api/v1/staff/appointments${buildQuery({
      date,
      page_size: 100,
    })}`,
  );
}