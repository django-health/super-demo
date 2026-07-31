"""Seed a demo user with two weeks of synthetic multi-source health data.

Creates user ``demo`` / ``demo`` (also a superuser so /admin/ works) with:

* 14 days of steps + active/basal calories from **two** competing sources
  (``apple_health`` and ``health_connect``) so the source-ranking dedup in
  the summary endpoint actually has something to deduplicate,
* nightly sleep records,
* a handful of workouts,
* active ``WearableConnection`` rows for both device pipelines.

Run it after ``migrate`` and you can log into the app with demo/demo and see
a populated dashboard before connecting anything real.
"""

from __future__ import annotations

import random
from datetime import datetime, time, timedelta, timezone

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.utils import timezone as dj_timezone

from healthdatamodel.constants import DataSource, DeviceBrand
from healthdatamodel.ingest import ingest_records, ingest_workouts
from healthdatamodel.models import WearableConnection
from healthdatamodel.query import SLEEP_TYPE, ActivityMetric, SleepValue
from healthdatamodel.schemas import RecordInput, WorkoutInput

DAYS = 14


class Command(BaseCommand):
    help = "Create demo/demo with two weeks of synthetic multi-source data."

    def handle(self, *args, **options):
        User = get_user_model()
        user, created = User.objects.get_or_create(
            username="demo",
            defaults={"is_staff": True, "is_superuser": True},
        )
        if created:
            user.set_password("demo")
            user.save()
        rng = random.Random(42)
        now = datetime.now(timezone.utc)
        today = now.date()

        records: list[RecordInput] = []
        sleep_records: list[RecordInput] = []
        for i in range(DAYS):
            day = today - timedelta(days=DAYS - 1 - i)
            day_start = datetime.combine(day, time(0), tzinfo=timezone.utc)

            steps = rng.randint(4000, 14000)
            active = rng.randint(250, 700)
            basal = rng.randint(1500, 1750)
            for metric, value, unit in [
                (ActivityMetric.STEPS, steps, "count"),
                (ActivityMetric.ACTIVE_CALORIES, active, "kcal"),
                (ActivityMetric.BASAL_CALORIES, basal, "kcal"),
            ]:
                records.append(
                    RecordInput(
                        startDate=day_start,
                        endDate=day_start + timedelta(days=1),
                        creationDate=now,
                        sourceName="Apple Watch",
                        value=str(value),
                        unit=unit,
                        type=metric.value,
                    )
                )

            # Bedtime ~22:30 the night before, waking 6:30–8:00.
            asleep = datetime.combine(
                day - timedelta(days=1), time(22, 30), tzinfo=timezone.utc
            ) + timedelta(minutes=rng.randint(-30, 45))
            wake = datetime.combine(
                day, time(7, 0), tzinfo=timezone.utc
            ) + timedelta(minutes=rng.randint(-30, 60))
            sleep_records.append(
                RecordInput(
                    startDate=asleep,
                    endDate=wake,
                    creationDate=now,
                    sourceName="Apple Watch",
                    value=SleepValue.ASLEEP_UNSPECIFIED.value,
                    type=SLEEP_TYPE,
                )
            )

        ingest_records(
            user, records + sleep_records, DataSource.APPLE_HEALTH.value
        )

        # A second, slightly-disagreeing pipeline for the same days: proves
        # the summary endpoint picks one ranked source instead of doubling.
        competing = [
            RecordInput(
                startDate=r.startDate,
                endDate=r.endDate,
                creationDate=now,
                sourceName="Pixel Watch",
                value=str(round(float(r.value) * rng.uniform(0.9, 1.1))),
                unit=r.unit,
                type=r.type,
            )
            for r in records
        ]
        ingest_records(user, competing, DataSource.HEALTH_CONNECT.value)

        workouts = []
        for i in range(0, DAYS, 3):
            day = today - timedelta(days=DAYS - 1 - i)
            start = datetime.combine(day, time(17, 30), tzinfo=timezone.utc)
            minutes = rng.randint(25, 60)
            workouts.append(
                WorkoutInput(
                    startDate=start,
                    endDate=start + timedelta(minutes=minutes),
                    creationDate=now,
                    sourceName="Apple Watch",
                    durationUnit="min",
                    duration=minutes,
                    workoutActivityType="HKWorkoutActivityTypeRunning",
                    caloriesBurned=minutes * 9.5,
                    caloriesUnit="kcal",
                    distance=minutes * 0.16,
                    distanceUnit="km",
                )
            )
        ingest_workouts(user, workouts, DataSource.APPLE_HEALTH.value)

        for source, brand in [
            (DataSource.APPLE_HEALTH.value, DeviceBrand.APPLE.value),
            (DataSource.HEALTH_CONNECT.value, DeviceBrand.SAMSUNG.value),
        ]:
            WearableConnection.objects.update_or_create(
                customer=user,
                data_source=source,
                defaults={
                    "device_brand": brand,
                    "status": "active",
                    "last_synced_at": dj_timezone.now(),
                },
            )

        self.stdout.write(
            self.style.SUCCESS(
                f"Seeded demo/demo: {len(records) + len(sleep_records)} apple_health "
                f"records, {len(competing)} health_connect records, "
                f"{len(workouts)} workouts."
            )
        )
