/**
 * Typed client for the super-demo backend (backend/api/).
 *
 * Record and workout payloads use the Apple HealthKit shape that
 * django-healthdatamodel's RecordInput/WorkoutInput accept verbatim.
 */

import { API_URL } from './config';

export interface RecordPayload {
  startDate: string;
  endDate: string;
  creationDate: string;
  sourceName: string;
  value: string;
  unit?: string;
  type: string;
  device?: string;
}

export interface WorkoutPayload {
  startDate: string;
  endDate: string;
  creationDate: string;
  sourceName: string;
  durationUnit: string;
  duration: number;
  workoutActivityType: string;
  caloriesBurned?: number;
  caloriesUnit?: string;
  distance?: number;
  distanceUnit?: string;
}

export interface DaySummary {
  date: string;
  steps: number | null;
  active_kcal: number | null;
  basal_kcal: number | null;
  sleep_hours: number | null;
}

export interface Summary {
  start: string;
  end: string;
  days: DaySummary[];
}

export interface ProviderInfo {
  slug: string;
  label: string;
  data_source: string;
  configured: boolean;
  connected: boolean;
  status: string | null;
  connected_at: string | null;
  records: number;
  workouts: number;
}

export interface DeviceConnectionInfo {
  data_source: string;
  device_brand: string;
  status: string;
  connected_at: string;
  last_synced_at: string | null;
  records: number;
  workouts: number;
}

export interface Connections {
  providers: ProviderInfo[];
  devices: DeviceConnectionInfo[];
}

export interface DeviceInfo {
  name: string;
  platform: string;
  created_at: string;
  last_seen_at: string | null;
  current: boolean;
}

export interface Me {
  username: string;
  devices: DeviceInfo[];
}

export class ApiError extends Error {
  status: number;

  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

async function request<T>(
  path: string,
  options: { method?: string; token?: string; body?: unknown } = {},
): Promise<T> {
  const headers: Record<string, string> = { 'Content-Type': 'application/json' };
  if (options.token) headers.Authorization = `Token ${options.token}`;
  const response = await fetch(`${API_URL}${path}`, {
    method: options.method ?? 'GET',
    headers,
    body: options.body === undefined ? undefined : JSON.stringify(options.body),
  });
  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new ApiError(response.status, data.error ?? `HTTP ${response.status}`);
  }
  return data as T;
}

export const api = {
  login: (username: string, password: string, deviceName: string, platform: string) =>
    request<{ token: string; username: string }>('/api/auth/login/', {
      method: 'POST',
      body: { username, password, device_name: deviceName, platform },
    }),

  logout: (token: string) =>
    request<{ ok: boolean }>('/api/auth/logout/', { method: 'POST', token }),

  me: (token: string) => request<Me>('/api/me/', { token }),

  summary: (token: string, days: number) =>
    request<Summary>(`/api/summary/?days=${days}`, { token }),

  connections: (token: string) => request<Connections>('/api/connections/', { token }),

  pushRecords: (
    token: string,
    source: string,
    deviceBrand: string,
    records: RecordPayload[],
  ) =>
    request<{ ingested: number }>('/api/push/records/', {
      method: 'POST',
      token,
      body: { source, device_brand: deviceBrand, records },
    }),

  pushWorkouts: (
    token: string,
    source: string,
    deviceBrand: string,
    workouts: WorkoutPayload[],
  ) =>
    request<{ ingested: number }>('/api/push/workouts/', {
      method: 'POST',
      token,
      body: { source, device_brand: deviceBrand, workouts },
    }),

  providerConnect: (token: string, slug: string) =>
    request<{ url: string; mode: string }>(`/api/providers/${slug}/connect/`, {
      method: 'POST',
      token,
    }),

  providerSync: (token: string, slug: string, days: number) =>
    request<{ total: number; counts: Record<string, number> }>(
      `/api/providers/${slug}/sync/`,
      { method: 'POST', token, body: { days } },
    ),

  providerDisconnect: (token: string, slug: string) =>
    request<{ ok: boolean }>(`/api/providers/${slug}/disconnect/`, {
      method: 'POST',
      token,
    }),
};
