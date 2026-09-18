import { apiRequest } from "../../api/client";
import type { ImagingOrderListResponse, ImagingOrderResponse, ImagingOrderTimelineResponse, ImagingSeriesResponse, ImagingStudy, ImagingStudyApiItem, ImagingStudyDetail, ImagingStudyListResponse, KeyImage, KeyImagesResponse, StudyAIHistoryResponse, StudyAIInputsResponse, ViewerContextResponse, ViewerSessionResponse } from "./types";
import type { NiftiViewerManifest } from "../ai-analysis/types";

function toScreenStudy(item: ImagingStudyApiItem): ImagingStudy {
  const sourceModality = Array.isArray(item.modalities)
    ? item.modalities[0]
    : item.modality;
  const modality = item.scan_type === "MRA"
    ? "MRA"
    : sourceModality === "MR"
      ? "MRI"
      : sourceModality ?? "";
  return {
    id: item.study_id,
    patient_id: item.patient?.patient_id ?? item.patient_id,
    patient_no: item.patient?.patient_no ?? item.patient_no,
    patient_name: item.patient?.name ?? item.patient_name,
    modality,
    series: `${item.series_count ?? 0} Series`,
    study_at: item.study_datetime,
    status: item.status ?? "UNKNOWN",
    accession_number: item.accession_number,
    series_count: item.series_count ?? 0,
    instance_count: item.instance_count ?? 0,
    latest_analysis: item.latest_analysis,
    current_report: item.current_report,
    critical_finding: item.critical_finding,
  };
}

export async function getImagingStudies(
  filters: { patientId?: string } = {},
): Promise<ImagingStudy[]> {
  const studies: ImagingStudy[] = [];
  let page = 1;
  let hasNext = true;
  while (hasNext) {
    const query = new URLSearchParams({ page: String(page) });
    if (filters.patientId) query.set("patient_id", filters.patientId);
    const response = await apiRequest<ImagingStudyListResponse>(`/api/v1/imaging-studies?${query}`);
    studies.push(...response.results.map(toScreenStudy));
    hasNext = Boolean(response.next);
    page += 1;
  }
  return studies;
}
export function getImagingStudy(studyId: string) { return apiRequest<ImagingStudyDetail>(`/api/v1/imaging-studies/${encodeURIComponent(studyId)}`); }
export function getImagingStudySeries(studyId: string) { return apiRequest<ImagingSeriesResponse>(`/api/v1/imaging-studies/${encodeURIComponent(studyId)}/series`); }
export function getStudyAIInputs(studyId: string) { return apiRequest<StudyAIInputsResponse>(`/api/v1/imaging-studies/${encodeURIComponent(studyId)}/ai-inputs`); }
export function getStudyNiftiViewerManifest(studyId: string) { return apiRequest<NiftiViewerManifest>(`/api/v1/imaging-studies/${encodeURIComponent(studyId)}/nifti-viewer`); }
export function getStudyAIAnalyses(studyId: string) { return apiRequest<StudyAIHistoryResponse>(`/api/v1/imaging-studies/${encodeURIComponent(studyId)}/ai-analyses`); }
export function getViewerContext(studyId: string, includeAIOverlay = true) { return apiRequest<ViewerContextResponse>(`/api/v1/imaging-studies/${encodeURIComponent(studyId)}/viewer-context?include_ai_overlay=${includeAIOverlay}`); }
export function getKeyImages(studyId: string) { return apiRequest<KeyImagesResponse>(`/api/v1/imaging-studies/${encodeURIComponent(studyId)}/key-images`); }
export function createViewerSession(studyId: string, payload: { purpose: "DIAGNOSIS" | "CONSULTATION" | "FOLLOW_UP"; include_ai_overlay: boolean }) { return apiRequest<ViewerSessionResponse>(`/api/v1/imaging-studies/${encodeURIComponent(studyId)}/viewer-session`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload) }); }
export function saveKeyImage(studyId: string, payload: { sop_instance_uid: string; frame_number?: number | null; label: string }) { return apiRequest<KeyImage>(`/api/v1/imaging-studies/${encodeURIComponent(studyId)}/key-images`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload) }); }
export function getImagingOrders(filters: { encounter_id?: string; patient_id?: string; status?: string } = {}) { const query = new URLSearchParams(Object.entries(filters).filter((entry): entry is [string, string] => Boolean(entry[1]))); return apiRequest<ImagingOrderListResponse>(`/api/v1/imaging-orders${query.size ? `?${query}` : ""}`); }
export function getImagingOrder(orderId: string) { return apiRequest<ImagingOrderResponse>(`/api/v1/imaging-orders/${encodeURIComponent(orderId)}`); }
export function createImagingOrder(payload: { encounter_id: string; patient_id: string; procedure_code: string; procedure_name: string; modality: "CT" | "MR" | "XA"; priority: "ROUTINE" | "URGENT" | "STAT"; reason: string }) { return apiRequest<ImagingOrderResponse>("/api/v1/imaging-orders", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload) }); }
export function updateImagingOrder(orderId: string, payload: { priority?: string; reason?: string; scheduled_at?: string }) { return apiRequest<ImagingOrderResponse>(`/api/v1/imaging-orders/${encodeURIComponent(orderId)}`, { method: "PATCH", headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload) }); }
export function cancelImagingOrder(orderId: string, reason: string) { return apiRequest<ImagingOrderResponse>(`/api/v1/imaging-orders/${encodeURIComponent(orderId)}/cancel`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ reason }) }); }
export function getImagingOrderTimeline(orderId: string) { return apiRequest<ImagingOrderTimelineResponse>(`/api/v1/imaging-orders/${encodeURIComponent(orderId)}/timeline`); }
