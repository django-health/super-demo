/**
 * Android Health Connect reader, via react-native-health-connect.
 *
 * Health Connect has its own vocabulary; we translate to the HK identifier
 * strings django-healthdatamodel stores (the same mapping every server-side
 * provider package does). Sleep sessions map stage-by-stage when stages are
 * present, else the whole session becomes one AsleepUnspecified record.
 */

import {
  initialize,
  readRecords,
  requestPermission,
  getSdkStatus,
  SdkAvailabilityStatus,
} from 'react-native-health-connect';

import type { RecordPayload, WorkoutPayload } from '@/lib/api';
import type { HealthReader, HealthReadResult } from './types';

// androidx.health.connect SleepSessionRecord stage constants.
const SLEEP_STAGE_NAMES: Record<number, string> = {
  1: 'HKCategoryValueSleepAnalysisAwake',
  2: 'HKCategoryValueSleepAnalysisAsleepUnspecified', // SLEEPING
  3: 'HKCategoryValueSleepAnalysisInBed', // OUT_OF_BED — closest HK analogue
  4: 'HKCategoryValueSleepAnalysisAsleepCore', // LIGHT
  5: 'HKCategoryValueSleepAnalysisAsleepDeep',
  6: 'HKCategoryValueSleepAnalysisAsleepREM',
  7: 'HKCategoryValueSleepAnalysisAwake', // AWAKE_IN_BED
};

function window(days: number): { startTime: string; endTime: string } {
  const end = new Date();
  const start = new Date(end.getTime() - days * 24 * 60 * 60 * 1000);
  return { startTime: start.toISOString(), endTime: end.toISOString() };
}

export const reader: HealthReader = {
  label: 'Health Connect',

  available: async () => {
    try {
      const status = await getSdkStatus();
      return status === SdkAvailabilityStatus.SDK_AVAILABLE;
    } catch {
      return false;
    }
  },

  requestPermissions: async () => {
    const initialized = await initialize();
    if (!initialized) return false;
    const granted = await requestPermission([
      { accessType: 'read', recordType: 'Steps' },
      { accessType: 'read', recordType: 'ActiveCaloriesBurned' },
      { accessType: 'read', recordType: 'TotalCaloriesBurned' },
      { accessType: 'read', recordType: 'SleepSession' },
      { accessType: 'read', recordType: 'ExerciseSession' },
    ]);
    return granted.length > 0;
  },

  async read(days: number): Promise<HealthReadResult> {
    await initialize();
    const timeRangeFilter = { operator: 'between' as const, ...window(days) };
    const now = new Date().toISOString();
    const records: RecordPayload[] = [];

    const steps = await readRecords('Steps', { timeRangeFilter });
    for (const record of steps.records) {
      records.push({
        startDate: record.startTime,
        endDate: record.endTime,
        creationDate: now,
        sourceName: record.metadata?.dataOrigin ?? 'Health Connect',
        value: String(record.count),
        unit: 'count',
        type: 'HKQuantityTypeIdentifierStepCount',
      });
    }

    const activeEnergy = await readRecords('ActiveCaloriesBurned', { timeRangeFilter });
    for (const record of activeEnergy.records) {
      records.push({
        startDate: record.startTime,
        endDate: record.endTime,
        creationDate: now,
        sourceName: record.metadata?.dataOrigin ?? 'Health Connect',
        value: String(record.energy.inKilocalories),
        unit: 'kcal',
        type: 'HKQuantityTypeIdentifierActiveEnergyBurned',
      });
    }

    const sleepSessions = await readRecords('SleepSession', { timeRangeFilter });
    for (const session of sleepSessions.records) {
      const sourceName = session.metadata?.dataOrigin ?? 'Health Connect';
      const stages = session.stages ?? [];
      if (stages.length > 0) {
        for (const stage of stages) {
          const value = SLEEP_STAGE_NAMES[stage.stage];
          if (!value) continue;
          records.push({
            startDate: stage.startTime,
            endDate: stage.endTime,
            creationDate: now,
            sourceName,
            value,
            type: 'HKCategoryTypeIdentifierSleepAnalysis',
          });
        }
      } else {
        records.push({
          startDate: session.startTime,
          endDate: session.endTime,
          creationDate: now,
          sourceName,
          value: 'HKCategoryValueSleepAnalysisAsleepUnspecified',
          type: 'HKCategoryTypeIdentifierSleepAnalysis',
        });
      }
    }

    const exercise = await readRecords('ExerciseSession', { timeRangeFilter });
    const workouts: WorkoutPayload[] = exercise.records.map((session) => ({
      startDate: session.startTime,
      endDate: session.endTime,
      creationDate: now,
      sourceName: session.metadata?.dataOrigin ?? 'Health Connect',
      durationUnit: 'min',
      duration: Math.round(
        (new Date(session.endTime).getTime() - new Date(session.startTime).getTime()) /
          60_000,
      ),
      workoutActivityType: `HealthConnectExerciseType${session.exerciseType}`,
    }));

    return { source: 'health_connect', deviceBrand: '', records, workouts };
  },
};
