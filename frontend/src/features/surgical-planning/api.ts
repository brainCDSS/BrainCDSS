/** Surgical planning persistence API. */

import { apiRequest } from "../../api/client";
import type {
  CreateSurgicalPlanClipRequest, CreateSurgicalPlanRequest,
  SurgicalPlanApi, SurgicalPlanClipApi, SurgicalPlanClipListApi,
  SurgicalPlanListApi, SurgicalPlanMessageApi, SurgicalPlanMessageListApi,
  UpdateSurgicalPlanClipRequest, UpdateSurgicalPlanRequest,
} from "./types";

const jsonRequest = (method: string, body: unknown): RequestInit => ({
  method,
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify(body),
});

export function getSurgicalPlans(query: { patient_id?: string; study_id?: string; status?: string } = {}) {
  const params = new URLSearchParams();
  Object.entries(query).forEach(([key, value]) => { if (value) params.set(key, value); });
  const suffix = params.size ? `?${params.toString()}` : "";
  return apiRequest<SurgicalPlanListApi>(`/api/v1/surgical-plans${suffix}`);
}

export function getSurgicalPlan(planningId: string) {
  return apiRequest<SurgicalPlanApi>(`/api/v1/surgical-plans/${encodeURIComponent(planningId)}`);
}

export function createSurgicalPlan(payload: CreateSurgicalPlanRequest) {
  return apiRequest<SurgicalPlanApi>("/api/v1/surgical-plans", jsonRequest("POST", payload));
}

export function updateSurgicalPlan(planningId: string, payload: UpdateSurgicalPlanRequest) {
  return apiRequest<SurgicalPlanApi>(`/api/v1/surgical-plans/${encodeURIComponent(planningId)}`, jsonRequest("PATCH", payload));
}

export function saveSurgicalPlanDraft(planningId: string, payload: UpdateSurgicalPlanRequest) {
  return apiRequest<SurgicalPlanApi>(`/api/v1/surgical-plans/${encodeURIComponent(planningId)}/draft`, jsonRequest("POST", payload));
}

export function confirmSurgicalPlan(planningId: string, version: number) {
  return apiRequest<SurgicalPlanApi>(`/api/v1/surgical-plans/${encodeURIComponent(planningId)}/confirm`, jsonRequest("POST", { version }));
}

export function getSurgicalPlanClips(planningId: string) {
  return apiRequest<SurgicalPlanClipListApi>(`/api/v1/surgical-plans/${encodeURIComponent(planningId)}/clips`);
}

export function createSurgicalPlanClip(planningId: string, payload: CreateSurgicalPlanClipRequest) {
  return apiRequest<SurgicalPlanClipApi>(`/api/v1/surgical-plans/${encodeURIComponent(planningId)}/clips`, jsonRequest("POST", payload));
}

export function updateSurgicalPlanClip(planningId: string, clipId: string, payload: UpdateSurgicalPlanClipRequest) {
  return apiRequest<SurgicalPlanClipApi>(`/api/v1/surgical-plans/${encodeURIComponent(planningId)}/clips/${encodeURIComponent(clipId)}`, jsonRequest("PATCH", payload));
}

export function deleteSurgicalPlanClip(planningId: string, clipId: string) {
  return apiRequest<void>(`/api/v1/surgical-plans/${encodeURIComponent(planningId)}/clips/${encodeURIComponent(clipId)}`, { method: "DELETE" });
}

export function getSurgicalPlanMessages(planningId: string) {
  return apiRequest<SurgicalPlanMessageListApi>(`/api/v1/surgical-plans/${encodeURIComponent(planningId)}/messages`);
}

export function createSurgicalPlanMessage(planningId: string, payload: { message: string; viewer_state?: Record<string, unknown> }) {
  return apiRequest<SurgicalPlanMessageApi>(`/api/v1/surgical-plans/${encodeURIComponent(planningId)}/messages`, jsonRequest("POST", payload));
}
