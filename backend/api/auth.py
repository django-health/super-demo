"""Token auth for the device API.

The app sends ``Authorization: Token <key>``. Tokens are per-device
(``DeviceToken``), so revoking one device never logs out the others.
"""

from __future__ import annotations

from functools import wraps

from django.http import HttpRequest, JsonResponse
from django.utils import timezone

from .models import DeviceToken


def _token_from_request(request: HttpRequest) -> DeviceToken | None:
    header = request.headers.get("Authorization", "")
    parts = header.split()
    if len(parts) != 2 or parts[0].lower() not in ("token", "bearer"):
        return None
    return (
        DeviceToken.objects.select_related("customer").filter(key=parts[1]).first()
    )


def token_required(view):
    @wraps(view)
    def wrapper(request: HttpRequest, *args, **kwargs):
        token = _token_from_request(request)
        if token is None:
            return JsonResponse({"error": "invalid or missing token"}, status=401)
        token.last_seen_at = timezone.now()
        token.save(update_fields=["last_seen_at"])
        request.user = token.customer
        request.device_token = token
        return view(request, *args, **kwargs)

    return wrapper
