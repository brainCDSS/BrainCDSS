/** Single boundary for backend HTTP calls; never call Gemini from the browser. */

const baseUrl =
  import.meta.env.VITE_BACKEND_URL ??
  'http://localhost:8000';

const testAccessToken =
  import.meta.env.VITE_TEST_ACCESS_TOKEN;

export async function apiRequest<T>(
  path: string,
  init: RequestInit = {},
): Promise<T> {
  const headers = new Headers(init.headers);

  if (testAccessToken) {
    headers.set(
      'Authorization',
      `Bearer ${testAccessToken}`,
    );
  }

  const response = await fetch(
    `${baseUrl}${path}`,
    {
      ...init,
      headers,
    },
  );

  if (!response.ok) {
    throw new Error(
      `BACKEND_REQUEST_FAILED:${response.status}`,
    );
  }

  return response.json() as Promise<T>;
}
