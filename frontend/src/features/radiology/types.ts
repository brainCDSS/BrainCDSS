export type ReportStatus = "NO_CURRENT_REPORT" | "DRAFT" | "PRELIMINARY" | "FINAL" | "AMENDED";
export interface RadiologyWorkItem {
  study_id: string;
  accession_number: string;
  patient?: { patient_id?: string; display?: string } | null;
  patient_id?: string;
  patient_name?: string;
  modality: string;
  priority: string;
  study_datetime: string;
  ai_status: string;
  report_status?: ReportStatus | null;
  status?: ReportStatus | null;
  critical_finding: boolean;
}
export interface RadiologyWorklistResponse { count:number; results:RadiologyWorkItem[]; next?:string|null; previous?:string|null; }
export interface RadiologyReport { report_id:string; study_id:string; status:ReportStatus; version:number; findings:string; impression:string; recommendation:string; author?:{user_id:string}; finalized_by?:{user_id:string}|null; finalized_at?:string|null; critical_finding:boolean; critical_level:string; }

export interface RadiologyReportDraft {
  reportId?: string;
  studyId: string;
  analysisId: string;
  accessionNumber: string;
  analysisType: string;
  finding: string;
  lesionCount: number | null;
  totalVolumeMl: number | null;
}
