"""Settings for the django-health super-demo backend.

One Django project that installs *every* django-health wearable integration
(google-health, garmin, oura, strava, whoop) on top of ``healthdatamodel``,
plus a small token-authenticated JSON API (the ``api`` app) that the React
Native app uses to push on-device HealthKit / Health Connect data and read
merged summaries.

All provider OAuth credentials come from environment variables, using the
same names as each package's own demo project — a provider with no
credentials set simply shows up as "not configured" in the API. See
``.env.example`` at the repo root.

Database defaults to SQLite. Set ``DATABASE_URL=postgres://...`` to use
PostgreSQL, which unlocks the source-ranked activity queries in
``healthdatamodel.query`` (the API falls back to a demo-local aggregation on
SQLite).
"""

import os
from pathlib import Path
from urllib.parse import urlparse

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = os.environ.get(
    "DJANGO_SECRET_KEY", "django-insecure-super-demo-key-do-not-use-in-production"
)
DEBUG = os.environ.get("DJANGO_DEBUG", "1") not in ("", "0", "false")
ALLOWED_HOSTS = ["*"]

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "corsheaders",
    "healthdatamodel",
    "googlehealth",
    "garmin",
    "oura",
    "strava",
    "whoop",
    "api",
]

MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

LOGIN_URL = "/admin/login/"
LOGIN_REDIRECT_URL = "/"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]


def _database_from_env() -> dict:
    url = os.environ.get("DATABASE_URL", "")
    if url.startswith(("postgres://", "postgresql://")):
        parsed = urlparse(url)
        return {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": parsed.path.lstrip("/"),
            "USER": parsed.username or "",
            "PASSWORD": parsed.password or "",
            "HOST": parsed.hostname or "",
            "PORT": str(parsed.port or ""),
        }
    return {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }


DATABASES = {"default": _database_from_env()}

STATIC_URL = "static/"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
USE_TZ = True

# The Expo app (native fetch has no origin; web builds run on another port).
CORS_ALLOW_ALL_ORIGINS = True
CORS_ALLOW_HEADERS = ["authorization", "content-type"]

# Where the packages' web connect/disconnect flows land afterwards. The
# super-demo has no server-rendered homepage — the bridge "done" page tells
# the user to return to the app.
_BRIDGE_DONE = "/bridge/done/"

# --- Google Health ---------------------------------------------------------
GOOGLE_HEALTH_CLIENT_ID = os.environ.get("GOOGLE_HEALTH_CLIENT_ID", "")
GOOGLE_HEALTH_CLIENT_SECRET = os.environ.get("GOOGLE_HEALTH_CLIENT_SECRET", "")
GOOGLE_HEALTH_REDIRECT_URI = os.environ.get(
    "GOOGLE_HEALTH_REDIRECT_URI",
    "http://localhost:8000/google-health/callback/",
)
GOOGLE_HEALTH_WEBHOOK_AUTHORIZATION = os.environ.get(
    "GOOGLE_HEALTH_WEBHOOK_AUTHORIZATION", ""
)
# profile.readonly is needed because sync runs with compute_basal=True (BMR
# needs age/sex from users.getProfile) — same as the google-health demo.
GOOGLE_HEALTH_DEFAULT_SCOPES = [
    "https://www.googleapis.com/auth/googlehealth.activity_and_fitness.readonly",
    "https://www.googleapis.com/auth/googlehealth.health_metrics_and_measurements.readonly",
    "https://www.googleapis.com/auth/googlehealth.sleep.readonly",
    "https://www.googleapis.com/auth/googlehealth.profile.readonly",
]
GOOGLE_HEALTH_CONNECT_SUCCESS_URL = _BRIDGE_DONE
# Deep link back into the Expo app for googlehealth's first-class mobile flow
# (see api.views.connect_start — the other providers use the browser bridge).
GOOGLE_HEALTH_APP_DEEPLINK = os.environ.get(
    "GOOGLE_HEALTH_APP_DEEPLINK", "superdemo://connected"
)

# --- Garmin ----------------------------------------------------------------
GARMIN_CLIENT_ID = os.environ.get("GARMIN_CLIENT_ID", "")
GARMIN_CLIENT_SECRET = os.environ.get("GARMIN_CLIENT_SECRET", "")
GARMIN_REDIRECT_URI = os.environ.get(
    "GARMIN_REDIRECT_URI", "http://localhost:8000/garmin/callback/"
)
GARMIN_CONNECT_SUCCESS_URL = _BRIDGE_DONE

# --- Oura ------------------------------------------------------------------
OURA_CLIENT_ID = os.environ.get("OURA_CLIENT_ID", "")
OURA_CLIENT_SECRET = os.environ.get("OURA_CLIENT_SECRET", "")
OURA_REDIRECT_URI = os.environ.get(
    "OURA_REDIRECT_URI", "http://localhost:8000/oura/callback/"
)
OURA_WEBHOOK_VERIFICATION_TOKEN = os.environ.get("OURA_WEBHOOK_VERIFICATION_TOKEN", "")
OURA_SANDBOX = os.environ.get("OURA_SANDBOX", "") not in ("", "0", "false")
OURA_CONNECT_SUCCESS_URL = _BRIDGE_DONE

# --- Strava ----------------------------------------------------------------
STRAVA_CLIENT_ID = os.environ.get("STRAVA_CLIENT_ID", "")
STRAVA_CLIENT_SECRET = os.environ.get("STRAVA_CLIENT_SECRET", "")
STRAVA_REDIRECT_URI = os.environ.get(
    "STRAVA_REDIRECT_URI", "http://localhost:8000/strava/callback/"
)
STRAVA_WEBHOOK_VERIFY_TOKEN = os.environ.get("STRAVA_WEBHOOK_VERIFY_TOKEN", "")
STRAVA_CONNECT_SUCCESS_URL = _BRIDGE_DONE

# --- WHOOP -----------------------------------------------------------------
WHOOP_CLIENT_ID = os.environ.get("WHOOP_CLIENT_ID", "")
WHOOP_CLIENT_SECRET = os.environ.get("WHOOP_CLIENT_SECRET", "")
WHOOP_REDIRECT_URI = os.environ.get(
    "WHOOP_REDIRECT_URI", "http://localhost:8000/whoop/callback/"
)
WHOOP_CONNECT_SUCCESS_URL = _BRIDGE_DONE
