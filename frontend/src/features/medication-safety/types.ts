export interface MedicationItem {
  id: string;
  medication_code: string;
  medication_name: string;
  dosage_form: string;
  strength: string;
  manufacturer: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface MedicationListResponse {
  count: number;
  next: string | null;
  previous: string | null;
  results: MedicationItem[];
}

export interface PrescriptionItemInput {
  item_id?: string | null;
  medication_id: string;
  dose: number;
  dose_unit: string;
  route: string;
  frequency_per_day: number;
  timing: string;
  start_date: string;
  duration_days: number;
  instructions: string;
}

export interface PrescriptionItemResponse extends PrescriptionItemInput {
  item_id: string;
  medication_code: string;
  medication_name: string;
}

export interface CreatePrescriptionRequest {
  encounter_id: string;
  items: PrescriptionItemInput[];
}

export interface UpdatePrescriptionRequest {
  items: PrescriptionItemInput[];
}

export interface PrescriptionResponse {
  prescription_id: string;
  status: "DRAFT" | "FINAL" | string;
  items: PrescriptionItemResponse[];
  created_at?: string;
  updated_at?: string;
  finalized_at?: string | null;
  doctor?: string | null;
  department?: string | null;
}

export type DurAlertType = "DDI" | "DOSE" | "DUPLICATE" | "AGE" | "ELDERLY" | "PREGNANCY" | "DURATION" | "ALLERGY";
export type DurSeverity = "BLOCK" | "MAJOR" | "WARNING" | "INFO";

export interface DurAlert {
  alert_type: DurAlertType;
  severity: DurSeverity;
  message: string | null;
  rule_id: string;
  related_medications: string[];
  override_allowed: boolean;
  observed_daily_dose_mg?: number;
  max_daily_dose_mg?: number;
  observed_duration_days?: number;
  max_duration_days?: number;
}

export interface SafetyCheckRequest {
  patient_id: string;
  medications: Array<{
    medication_id: string;
    dose: number;
    unit: string;
    frequency_per_day: number;
    duration_days: number;
    route?: string;
  }>;
  draft_prescription_id?: string;
}

export interface SafetyCheckResponse {
  safe: boolean;
  alerts: DurAlert[];
  context: { pregnancy_status: string | null; patient_age: number | null; checked_at: string };
}

export interface PrescriptionOverride {
  alert_type: string;
  rule_type: string;
  rule_id: string;
  reason: string;
}

export interface FinalizePrescriptionResponse {
  prescription_id: string;
  status: "FINAL";
  finalized_at: string;
  safety: {
    safe: boolean;
    alerts: DurAlert[];
    overrides: Array<{ override_id: string; alert_type: string; severity: string; reason: string }>;
  };
  schedules_created: number;
}
