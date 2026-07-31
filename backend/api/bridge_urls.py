from django.urls import path

from . import bridge

urlpatterns = [
    path("connect/<slug:slug>/", bridge.connect, name="bridge-connect"),
    path("done/", bridge.done, name="bridge-done"),
]
