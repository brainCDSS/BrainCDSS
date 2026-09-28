import { apiRequest } from "../../api/client";
import type {
  CreatePrescriptionRequest,
  CurrentMedicationListResponse,
  EncounterListItem,
  EncounterListResponse,
  FinalizePrescriptionResponse,
  MedicationListResponse,
  PrescriptionOverride,
  PrescriptionResponse,
  SafetyCheckRequest,
  SafetyCheckResponse,
  UpdatePrescriptionRequest,
} from "./types";

export function getCurrentMedications(patientId: string) {
  return apiRequest<CurrentMedicationListResponse>(
    `/api/v1/patients/${encodeURIComponent(patientId)}/current-medications`,
  );
}

export async function getPatientEncounters(patientId: string) {
  const params = new URLSearchParams({ patient_id: patientId });
  const response = await apiRequest<EncounterListResponse | EncounterListItem[]>(
    `/api/v1/encounters?${params}`,
  );
  return Array.isArray(response) ? response : response.results;
}

export async function getActiveEncounter(patientId: string) {
  const encounters = await getPatientEncounters(patientId);
  return encounters
    .filter((encounter) =>
      encounter.patient_id === patientId &&
      (encounter.status === "IN_PROGRESS" || encounter.status === "REGISTERED"),
    )
    .sort((left, right) => {
      const statusOrder = (status: string) => status === "IN_PROGRESS" ? 0 : 1;
      return statusOrder(left.status) - statusOrder(right.status) ||
        (right.started_at ?? right.arrived_at ?? "").localeCompare(
          left.started_at ?? left.arrived_at ?? "",
        );
    })[0] ?? null;
}

export function searchMedications(search: string, diseaseGroup = "") {
  const params = new URLSearchParams({ is_active: "True" });
  if (search) params.set("search", search);
  if (diseaseGroup) params.set("disease_group", diseaseGroup);
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
  return apiRequest<PrescriptionResponse>(
    `/api/v1/prescriptions/${encodeURIComponent(id)}`,
  );
}

export function updatePrescription(
  id: string,
  payload: UpdatePrescriptionRequest,
) {
  return apiRequest<PrescriptionResponse>(
    `/api/v1/prescriptions/${encodeURIComponent(id)}`,
    {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    },
  );
}

export function finalizePrescription(
  id: string,
  overrides: PrescriptionOverride[],
) {
  return apiRequest<FinalizePrescriptionResponse>(
    `/api/v1/prescriptions/${encodeURIComponent(id)}/finalize`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ overrides }),
    },
  );
}
