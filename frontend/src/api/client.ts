/**
 * HTTP client — thin wrapper around fetch for the backend API.
 * Automatically injects JWT token from localStorage.
 */

const API_BASE = '/api/v1'

class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
    public data?: unknown,
  ) {
    super(message)
    this.name = 'ApiError'
  }
}

async function request<T>(
  path: string,
  options: RequestInit = {},
): Promise<T> {
  const token = localStorage.getItem('quantitext-token')

  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...(options.headers as Record<string, string> | undefined),
  }
  if (token) {
    headers['Authorization'] = `Bearer ${token}`
  }

  const res = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers,
  })

  if (!res.ok) {
    const body = await res.json().catch(() => ({}))
    // Extract a human-readable message from various error shapes:
    //  - Our AppException: { error: "msg", detail: {...} }
    //  - FastAPI HTTPException: { detail: "msg" } or { detail: [...] }
    const message =
      (typeof body.error === 'string' && body.error) ||
      (typeof body.detail === 'string' && body.detail) ||
      (Array.isArray(body.detail) && body.detail.map((e: { msg?: string }) => e.msg ?? JSON.stringify(e)).join('; ')) ||
      res.statusText
    throw new ApiError(res.status, message, body)
  }

  // Handle 204 No Content
  if (res.status === 204) return undefined as T

  return res.json() as Promise<T>
}

export const api = {
  get: <T>(path: string) => request<T>(path, { method: 'GET' }),
  post: <T>(path: string, body?: unknown) =>
    request<T>(path, { method: 'POST', body: body ? JSON.stringify(body) : undefined }),
  put: <T>(path: string, body?: unknown) =>
    request<T>(path, { method: 'PUT', body: body ? JSON.stringify(body) : undefined }),
  delete: <T>(path: string) => request<T>(path, { method: 'DELETE' }),
}

export { ApiError }
export { request as apiFetch }
