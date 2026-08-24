/** Single boundary for backend HTTP calls; never call Gemini from the browser. */
const baseUrl = import.meta.env.VITE_BACKEND_URL ?? 'http://localhost:8080';
export async function apiRequest<T>(path: string, init?: RequestInit): Promise<T> { const response = await fetch(`${baseUrl}${path}`, init); if (!response.ok) throw new Error(`BACKEND_REQUEST_FAILED:${response.status}`); return response.json() as Promise<T>; }
