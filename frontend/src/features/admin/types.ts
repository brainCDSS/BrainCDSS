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
