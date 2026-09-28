import type {
  RoleCode,
} from "../auth/types";


export interface AdminUser {
  id: string;
  login_id: string;
  name: string;
  email: string | null;

  role: {
    code: RoleCode;
    name: string;
  };

  is_active: boolean;
  last_login: string | null;
  created_at: string;
}


export interface AdminPermission {
  code: string;
  name: string;
  domain: string;
}


export interface AdminRole {
  id: string;
  code: RoleCode;
  name: string;
  description: string | null;
  is_active: boolean;
  permissions: AdminPermission[];
}


export interface AdminUserCreatePayload {
  login_id: string;
  name: string;
  email?: string | null;
  role_id: string;
  temp_password: string;
}


export interface AdminUserUpdatePayload {
  name?: string;
  email?: string | null;
  role_id?: string;
  is_active?: boolean;
}


export interface RolePermissionUpdateResponse {
  role: {
    id?: string;
    code?: string;
    name?: string;
  };

  permissions: AdminPermission[];
  updated_at: string;
}


export interface AuditLogItem {
  audit_id: string;
  actor_login_id: string | null;
  actor_role_code: string | null;
  action: string;
  resource_type: string;
  resource_id: string | null;
  outcome: string;
  request_id: string | null;
  tracking_code: string | null;
  occurred_at: string;
}


export interface PaginatedResponse<T> {
  count: number;
  next: string | null;
  previous: string | null;
  results: T[];
}


export interface ServiceStatusItem {
  service: string;
  status:
    | "정상"
    | "확인 실패"
    | "API 미연결";
  checkedAt: string;
  message: string;
}


export interface AnalysisStatusItem {
  type: string;
  completed: number | null;
  running: number | null;
  failed: number | null;
}

export interface MLModelSummary {
  model_id: string;
  code: string;
  display_name: string;
  task_type: string;
  disease_scope: string;
  supported_modalities: string[];
  is_enabled: boolean;
}

export interface MLModelVersionSummary {
  version_id: string;
  model_id: string;
  model_code: string;
  model_name: string;
  version: string;
  mlflow_registered_model_name: string;
  mlflow_model_version: string;
  mlflow_run_id: string;
  artifact_uri: string;
  experiment_id: string;
  model_bundle_uri: string;
  manifest_uri: string;
  checkpoint_uri: string;
  validation_status: "DRAFT" | "VALIDATED" | "APPROVED" | "RETIRED";
  is_active: boolean;
  performance_metrics: Record<string, unknown>;
  created_at: string;
  updated_at: string;
}

export interface MLRoutingConfig {
  routing_id: string;
  version: string;
  modality: "CT" | "MR" | "MRA";
  analysis_type: string;
  is_active: boolean;
  created_at: string;
  target_model_version: MLModelVersionSummary | null;
}

export interface MLModelOverview {
  models: MLModelSummary[];
  versions: MLModelVersionSummary[];
  routing_configs: MLRoutingConfig[];
}

export interface MLflowSyncResult {
  discovered: number;
  created: number;
  updated: number;
  skipped: number;
  errors: number;
  error_details: Array<{
    registered_model_name: string;
    model_version: string;
    code: string;
    message: string;
  }>;
}

export interface MLValidationCheck {
  code: string;
  label: string;
  passed: boolean;
  message: string;
}

export interface MLValidationResult extends MLModelVersionSummary {
  passed: boolean;
  checks: MLValidationCheck[];
}
