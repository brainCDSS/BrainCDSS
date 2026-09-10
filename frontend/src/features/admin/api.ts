import { apiRequest } from "../../api/client";
import type { AdminRole, AdminUser, AuditLogItem, PaginatedResponse } from "./types";

export function getAdminUsers(params: URLSearchParams) {
  const query = params.toString();
  return apiRequest<PaginatedResponse<AdminUser>>(
    `/api/v1/admin/users${query ? `?${query}` : ""}`,
  );
}

export function getAdminRoles() {
  return apiRequest<{ roles: AdminRole[] }>("/api/v1/admin/roles");
}

export function getAuditLogs(params: URLSearchParams) {
  return apiRequest<PaginatedResponse<AuditLogItem>>(
    `/api/v1/operations/audit-logs?${params.toString()}`,
  );
}

export function getBackendHealth() {
  return apiRequest<{ status: string; service: string; trace_id: string }>(
    "/api/v1/health/",
  );
}
