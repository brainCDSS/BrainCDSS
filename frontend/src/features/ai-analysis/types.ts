export type AIAnalysisStatus =
  | "QUEUED"
  | "PROCESSING"
  | "COMPLETED"
  | "FAILED"
  | "RETRYING"
  | "CANCELLED";

export interface AIAnalysisItem {
  analysis_id: string;
  study_id: string;
  analysis_type: string;
  status: AIAnalysisStatus;
  stage: string;
  priority: string;
  attempt_count: number;
  model?: { code: string; version: string };
  requested_at: string;
}

export interface AIAnalysisListResponse {
  count: number;
  next?: string | number | null;
  previous?: string | number | null;
  results: AIAnalysisItem[];
}

export interface AIAnalysisResult {
  analysis_id: string;
  result_id: string;
  output_schema_version: string;
  is_positive: boolean;
  confidence: number;
  threshold_used: number;
  lesion_count: number;
  total_volume_ml: number;
  severity: string;
  structured_findings: Record<string, unknown>;
  artifacts: Array<{ type: string; sop_instance_uid: string }>;
  latest_review?: { decision: string } | null;
}
