"""End-to-end tests for the device API: login → push → summary → connections."""

from __future__ import annotations

import json
from datetime import datetime, time, timedelta, timezone

import pytest
from django.contrib.auth.models import User
from django.urls import reverse

from api.models import BridgeToken, DeviceToken


@pytest.fixture
def user(db):
    return User.objects.create_user(username="alice", password="pw")


@pytest.fixture
def token(user):
    return DeviceToken.issue(user, name="Test iPhone", platform="ios")


def auth(token):
    return {"HTTP_AUTHORIZATION": f"Token {token.key}"}


def post_json(client, url, payload, **extra):
    return client.post(
        url, json.dumps(payload), content_type="application/json", **extra
    )


# --- auth -------------------------------------------------------------------


def test_login_issues_device_token(client, user):
    resp = post_json(
        client,
        reverse("api-login"),
        {"username": "alice", "password": "pw", "device_name": "Pixel", "platform": "android"},
    )
    assert resp.status_code == 200
    key = resp.json()["token"]
    assert DeviceToken.objects.get(key=key).name == "Pixel"


def test_login_rejects_bad_credentials(client, user):
    resp = post_json(client, reverse("api-login"), {"username": "alice", "password": "nope"})
    assert resp.status_code == 401


def test_endpoints_require_token(client, db):
    assert client.get(reverse("api-summary")).status_code == 401
    assert client.get(reverse("api-me"), HTTP_AUTHORIZATION="Token bogus").status_code == 401


def test_me_lists_devices_and_marks_current(client, user, token):
    DeviceToken.issue(user, name="Old laptop", platform="web")
    resp = client.get(reverse("api-me"), **auth(token))
    devices = resp.json()["devices"]
    assert len(devices) == 2
    assert [d["name"] for d in devices if d["current"]] == ["Test iPhone"]


def test_logout_revokes_only_this_device(client, user, token):
    other = DeviceToken.issue(user, name="iPad", platform="ios")
    resp = client.post(reverse("api-logout"), **auth(token))
    assert resp.status_code == 200
    assert not DeviceToken.objects.filter(pk=token.pk).exists()
    assert DeviceToken.objects.filter(pk=other.pk).exists()


# --- push + summary ---------------------------------------------------------


def _day_record(day, type_, value, unit, source_name="Test iPhone"):
    start = datetime.combine(day, time(0), tzinfo=timezone.utc)
    return {
        "startDate": start.isoformat(),
        "endDate": (start + timedelta(days=1)).isoformat(),
        "creationDate": datetime.now(timezone.utc).isoformat(),
        "sourceName": source_name,
        "value": str(value),
        "unit": unit,
        "type": type_,
    }


def test_push_records_and_read_back_summary(client, user, token):
    today = datetime.now(timezone.utc).date()
    records = [
        _day_record(today, "HKQuantityTypeIdentifierStepCount", 8000, "count"),
        _day_record(today, "HKQuantityTypeIdentifierActiveEnergyBurned", 500, "kcal"),
    ]
    resp = post_json(
        client,
        reverse("api-push-records"),
        {"source": "apple_health", "device_brand": "apple", "records": records},
        **auth(token),
    )
    assert resp.status_code == 200
    assert resp.json()["ingested"] == 2

    resp = client.get(reverse("api-summary"), {"days": 1}, **auth(token))
    day = resp.json()["days"][0]
    assert day["date"] == today.isoformat()
    assert day["steps"] == 8000.0
    assert day["active_kcal"] == 500.0
    assert day["sleep_hours"] is None


def test_summary_dedupes_competing_sources(client, user, token):
    """Two pipelines report the same day; the summary must pick one, not sum."""
    today = datetime.now(timezone.utc).date()
    for source, steps in [("apple_health", 8000), ("health_connect", 9000)]:
        post_json(
            client,
            reverse("api-push-records"),
            {
                "source": source,
                "records": [
                    _day_record(today, "HKQuantityTypeIdentifierStepCount", steps, "count")
                ],
            },
            **auth(token),
        )
    resp = client.get(reverse("api-summary"), {"days": 1}, **auth(token))
    assert resp.json()["days"][0]["steps"] in (8000.0, 9000.0)


def test_push_sleep_shows_in_summary(client, user, token):
    today = datetime.now(timezone.utc).date()
    asleep = datetime.combine(today - timedelta(days=1), time(23, 0), tzinfo=timezone.utc)
    record = {
        "startDate": asleep.isoformat(),
        "endDate": (asleep + timedelta(hours=8)).isoformat(),
        "creationDate": datetime.now(timezone.utc).isoformat(),
        "sourceName": "Test iPhone",
        "value": "HKCategoryValueSleepAnalysisAsleepUnspecified",
        "type": "HKCategoryTypeIdentifierSleepAnalysis",
    }
    post_json(
        client,
        reverse("api-push-records"),
        {"source": "apple_health", "records": [record]},
        **auth(token),
    )
    resp = client.get(reverse("api-summary"), {"days": 1}, **auth(token))
    assert resp.json()["days"][0]["sleep_hours"] == 8.0


def test_push_rejects_non_device_source(client, user, token):
    resp = post_json(
        client,
        reverse("api-push-records"),
        {"source": "strava", "records": [{}]},
        **auth(token),
    )
    assert resp.status_code == 400


def test_push_workouts(client, user, token):
    now = datetime.now(timezone.utc)
    workout = {
        "startDate": (now - timedelta(hours=1)).isoformat(),
        "endDate": now.isoformat(),
        "creationDate": now.isoformat(),
        "sourceName": "Test iPhone",
        "durationUnit": "min",
        "duration": 60,
        "workoutActivityType": "HKWorkoutActivityTypeRunning",
        "caloriesBurned": 540.0,
        "caloriesUnit": "kcal",
    }
    resp = post_json(
        client,
        reverse("api-push-workouts"),
        {"source": "health_connect", "workouts": [workout]},
        **auth(token),
    )
    assert resp.status_code == 200
    assert resp.json()["ingested"] == 1


def test_push_upserts_wearable_connection(client, user, token):
    today = datetime.now(timezone.utc).date()
    post_json(
        client,
        reverse("api-push-records"),
        {
            "source": "apple_health",
            "device_brand": "apple",
            "records": [_day_record(today, "HKQuantityTypeIdentifierStepCount", 1, "count")],
        },
        **auth(token),
    )
    connection = user.wearable_connections.get(data_source="apple_health")
    assert connection.status == "active"
    assert connection.device_brand == "apple"
    assert connection.last_synced_at is not None


# --- connections + providers -------------------------------------------------


def test_connections_lists_all_providers(client, user, token):
    resp = client.get(reverse("api-connections"), **auth(token))
    body = resp.json()
    slugs = {p["slug"] for p in body["providers"]}
    assert slugs == {"google-health", "garmin", "oura", "strava", "whoop"}
    # No credentials in test settings → nothing is configured or connected.
    assert not any(p["configured"] for p in body["providers"])
    assert not any(p["connected"] for p in body["providers"])


def test_provider_connect_requires_configuration(client, user, token):
    resp = client.post(
        reverse("api-provider-connect", kwargs={"slug": "strava"}), **auth(token)
    )
    assert resp.status_code == 409


def test_provider_connect_returns_bridge_url(client, user, token, settings):
    settings.STRAVA_CLIENT_ID = "test-client"
    resp = client.post(
        reverse("api-provider-connect", kwargs={"slug": "strava"}), **auth(token)
    )
    assert resp.status_code == 200
    url = resp.json()["url"]
    assert "/bridge/connect/strava/?t=" in url


def test_bridge_consumes_token_and_redirects_to_provider(client, user, settings):
    settings.STRAVA_CLIENT_ID = "test-client"
    bridge_token = BridgeToken.issue(user, "strava")
    resp = client.get(f"/bridge/connect/strava/?t={bridge_token.key}")
    assert resp.status_code == 302
    assert resp.url == reverse("strava:connect")
    # Single use: the same link must not work twice.
    assert client.get(f"/bridge/connect/strava/?t={bridge_token.key}").status_code == 403


def test_provider_sync_requires_connection(client, user, token):
    resp = client.post(
        reverse("api-provider-sync", kwargs={"slug": "whoop"}), **auth(token)
    )
    assert resp.status_code == 409


def test_unknown_provider_404s(client, user, token):
    resp = client.post(
        reverse("api-provider-sync", kwargs={"slug": "fitbit-classic"}), **auth(token)
    )
    assert resp.status_code == 404


# --- seed command ------------------------------------------------------------


def test_seed_demo_populates_dashboard(client, db, django_user_model):
    from django.core.management import call_command

    call_command("seed_demo")
    resp = post_json(
        client, reverse("api-login"), {"username": "demo", "password": "demo"}
    )
    key = resp.json()["token"]
    resp = client.get(
        reverse("api-summary"), {"days": 7}, HTTP_AUTHORIZATION=f"Token {key}"
    )
    days = resp.json()["days"]
    assert all(d["steps"] is not None for d in days)
    assert all(d["sleep_hours"] is not None for d in days)
