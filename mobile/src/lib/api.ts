import type { DeviceRegistration, JobCreateResponse, JobView } from './types';

export class ApiError extends Error {
  status: number;
  code: string | null;

  constructor(status: number, message: string, code: string | null = null) {
    super(message);
    this.status = status;
    this.code = code;
  }
}

async function request<T>(
  baseUrl: string,
  path: string,
  options: { method?: string; token?: string; body?: unknown } = {},
): Promise<T> {
  const headers: Record<string, string> = {};
  if (options.token) headers.Authorization = `Bearer ${options.token}`;
  if (options.body !== undefined) headers['Content-Type'] = 'application/json';

  let response: Response;
  try {
    response = await fetch(`${baseUrl}${path}`, {
      method: options.method ?? 'GET',
      headers,
      body: options.body === undefined ? undefined : JSON.stringify(options.body),
    });
  } catch {
    throw new ApiError(0, `Could not reach the backend at ${baseUrl}. Is it running, and is your phone on the same network?`);
  }

  if (response.status === 204) return undefined as T;

  let payload: any = null;
  try {
    payload = await response.json();
  } catch {
    // Non-JSON body (proxy error page etc.) — fall through to status handling.
  }

  if (!response.ok) {
    const detail = payload?.detail;
    const message =
      (typeof detail === 'object' && detail?.message) ||
      (typeof detail === 'string' && detail) ||
      `Request failed (HTTP ${response.status})`;
    const code = typeof detail === 'object' ? (detail?.code ?? null) : null;
    throw new ApiError(response.status, message, code);
  }
  return payload as T;
}

export function registerDevice(baseUrl: string): Promise<DeviceRegistration> {
  return request<DeviceRegistration>(baseUrl, '/v1/devices', { method: 'POST' });
}

export function createJob(
  baseUrl: string,
  token: string,
  args: { client_id: string; url: string; locale: string },
): Promise<JobCreateResponse> {
  return request<JobCreateResponse>(baseUrl, '/v1/jobs', { method: 'POST', token, body: args });
}

export function getJob(baseUrl: string, token: string, jobId: string): Promise<JobView> {
  return request<JobView>(baseUrl, `/v1/jobs/${jobId}`, { token });
}

export function retryJob(baseUrl: string, token: string, jobId: string): Promise<JobView> {
  return request<JobView>(baseUrl, `/v1/jobs/${jobId}/retry`, { method: 'POST', token });
}

export function deleteJob(baseUrl: string, token: string, jobId: string): Promise<void> {
  return request<void>(baseUrl, `/v1/jobs/${jobId}`, { method: 'DELETE', token });
}

export function health(baseUrl: string): Promise<{ status: string; version: string }> {
  return request<{ status: string; version: string }>(baseUrl, '/healthz');
}
