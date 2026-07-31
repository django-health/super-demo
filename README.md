# super-demo

End-to-end demo of the whole **django-health** stack: one Django backend
running **every** wearable integration, plus one React Native codebase that
ships as an iOS app, an Android app, *and* a web app. Connect a cloud
provider on the web, push HealthKit data from your phone, and watch the same
merged dashboard update everywhere — the same shape of product you'd get from
a connection aggregator like Terra, built entirely from the open-source
django-health packages.

```
┌─────────────┐   ┌─────────────┐   ┌─────────────┐
│  iOS app    │   │ Android app │   │   Web app   │      one Expo codebase
│ (HealthKit) │   │ (H.Connect) │   │ (dashboard) │
└──────┬──────┘   └──────┬──────┘   └──────┬──────┘
       │  push records    │  push records   │  read summaries
       ▼                  ▼                 ▼
┌──────────────────────────────────────────────────┐
│                Django backend                    │
│  api/ ─ device tokens, push, summary, bridge     │
│  googlehealth · garmin · oura · strava · whoop   │  ← OAuth + webhooks +
│           django-healthdatamodel                 │    server-side sync
└──────────────────────────────────────────────────┘
```

## What it demonstrates

- **Every provider package in one project** — `django-google-health`,
  `django-garmin`, `django-oura`, `django-strava`, `django-whoop`, all
  writing to `django-healthdatamodel`'s `Record`/`Workout` tables.
- **On-device pipelines** — the app reads Apple HealthKit
  (`@kingstinct/react-native-healthkit`) or Android Health Connect
  (`react-native-health-connect`) and POSTs records in the HealthKit shape
  `healthdatamodel.schemas.RecordInput` accepts verbatim.
- **Multi-device sync** — device tokens are per-install; push from the phone,
  pull-to-refresh on the web, and the merged summary (source-ranked, so two
  pipelines reporting the same day don't double-count) is identical
  everywhere.
- **Mobile OAuth** — the app opens a single-use `/bridge/connect/<provider>/`
  URL in the system browser, which exchanges the token for a session and
  hands off to the provider package's normal `connect` view. (google-health's
  first-class backend-owned mobile flow with an app deep link is also wired —
  POST `{"mode": "native"}` to its connect endpoint.)

## Backend

```bash
cd backend
uv sync
uv run python manage.py migrate
uv run python manage.py seed_demo      # demo/demo + 2 weeks of synthetic data
uv run python manage.py runserver 0.0.0.0:8000
```

Provider credentials come from the same environment variables as each
package's own demo (`GOOGLE_HEALTH_CLIENT_ID`, `GARMIN_CLIENT_ID`,
`OURA_CLIENT_ID`, `STRAVA_CLIENT_ID`, `WHOOP_CLIENT_ID`, plus matching
`_CLIENT_SECRET` / `_REDIRECT_URI`) — see `backend/config/settings.py`.
Providers without credentials show up as “no credentials” in the app.
Unconfigured is fine: the device pipelines and seeded data work with zero
provider setup.

The API is plain Django + JSON (no DRF): `POST /api/auth/login/` issues a
per-device token, `POST /api/push/records/` ingests device data,
`GET /api/summary/` returns merged daily totals, and
`POST /api/providers/<slug>/{connect,sync,disconnect}/` drives the cloud
providers. `uv run pytest` covers the whole surface.

> SQLite works out of the box (the summary endpoint falls back to a
> demo-local ranked aggregation); set `DATABASE_URL=postgres://…` to use
> healthdatamodel's native source-ranked queries.

## App (iOS / Android / web)

```bash
cd app
npm install
npx expo start --web        # web app on http://localhost:8081
```

The health libraries are native modules, so phones need a dev build (not
Expo Go):

```bash
npx expo run:ios            # or: npx expo run:android
```

Sign in with `demo` / `demo`. On a physical phone, point the app at your
machine: `EXPO_PUBLIC_API_URL=http://<your-lan-ip>:8000 npx expo start`.
The Android emulator uses `http://10.0.2.2:8000` automatically. If port
8000 is taken, run the backend on another port and set
`EXPO_PUBLIC_API_URL` to match (it works on web builds too).

The suggested demo loop:

1. `seed_demo`, then sign in on **web** — populated dashboard.
2. Sign in on a **phone**, This Device tab → grant permissions → read →
   push. (`/api/me/` now lists both devices.)
3. Pull-to-refresh the web dashboard — the phone's data is there, deduped
   against the seeded sources.
4. Connections tab → connect a real provider → sync → refresh again.

## Repo layout

```
backend/   Django project: config/ (settings, urls), api/ (device API,
           OAuth bridge, seed_demo), tests/
app/       Expo app: src/app/ (router screens), src/lib/ (API client,
           auth, storage), src/health/ (reader.ios.ts / reader.android.ts /
           reader.ts platform split)
```

## License

BSD 3-Clause, same as the rest of the django-health org.
