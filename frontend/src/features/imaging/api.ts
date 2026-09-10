import { apiRequest } from "../../api/client";
import type { ImagingSeriesResponse, ImagingStudy, ImagingStudyApiItem, ImagingStudyDetail, ImagingStudyListResponse, KeyImagesResponse, StudyAIHistoryResponse, ViewerContextResponse } from "./types";

function toScreenStudy(item: ImagingStudyApiItem): ImagingStudy {
  const modality = item.scan_type === "MRA" ? "MRA" : item.modalities[0] === "MR" ? "MRI" : item.modalities[0] ?? "";
  return {
    id: item.study_id,
    patient_id: item.patient?.patient_id ?? item.patient_id,
    patient_no: item.patient?.patient_no ?? item.patient_no,
    patient_name: item.patient?.name ?? item.patient_name,
    modality,
    series: `${item.series_count} Series`,
    study_at: item.study_datetime,
    status: item.status,
    accession_number: item.accession_number,
    series_count: item.series_count,
    instance_count: item.instance_count,
    latest_analysis: item.latest_analysis,
    current_report: item.current_report,
    critical_finding: item.critical_finding,
  };
}

export async function getImagingStudies(): Promise<ImagingStudy[]> {
  const studies: ImagingStudy[] = [];
  let page = 1;
  let hasNext = true;
  while (hasNext) {
    const response = await apiRequest<ImagingStudyListResponse>(`/api/v1/imaging-studies?page=${page}`);
    studies.push(...response.results.map(toScreenStudy));
    hasNext = Boolean(response.next);
    page += 1;
  }
  return studies;
}
export function getImagingStudy(studyId: string) { return apiRequest<ImagingStudyDetail>(`/api/v1/imaging-studies/${encodeURIComponent(studyId)}`); }
export function getImagingStudySeries(studyId: string) { return apiRequest<ImagingSeriesResponse>(`/api/v1/imaging-studies/${encodeURIComponent(studyId)}/series`); }
export function getStudyAIAnalyses(studyId: string) { return apiRequest<StudyAIHistoryResponse>(`/api/v1/imaging-studies/${encodeURIComponent(studyId)}/ai-analyses`); }
export function getViewerContext(studyId: string, includeAIOverlay = true) { return apiRequest<ViewerContextResponse>(`/api/v1/imaging-studies/${encodeURIComponent(studyId)}/viewer-context?include_ai_overlay=${includeAIOverlay}`); }
export function getKeyImages(studyId: string) { return apiRequest<KeyImagesResponse>(`/api/v1/imaging-studies/${encodeURIComponent(studyId)}/key-images`); }
