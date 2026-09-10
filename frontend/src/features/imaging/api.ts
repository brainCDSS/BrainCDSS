import { apiRequest } from "../../api/client";

import type {
  AnalysisType,
  ImagingModality,
  ImagingStudy,
} from "./types";


interface ImagingStudyApiItem {
  id?: string;
  study_id?: string;
  patient_id?: string | null;
  patient_no?: string;
  patient_name?: string;
  accession_number?: string;
  study_datetime?: string;
  modalities?: string[];
  study_description?: string;
  orthanc_study_id?: string | null;
  orthanc_study?: string | null;
  status?: string;
}

interface ImagingStudyListResponse {
  results?: ImagingStudyApiItem[];
}


function modalityFor(item: ImagingStudyApiItem): ImagingModality {
  const modalities = item.modalities ?? [];
  const description = (item.study_description ?? "").toUpperCase();

  if (modalities.includes("CT")) return "CT";
  if (description.includes("MRA") || description.includes("ANGIO")) return "MRA";
  return "MRI";
}


function analysisFor(modality: ImagingModality): AnalysisType {
  if (modality === "CT") return "HEMORRHAGE";
  if (modality === "MRA") return "ANEURYSM";
  return "ISCHEMIA";
}


function normalizeStudy(item: ImagingStudyApiItem): ImagingStudy {
  const modality = modalityFor(item);
  const status = item.status === "AVAILABLE"
    ? "READY"
    : item.status === "RECEIVING"
      ? "QUEUED"
      : "REVIEW_REQUIRED";

  return {
    id: item.study_id ?? item.id ?? "",
    patient_id: item.patient_id ?? "",
    patient_no: item.patient_no ?? "-",
    patient_name: item.patient_name ?? "-",
    modality,
    series: item.study_description ?? item.accession_number ?? "-",
    study_at: item.study_datetime ?? "",
    source: item.orthanc_study_id || item.orthanc_study ? "ORTHANC" : "UPLOAD",
    recommended_analysis: analysisFor(modality),
    status,
  };
}


export async function getImagingStudies(): Promise<ImagingStudy[]> {
  const response = await apiRequest<ImagingStudyListResponse | ImagingStudyApiItem[]>(
    "/api/v1/imaging-studies",
  );

  const items = Array.isArray(response) ? response : response.results ?? [];
  return items.map(normalizeStudy).filter((study) => study.id !== "");
}
