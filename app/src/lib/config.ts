import { Platform } from 'react-native';

/**
 * Base URL of the Django backend.
 *
 * Override with EXPO_PUBLIC_API_URL (e.g. your LAN IP when running on a
 * physical phone: EXPO_PUBLIC_API_URL=http://192.168.1.20:8000). The Android
 * emulator reaches the host machine at 10.0.2.2.
 */
export const API_URL =
  process.env.EXPO_PUBLIC_API_URL ??
  Platform.select({
    android: 'http://10.0.2.2:8000',
    default: 'http://localhost:8000',
  });
