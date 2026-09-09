export type ImagingFilter =
  | "ALL"
  | "CT"
  | "MRI"
  | "MRA";


export type ImagingModality =
  | "CT"
  | "MRI"
  | "MRA";


export type ImagingSource =
  | "ORTHANC"
  | "UPLOAD";


export type AnalysisType =
  | "HEMORRHAGE"
  | "ISCHEMIA"
  | "ANEURYSM";


export type ImagingStatus =
  | "READY"
  | "REVIEW_REQUIRED"
  | "QUEUED";


export interface ImagingStudy {
  id: string;

  patient_id: string;
  patient_no: string;
  patient_name: string;

  modality: ImagingModality;
  series: string;

  study_at: string;

  source: ImagingSource;

  recommended_analysis: AnalysisType;

  status: ImagingStatus;
}