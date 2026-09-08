import { getAccessToken } from "../features/auth/session";

/** Single boundary for backend HTTP calls; never call internal services from the browser. */
const baseUrl = import.meta.env.VITE_BACKEND_URL ?? "http://localhost:8080";

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
    throw new Error(`BACKEND_REQUEST_FAILED:${response.status}`);
  }

  if (response.status === 204) {
    return undefined as T;
  }

  return response.json() as Promise<T>;
}

