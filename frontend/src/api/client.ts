import { getAccessToken } from "../features/auth/session";

/** Single boundary for backend HTTP calls; never call internal services from the browser. */
const baseUrl =
  import.meta.env.DEV
    ? ""
    : import.meta.env.VITE_BACKEND_URL ?? "";

export class ApiRequestError extends Error {
  constructor(
    readonly status: number,
    readonly detail: string,
  ) {
    super(`BACKEND_REQUEST_FAILED:${status}${detail ? `:${detail}` : ""}`);
    this.name = "ApiRequestError";
  }
}

export function getApiRequestStatus(error: unknown): number | null {
  return error instanceof ApiRequestError ? error.status : null;
}

export function authenticatedAsset(path: string) {
  if (/^https?:\/\//i.test(path)) {
    return { url: path, headers: {} };
  }
  const accessToken = getAccessToken();
  const headers: Record<string, string> = {};
  if (accessToken) headers.Authorization = `Bearer ${accessToken}`;
  return {
    url: `${baseUrl}${path}`,
    headers,
  };
}

export async function apiRequest<T>(
  path: string,
  init: RequestInit = {},
): Promise<T> {
  const headers = new Headers(init.headers);
  const accessToken = getAccessToken();

  if (accessToken && !headers.has("Authorization")) {
    headers.set("Authorization", `Bearer ${accessToken}`);
  }

  const response = await fetch(`${baseUrl}${path}`, {
    ...init,
    headers,
  });

  if (!response.ok) {
    const body = await response.text();
    let detail = body;
    try {
      const payload = JSON.parse(body) as { detail?: unknown } | Record<string, unknown>;
      detail = typeof payload.detail === "string"
        ? payload.detail
        : JSON.stringify(payload);
    } catch { /* Keep the plain response body. */ }
    throw new ApiRequestError(response.status, detail);
  }

  if (response.status === 204) {
    return undefined as T;
  }

  return response.json() as Promise<T>;
}
