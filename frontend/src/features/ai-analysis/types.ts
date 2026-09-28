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
  failure_code?: string | null;
  model?: { code: string; version: string };
  requested_at: string;
  completed_at?: string | null;
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
  is_positive: boolean | null;
  confidence: number | null;
  threshold_used: number | null;
  lesion_count: number | null;
  total_volume_ml: number | null;
  severity: string;
  structured_findings: Record<string, unknown>;
  artifacts: Array<{ artifact_id?: string; type: string; sop_instance_uid: string }>;
  latest_review?: { decision: string } | null;
}

export interface AIAnalysisDetail extends AIAnalysisItem {
  failure_code?: string | null;
}
export interface AIResultReview {
  review_id: string; result_id: string; decision: "ACCEPT" | "MODIFY" | "REJECT";
  comment: string; corrected_findings?: Record<string, unknown>; reviewer_id?: string;
  reviewer?: { user_id: string; name: string; role_code: string; role_name: string };
  reviewed_at: string;
}
export interface AIResultReviewList { result_id: string; reviews: AIResultReview[] }
export interface NiftiViewerAsset { artifact_id?: string; type?: string; role?: string | null; url: string }
export interface NiftiViewerManifest {
  analysis_id: string;
  inputs: Array<{ role: string; url: string }>;
  masks: NiftiViewerAsset[];
  probabilities?: NiftiViewerAsset[];
  components?: NiftiViewerAsset[];
  xai?: NiftiViewerAsset[];
}
export interface NiftiProbe {
  voxel: [number, number, number]; slice: number; sourceRole: string; sourceValue: number | null;
  dwiValue?: number | null; adcValue?: number | null; probability?: number | null; maskValue?: number | null; xaiValue?: number | null; componentId?: number | null;
}
