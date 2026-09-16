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
