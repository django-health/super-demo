import type { HealthReader } from './types';

/**
 * Default reader (web and anything else without an on-device health store).
 *
 * Metro's platform extensions pick reader.ios.ts / reader.android.ts on
 * device; on web there is nothing to read — health data arrives via the
 * cloud-provider connections or from your other devices instead.
 */
export const reader: HealthReader = {
  label: 'On-device health data',
  available: async () => false,
  requestPermissions: async () => false,
  read: async () => {
    throw new Error('No on-device health store on this platform.');
  },
};
