import {
  apiRequest,
} from "../../api/client";

import type {
  AdminRole,
  AdminUser,
  AdminUserCreatePayload,
  AdminUserUpdatePayload,
  AuditLogItem,
  PaginatedResponse,
  RolePermissionUpdateResponse,
  MLModelOverview,
  MLRoutingConfig,
  MLModelVersionSummary,
  MLflowSyncResult,
} from "./types";


function jsonRequest(
  method: "POST" | "PATCH" | "PUT",
  body: unknown,
): RequestInit {
  return {
    method,
    headers: {
      "Content-Type":
        "application/json",
    },
    body: JSON.stringify(body),
  };
}


export function getAdminUsers(
  params: URLSearchParams,
) {
  const query = params.toString();

  return apiRequest<
    PaginatedResponse<AdminUser>
  >(
    `/api/v1/admin/users${
      query ? `?${query}` : ""
    }`,
  );
}


export function createAdminUser(
  payload: AdminUserCreatePayload,
) {
  return apiRequest<AdminUser>(
    "/api/v1/admin/users",
    jsonRequest(
      "POST",
      payload,
    ),
  );
}


export function updateAdminUser(
  userId: string,
  payload: AdminUserUpdatePayload,
) {
  return apiRequest<AdminUser>(
    `/api/v1/admin/users/${userId}`,
    jsonRequest(
      "PATCH",
      payload,
    ),
  );
}


export function getAdminRoles() {
  return apiRequest<{
    roles: AdminRole[];
  }>(
    "/api/v1/admin/roles",
  );
}


export function updateRolePermissions(
  roleId: string,
  permissionCodes: string[],
) {
  return apiRequest<
    RolePermissionUpdateResponse
  >(
    (
      "/api/v1/admin/roles/"
      + roleId
      + "/permissions"
    ),
    jsonRequest(
      "PUT",
      {
        permission_codes:
          permissionCodes,
      },
    ),
  );
}


export function getAuditLogs(
  params: URLSearchParams,
) {
  return apiRequest<
    PaginatedResponse<AuditLogItem>
  >(
    (
      "/api/v1/operations/"
      + "audit-logs?"
      + params.toString()
    ),
  );
}


export function getBackendHealth() {
  return apiRequest<{
    status: string;
    service: string;
    trace_id: string;
  }>(
    "/api/v1/health/",
  );
}

export function getMLModelOverview() {
  return apiRequest<MLModelOverview>("/api/v1/admin/ml/overview");
}

export function syncMLflowModelVersions() {
  return apiRequest<MLflowSyncResult>(
    "/api/v1/admin/ml/mlflow/sync",
    { method: "POST" },
  );
}

export function approveMLModelVersion(versionId: string, reason: string) {
  return apiRequest<MLModelVersionSummary>(
    `/api/v1/admin/ml/model-versions/${encodeURIComponent(versionId)}/approve`,
    jsonRequest("POST", { reason, confirmation: true }),
  );
}

export function retireMLModelVersion(versionId: string, reason: string) {
  return apiRequest<MLModelVersionSummary>(
    `/api/v1/admin/ml/model-versions/${encodeURIComponent(versionId)}/retire`,
    jsonRequest("POST", { reason, confirmation: true }),
  );
}

export function createMLRoutingConfig(payload: {
  version: string;
  modality: "CT" | "MR" | "MRA";
  analysis_type: string;
  target_model_version_id: string;
  reason: string;
}) {
  return apiRequest<MLRoutingConfig>(
    "/api/v1/admin/ml/routing-configs",
    jsonRequest("POST", payload),
  );
}

export function activateMLRoutingConfig(routingId: string, reason: string) {
  return apiRequest<MLRoutingConfig>(
    `/api/v1/admin/ml/routing-configs/${encodeURIComponent(routingId)}/activate`,
    jsonRequest("POST", { reason, confirmation: true }),
  );
}
