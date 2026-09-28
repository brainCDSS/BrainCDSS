import type { InitialAssessmentLike } from "../assessments/viewModel";

export interface Patient{
    id: string;
    patient_no: string;
    name: string;
    birth_date: string | null;
    estimated_age: number |null;
    sex: string |null;
    phone: string | null;
    allergy_info: string | null;
    status: string;

}

/** GET /api/v1/patients/{patient_id} 응답 */
export interface PatientDetail extends Patient {
  latest_assessment?: InitialAssessmentLike | null;
  emergency_contact: string | null;
  pregnancy_status: string;
  pregnancy_status_updated_at: string | null;
  merged_into: { id: string; patient_no: string } | null;
  resolved_from_patient_id: string | null;
  merged_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface PatientListResponse {
  count: number;
  next: string | null;
  previous: string | null;
  results: Patient[];
}
