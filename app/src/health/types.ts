import type { RecordPayload, WorkoutPayload } from '@/lib/api';

/** What a platform health reader hands back, ready to POST to the backend. */
export interface HealthReadResult {
  /** healthdatamodel DataSource value: apple_health | health_connect */
  source: 'apple_health' | 'health_connect';
  /** healthdatamodel DeviceBrand value, best guess for this platform. */
  deviceBrand: string;
  records: RecordPayload[];
  workouts: WorkoutPayload[];
}

export interface HealthReader {
  /** Whether this platform can read on-device health data at all. */
  available: () => Promise<boolean>;
  /** Human label shown on the Device screen ("Apple Health", …). */
  label: string;
  /** Request read permissions from the OS. Resolves false if denied. */
  requestPermissions: () => Promise<boolean>;
  /** Read the last `days` days of steps, energy, sleep and workouts. */
  read: (days: number) => Promise<HealthReadResult>;
}
