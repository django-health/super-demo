/**
 * Apple HealthKit reader, via @kingstinct/react-native-healthkit.
 *
 * Everything HealthKit returns is already in the HK identifier vocabulary
 * that django-healthdatamodel stores natively, so the mapping is close to
 * 1:1: quantity samples → RecordPayload, sleep category samples →
 * HKCategoryValueSleepAnalysis* strings, workouts → WorkoutPayload.
 */

import {
  CategoryValueSleepAnalysis,
  isHealthDataAvailableAsync,
  queryCategorySamples,
  queryQuantitySamples,
  queryWorkoutSamples,
  requestAuthorization,
  WorkoutActivityType,
} from '@kingstinct/react-native-healthkit';

import type { RecordPayload, WorkoutPayload } from '@/lib/api';
import type { HealthReader, HealthReadResult } from './types';

const QUANTITY_TYPES = [
  { identifier: 'HKQuantityTypeIdentifierStepCount', unit: 'count' },
  { identifier: 'HKQuantityTypeIdentifierActiveEnergyBurned', unit: 'kcal' },
  { identifier: 'HKQuantityTypeIdentifierBasalEnergyBurned', unit: 'kcal' },
] as const;

const SLEEP_TYPE = 'HKCategoryTypeIdentifierSleepAnalysis' as const;

const SLEEP_VALUE_NAMES: Record<number, string> = {
  [CategoryValueSleepAnalysis.inBed]: 'HKCategoryValueSleepAnalysisInBed',
  [CategoryValueSleepAnalysis.asleepUnspecified]:
    'HKCategoryValueSleepAnalysisAsleepUnspecified',
  [CategoryValueSleepAnalysis.awake]: 'HKCategoryValueSleepAnalysisAwake',
  [CategoryValueSleepAnalysis.asleepCore]: 'HKCategoryValueSleepAnalysisAsleepCore',
  [CategoryValueSleepAnalysis.asleepDeep]: 'HKCategoryValueSleepAnalysisAsleepDeep',
  [CategoryValueSleepAnalysis.asleepREM]: 'HKCategoryValueSleepAnalysisAsleepREM',
};

function window(days: number): { startDate: Date; endDate: Date } {
  const endDate = new Date();
  const startDate = new Date(endDate.getTime() - days * 24 * 60 * 60 * 1000);
  return { startDate, endDate };
}

export const reader: HealthReader = {
  label: 'Apple Health',

  available: () => isHealthDataAvailableAsync(),

  requestPermissions: () =>
    requestAuthorization({
      toRead: [
        ...QUANTITY_TYPES.map((t) => t.identifier),
        SLEEP_TYPE,
        'HKWorkoutTypeIdentifier',
      ],
    }),

  async read(days: number): Promise<HealthReadResult> {
    const filter = { date: window(days) };
    const now = new Date().toISOString();
    const records: RecordPayload[] = [];

    for (const { identifier, unit } of QUANTITY_TYPES) {
      const samples = await queryQuantitySamples(identifier, {
        filter,
        limit: -1,
        unit,
      });
      for (const sample of samples) {
        records.push({
          startDate: sample.startDate.toISOString(),
          endDate: sample.endDate.toISOString(),
          creationDate: now,
          sourceName: sample.sourceRevision?.source?.name ?? 'HealthKit',
          value: String(sample.quantity),
          unit: sample.unit,
          type: identifier,
          device: sample.device?.name ?? undefined,
        });
      }
    }

    const sleepSamples = await queryCategorySamples(SLEEP_TYPE, { filter, limit: -1 });
    for (const sample of sleepSamples) {
      const value = SLEEP_VALUE_NAMES[sample.value as number];
      if (!value) continue;
      records.push({
        startDate: sample.startDate.toISOString(),
        endDate: sample.endDate.toISOString(),
        creationDate: now,
        sourceName: sample.sourceRevision?.source?.name ?? 'HealthKit',
        value,
        type: SLEEP_TYPE,
        device: sample.device?.name ?? undefined,
      });
    }

    const workoutSamples = await queryWorkoutSamples({ filter, limit: -1 });
    const workouts: WorkoutPayload[] = workoutSamples.map((workout) => {
      // Reverse-map the numeric enum back to HK's identifier string:
      // 37 → "running" → "HKWorkoutActivityTypeRunning".
      const name = WorkoutActivityType[workout.workoutActivityType] ?? 'Other';
      return {
        startDate: workout.startDate.toISOString(),
        endDate: workout.endDate.toISOString(),
        creationDate: now,
        sourceName: workout.sourceRevision?.source?.name ?? 'HealthKit',
        durationUnit: 'min',
        duration: Math.round(
          (workout.endDate.getTime() - workout.startDate.getTime()) / 60_000,
        ),
        workoutActivityType: `HKWorkoutActivityType${name.charAt(0).toUpperCase()}${name.slice(1)}`,
        caloriesBurned: workout.totalEnergyBurned?.quantity,
        caloriesUnit: workout.totalEnergyBurned ? workout.totalEnergyBurned.unit : undefined,
        distance: workout.totalDistance?.quantity,
        distanceUnit: workout.totalDistance ? workout.totalDistance.unit : undefined,
      };
    });

    return { source: 'apple_health', deviceBrand: 'apple', records, workouts };
  },
};
