"""Auth models for the device API.

``DeviceToken`` is a long-lived per-device credential — one row per app
install, so the /api/me/ device list doubles as a picture of every device
syncing into the account (the multi-device story).

``BridgeToken`` is a single-use, short-lived token that lets the mobile app
hand a provider OAuth flow to the system browser: the app POSTs
/api/providers/<slug>/connect/, gets back a /bridge/connect/ URL carrying the
token, and the bridge view logs the browser session in before redirecting to
the provider package's ``connect`` view.
"""

from __future__ import annotations

import secrets
from datetime import timedelta

from django.conf import settings
from django.db import models
from django.utils import timezone

BRIDGE_TOKEN_TTL = timedelta(minutes=10)


class DeviceToken(models.Model):
    customer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="device_tokens",
    )
    key = models.CharField(max_length=64, unique=True)
    name = models.CharField(max_length=100, blank=True, default="")
    platform = models.CharField(max_length=20, blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    last_seen_at = models.DateTimeField(null=True, blank=True)

    def __str__(self) -> str:
        return f"{self.customer} — {self.name or 'device'} ({self.platform})"

    @classmethod
    def issue(cls, customer, name: str = "", platform: str = "") -> "DeviceToken":
        return cls.objects.create(
            customer=customer,
            key=secrets.token_hex(20),
            name=name[:100],
            platform=platform[:20],
        )


class BridgeToken(models.Model):
    customer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="bridge_tokens",
    )
    provider = models.CharField(max_length=50)
    key = models.CharField(max_length=64, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    used_at = models.DateTimeField(null=True, blank=True)

    def __str__(self) -> str:
        return f"{self.customer} — {self.provider}"

    @classmethod
    def issue(cls, customer, provider: str) -> "BridgeToken":
        # One pending flow per provider per user; a retry replaces the old row.
        cls.objects.filter(customer=customer, provider=provider, used_at=None).delete()
        return cls.objects.create(
            customer=customer, provider=provider, key=secrets.token_hex(20)
        )

    @classmethod
    def consume(cls, key: str, provider: str) -> "BridgeToken | None":
        token = cls.objects.filter(
            key=key,
            provider=provider,
            used_at=None,
            created_at__gte=timezone.now() - BRIDGE_TOKEN_TTL,
        ).first()
        if token is None:
            return None
        token.used_at = timezone.now()
        token.save(update_fields=["used_at"])
        return token
