from django.contrib import admin

from .models import BridgeToken, DeviceToken


@admin.register(DeviceToken)
class DeviceTokenAdmin(admin.ModelAdmin):
    list_display = ("customer", "name", "platform", "created_at", "last_seen_at")
    readonly_fields = ("key",)


@admin.register(BridgeToken)
class BridgeTokenAdmin(admin.ModelAdmin):
    list_display = ("customer", "provider", "created_at", "used_at")
    readonly_fields = ("key",)
