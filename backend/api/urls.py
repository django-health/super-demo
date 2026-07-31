from django.urls import path

from . import views

urlpatterns = [
    path("auth/login/", views.login, name="api-login"),
    path("auth/logout/", views.logout, name="api-logout"),
    path("me/", views.me, name="api-me"),
    path("summary/", views.summary, name="api-summary"),
    path("connections/", views.connections, name="api-connections"),
    path("push/records/", views.push_records, name="api-push-records"),
    path("push/workouts/", views.push_workouts, name="api-push-workouts"),
    path("providers/<slug:slug>/connect/", views.provider_connect, name="api-provider-connect"),
    path("providers/<slug:slug>/sync/", views.provider_sync, name="api-provider-sync"),
    path("providers/<slug:slug>/disconnect/", views.provider_disconnect, name="api-provider-disconnect"),
]
