"""JSON API for the React Native app (iOS / Android / web).

All endpoints are token-authenticated (``Authorization: Token <key>``) and
CSRF-exempt — the CSRF machinery protects session cookies, which these
endpoints never rely on.

Push endpoints accept the Apple HealthKit shape used by
``healthdatamodel.schemas.RecordInput`` / ``WorkoutInput`` verbatim, so the
app's HealthKit / Health Connect mappers stay thin.
"""

from __future__ import annotations

import json
from datetime import date, datetime, timedelta, timezone as dt_timezone

from django.contrib.auth import authenticate
from django.db import NotSupportedError, OperationalError
from django.db.models import Count
from django.http import HttpRequest, HttpResponseNotAllowed, JsonResponse
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from pydantic import ValidationError

from healthdatamodel.constants import ConnectionStatus, DataSource
from healthdatamodel.ingest import ingest_records, ingest_workouts
from healthdatamodel.models import Record, WearableConnection, Workout
from healthdatamodel.query import (
    ActivityMetric,
    ensure_ranks,
    get_activity_by_day,
    get_sleep_hours_by_day,
)

from . import providers
from .auth import token_required
from .models import BridgeToken, DeviceToken

# Sources a device is allowed to push directly (everything else arrives via a
# provider package's server-side sync).
DEVICE_SOURCES = {DataSource.APPLE_HEALTH.value, DataSource.HEALTH_CONNECT.value}


def _body(request: HttpRequest) -> dict:
    try:
        payload = json.loads(request.body.decode("utf-8")) if request.body else {}
    except (UnicodeDecodeError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def _error(message: str, status: int = 400) -> JsonResponse:
    return JsonResponse({"error": message}, status=status)


# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------


@csrf_exempt
def login(request: HttpRequest) -> JsonResponse:
    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])
    payload = _body(request)
    user = authenticate(
        username=payload.get("username", ""), password=payload.get("password", "")
    )
    if user is None:
        return _error("invalid credentials", status=401)
    token = DeviceToken.issue(
        user,
        name=str(payload.get("device_name", "")),
        platform=str(payload.get("platform", "")),
    )
    return JsonResponse({"token": token.key, "username": user.get_username()})


@csrf_exempt
@token_required
def logout(request: HttpRequest) -> JsonResponse:
    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])
    request.device_token.delete()
    return JsonResponse({"ok": True})


@csrf_exempt
@token_required
def me(request: HttpRequest) -> JsonResponse:
    devices = [
        {
            "name": t.name,
            "platform": t.platform,
            "created_at": t.created_at.isoformat(),
            "last_seen_at": t.last_seen_at.isoformat() if t.last_seen_at else None,
            "current": t.pk == request.device_token.pk,
        }
        for t in request.user.device_tokens.order_by("created_at")
    ]
    return JsonResponse({"username": request.user.get_username(), "devices": devices})


# ---------------------------------------------------------------------------
# Device push (HealthKit / Health Connect)
# ---------------------------------------------------------------------------


def _touch_wearable_connection(customer, source: str, device_brand: str) -> None:
    connection, _created = WearableConnection.objects.get_or_create(
        customer=customer,
        data_source=source,
        defaults={"device_brand": device_brand},
    )
    connection.status = ConnectionStatus.ACTIVE
    connection.disconnected_at = None
    connection.last_synced_at = timezone.now()
    fields = ["status", "disconnected_at", "last_synced_at"]
    if device_brand and connection.device_brand != device_brand:
        connection.device_brand = device_brand
        fields.append("device_brand")
    connection.save(update_fields=fields)


@csrf_exempt
@token_required
def push_records(request: HttpRequest) -> JsonResponse:
    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])
    payload = _body(request)
    source = payload.get("source", "")
    if source not in DEVICE_SOURCES:
        return _error(f"source must be one of {sorted(DEVICE_SOURCES)}")
    raw = payload.get("records")
    if not isinstance(raw, list) or not raw:
        return _error("records must be a non-empty list")
    from healthdatamodel.schemas import RecordInput

    try:
        records = [RecordInput.model_validate(r) for r in raw]
    except ValidationError as exc:
        return _error(f"invalid record: {exc.errors()[0]}")
    ingest_records(request.user, records, source)
    _touch_wearable_connection(
        request.user, source, str(payload.get("device_brand", ""))
    )
    return JsonResponse({"ingested": len(records), "source": source})


@csrf_exempt
@token_required
def push_workouts(request: HttpRequest) -> JsonResponse:
    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])
    payload = _body(request)
    source = payload.get("source", "")
    if source not in DEVICE_SOURCES:
        return _error(f"source must be one of {sorted(DEVICE_SOURCES)}")
    raw = payload.get("workouts")
    if not isinstance(raw, list) or not raw:
        return _error("workouts must be a non-empty list")
    from healthdatamodel.schemas import WorkoutInput

    try:
        workouts = [WorkoutInput.model_validate(w) for w in raw]
    except ValidationError as exc:
        return _error(f"invalid workout: {exc.errors()[0]}")
    ingest_workouts(request.user, workouts, source)
    _touch_wearable_connection(
        request.user, source, str(payload.get("device_brand", ""))
    )
    return JsonResponse({"ingested": len(workouts), "source": source})


# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------


def _activity_by_day_ranked_fallback(
    customer, metric: ActivityMetric, start: date, end: date
) -> dict[date, float | None]:
    """SQLite-friendly stand-in for ``healthdatamodel.query.get_activity_by_day``.

    The real query needs PostgreSQL (window functions) for interval-level
    source dedup. Here we sum per (day, source) in Python and keep each day's
    highest-ranked source, which matches the real semantics whenever sources
    report at daily-or-finer granularity for whole days.
    """
    ensure_ranks(customer)
    from healthdatamodel.models import DataSourceRanking

    rank_order = {
        r.dataSource: r.rank
        for r in DataSourceRanking.objects.filter(customer=customer)
    }
    start_dt = datetime(start.year, start.month, start.day, tzinfo=dt_timezone.utc)
    end_dt = start_dt + timedelta(days=(end - start).days + 1)

    per_day_source: dict[date, dict[str, float]] = {}
    rows = Record.objects.filter(
        customer=customer,
        type=metric.value,
        startDate__gte=start_dt,
        startDate__lt=end_dt,
    ).values_list("startDate", "source", "value", "unit")
    for start_ts, source, value, unit in rows:
        try:
            v = float(value)
        except (TypeError, ValueError):
            continue
        if unit in ("cal", "calories"):
            v /= 1000
        day_sources = per_day_source.setdefault(start_ts.date(), {})
        day_sources[source] = day_sources.get(source, 0.0) + max(0.0, v)

    result: dict[date, float | None] = {}
    for i in range((end - start).days + 1):
        day = start + timedelta(days=i)
        day_sources = per_day_source.get(day)
        if not day_sources:
            result[day] = None
            continue
        best = min(day_sources, key=lambda s: rank_order.get(s, 10_000))
        result[day] = day_sources[best]
    return result


def _activity_by_day(customer, metric: ActivityMetric, start: date, end: date):
    try:
        return get_activity_by_day(customer, metric, start, end)
    except (NotSupportedError, OperationalError):
        # healthdatamodel's ranked activity query is PostgreSQL-only; on
        # SQLite it fails at execution time with OperationalError.
        return _activity_by_day_ranked_fallback(customer, metric, start, end)


@csrf_exempt
@token_required
def summary(request: HttpRequest) -> JsonResponse:
    days = min(max(int(request.GET.get("days", "14")), 1), 90)
    end = timezone.now().date()
    start = end - timedelta(days=days - 1)

    steps = _activity_by_day(request.user, ActivityMetric.STEPS, start, end)
    active = _activity_by_day(request.user, ActivityMetric.ACTIVE_CALORIES, start, end)
    basal = _activity_by_day(request.user, ActivityMetric.BASAL_CALORIES, start, end)
    sleep = get_sleep_hours_by_day(request.user, start, end)

    return JsonResponse(
        {
            "start": start.isoformat(),
            "end": end.isoformat(),
            "days": [
                {
                    "date": day.isoformat(),
                    "steps": steps.get(day),
                    "active_kcal": active.get(day),
                    "basal_kcal": basal.get(day),
                    "sleep_hours": sleep.get(day),
                }
                for day in (start + timedelta(days=i) for i in range(days))
            ],
        }
    )


# ---------------------------------------------------------------------------
# Connections (device pushes + provider OAuth)
# ---------------------------------------------------------------------------


@csrf_exempt
@token_required
def connections(request: HttpRequest) -> JsonResponse:
    record_counts = dict(
        Record.objects.filter(customer=request.user)
        .values_list("source")
        .annotate(n=Count("id"))
    )
    workout_counts = dict(
        Workout.objects.filter(customer=request.user)
        .values_list("source")
        .annotate(n=Count("id"))
    )

    provider_rows = []
    for provider in providers.PROVIDERS.values():
        connection = providers.get_connection(provider, request.user)
        provider_rows.append(
            {
                "slug": provider.slug,
                "label": provider.label,
                "data_source": provider.data_source,
                "configured": providers.is_configured(provider),
                "connected": bool(connection)
                and connection.status == "active",
                "status": connection.status if connection else None,
                "connected_at": (
                    connection.connected_at.isoformat() if connection else None
                ),
                "records": record_counts.get(provider.data_source, 0),
                "workouts": workout_counts.get(provider.data_source, 0),
            }
        )

    device_rows = [
        {
            "data_source": c.data_source,
            "device_brand": c.device_brand,
            "status": c.status,
            "connected_at": c.connected_at.isoformat(),
            "last_synced_at": (
                c.last_synced_at.isoformat() if c.last_synced_at else None
            ),
            "records": record_counts.get(c.data_source, 0),
            "workouts": workout_counts.get(c.data_source, 0),
        }
        for c in request.user.wearable_connections.all()
    ]

    return JsonResponse({"providers": provider_rows, "devices": device_rows})


# ---------------------------------------------------------------------------
# Provider actions
# ---------------------------------------------------------------------------


def _provider_or_none(slug: str) -> providers.Provider | None:
    return providers.PROVIDERS.get(slug)


@csrf_exempt
@token_required
def provider_connect(request: HttpRequest, slug: str) -> JsonResponse:
    """Start an OAuth connect flow; returns a URL for the system browser.

    Default is the session bridge (works for every provider). For
    google-health, ``{"mode": "native"}`` uses the package's first-class
    backend-owned mobile flow instead: the returned URL is the Google consent
    page itself, and the callback deep-links straight back into the app.
    """
    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])
    provider = _provider_or_none(slug)
    if provider is None:
        return _error("unknown provider", status=404)
    if not providers.is_configured(provider):
        return _error(f"{provider.label} is not configured on this server", status=409)

    if slug == "google-health" and _body(request).get("mode") == "native":
        from googlehealth.oauth import start_mobile_flow

        return JsonResponse(
            {"url": start_mobile_flow(request.user), "mode": "native"}
        )

    token = BridgeToken.issue(request.user, provider.slug)
    path = reverse("bridge-connect", kwargs={"slug": provider.slug})
    url = request.build_absolute_uri(f"{path}?t={token.key}")
    return JsonResponse({"url": url, "mode": "bridge"})


@csrf_exempt
@token_required
def provider_sync(request: HttpRequest, slug: str) -> JsonResponse:
    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])
    provider = _provider_or_none(slug)
    if provider is None:
        return _error("unknown provider", status=404)
    connection = providers.get_connection(provider, request.user)
    if connection is None or connection.status != "active":
        return _error(f"{provider.label} is not connected", status=409)

    days = min(max(int(_body(request).get("days", 7)), 1), 90)
    end = datetime.now(dt_timezone.utc)
    start = end - timedelta(days=days)
    try:
        result = providers.sync_user(provider, connection, start=start, end=end)
    except Exception as exc:  # noqa: BLE001 — surface provider errors to the app
        return _error(f"sync failed: {exc}", status=502)
    return JsonResponse({"total": result.total, "counts": result.counts})


@csrf_exempt
@token_required
def provider_disconnect(request: HttpRequest, slug: str) -> JsonResponse:
    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])
    provider = _provider_or_none(slug)
    if provider is None:
        return _error("unknown provider", status=404)
    connection = providers.get_connection(provider, request.user)
    if connection is None:
        return _error(f"{provider.label} is not connected", status=409)
    try:
        providers.revoke(provider, connection)
    except Exception as exc:  # noqa: BLE001
        return _error(f"disconnect failed: {exc}", status=502)
    return JsonResponse({"ok": True})
