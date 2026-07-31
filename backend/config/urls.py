from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    # OAuth web flows + webhooks for every provider package.
    path("google-health/", include("googlehealth.urls")),
    path("garmin/", include("garmin.urls")),
    path("oura/", include("oura.urls")),
    path("strava/", include("strava.urls")),
    path("whoop/", include("whoop.urls")),
    # Device API + the browser bridge the mobile app uses for OAuth.
    path("api/", include("api.urls")),
    path("bridge/", include("api.bridge_urls")),
]
