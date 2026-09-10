export type ImagingFilter =
  | "ALL"
  | "CT"
  | "MRI"
  | "MRA";

export type ImagingModality =
  | "CT"
  | "MRI"
  | "MRA"
  | "MR"
  | string;

export type ImagingSource =
  | "ORTHANC"
  | "UPLOAD";

export type AnalysisType =
  | "HEMORRHAGE"
  | "ISCHEMIA"
  | "ANEURYSM";

export type ImagingStatus =
  | "RECEIVING"
  | "AVAILABLE"
  | "INCOMPLETE"
  | "UNMATCHED"
  | "ERROR"
  | string;

export interface ImagingAnalysisSummary {
  analysis_id: string;
  status: string;
}

export interface ImagingReportSummary {
  report_id: string;
  status: string;
}

export interface ImagingPatientSummary {
  patient_id: string;
  patient_no?: string;
  name?: string;
}

export interface ImagingStudyApiItem {
  study_id: string;
  accession_number: string;
  study_datetime: string;
  modalities: string[];

  status: ImagingStatus;
  series_count: number;
  instance_count: number;

  latest_analysis: ImagingAnalysisSummary | null;
  current_report: ImagingReportSummary | null;
  critical_finding: boolean;

  patient?: ImagingPatientSummary | null;
  patient_id?: string;
  patient_no?: string;
  patient_name?: string;
  scan_type?: string;
}

export interface ImagingStudyListResponse {
  count: number;
  next: string | null;
  previous: string | null;
  results: ImagingStudyApiItem[];
}

export interface ImagingSeries {
  series_id: string;
  series_instance_uid: string;
  series_number?: number;
  modality: string;
  series_description?: string;

  instance_count: number;
  slice_thickness?: number | null;
  is_complete: boolean;
  is_ai_eligible: boolean;
  ai_exclusion_reason?: string;
}

export interface ImagingStudyDetail {
  study_id: string;
  study_instance_uid: string;
  accession_number: string;
  study_datetime: string;
  status: ImagingStatus;

  patient: ImagingPatientSummary | null;
  series: ImagingSeries[];
  latest_analysis: ImagingAnalysisSummary | null;
  current_report: ImagingReportSummary | null;
}

export interface ImagingSeriesResponse {
  study_id: string;
  series: ImagingSeries[];
}

export interface StudyAIHistoryResponse {
  study_id: string;

  results: Array<
    ImagingAnalysisSummary & {
      analysis_type: string;
      stage: string;

      model?: {
        code: string;
        version: string;
      };

      attempt_count: number;
      requested_at: string;

      result_summary?: {
        is_positive?: boolean;
        total_volume_ml?: number;
      } | null;
    }
  >;
}

export interface ViewerContextResponse {
  study: Record<string, unknown>;
  viewer_session: Record<string, unknown>;
  series: ImagingSeries[];
  ai: Record<string, unknown> | null;
  final_report: Record<string, unknown> | null;
}

export interface KeyImage {
  key_image_id: string;
  sop_instance_uid: string;
  frame_number?: number | null;
  label: string;
  selected_by: unknown;
  selected_at: string;
}

export interface KeyImagesResponse {
  results: KeyImage[];
}

/**
 * Existing UI model.
 * API에 없는 값은 생성하지 않고 undefined로 둔다.
 */
export interface ImagingStudy {
  id: string;

  patient_id?: string;
  patient_no?: string;
  patient_name?: string;

  modality: ImagingModality;

  series: string;
  study_at: string;

  /**
   * 현재 Imaging Study API 응답에 없는 UI 호환 필드.
   * API에서 값이 없으면 undefined.
   */
  source?: ImagingSource;

  recommended_analysis?: AnalysisType;

  status: ImagingStatus;

  accession_number: string;

  series_count: number;
  instance_count: number;

  latest_analysis: ImagingAnalysisSummary | null;
  current_report: ImagingReportSummary | null;

  critical_finding: boolean;
}