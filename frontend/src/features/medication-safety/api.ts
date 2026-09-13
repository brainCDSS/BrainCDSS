import { apiRequest } from "../../api/client";
import type {
  CreatePrescriptionRequest,
  FinalizePrescriptionResponse,
  MedicationListResponse,
  PrescriptionOverride,
  PrescriptionResponse,
  SafetyCheckRequest,
  SafetyCheckResponse,
  UpdatePrescriptionRequest,
} from "./types";

export function searchMedications(search: string) {
  const params = new URLSearchParams({ search, is_active: "true" });
  return apiRequest<MedicationListResponse>(`/api/v1/medications?${params}`);
}

export function checkPrescriptionSafety(payload: SafetyCheckRequest) {
  return apiRequest<SafetyCheckResponse>("/api/v1/prescriptions/safety-check", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
}

export function createPrescription(payload: CreatePrescriptionRequest) {
  return apiRequest<PrescriptionResponse>("/api/v1/prescriptions", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
}

export function getPrescription(id: string) {
  return apiRequest<PrescriptionResponse>(`/api/v1/prescriptions/${encodeURIComponent(id)}`);
}

export function updatePrescription(id: string, payload: UpdatePrescriptionRequest) {
  return apiRequest<PrescriptionResponse>(`/api/v1/prescriptions/${encodeURIComponent(id)}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
}

export function finalizePrescription(id: string, overrides: PrescriptionOverride[]) {
  return apiRequest<FinalizePrescriptionResponse>(
    `/api/v1/prescriptions/${encodeURIComponent(id)}/finalize`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ overrides }),
    },
  );
}
