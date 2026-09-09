import{apiRequest}from"../../api/client";import type{MedicationListResponse}from"./types";
export function searchMedications(search:string){return apiRequest<MedicationListResponse>(`/api/v1/medications?search=${encodeURIComponent(search)}&is_active=true`)}
