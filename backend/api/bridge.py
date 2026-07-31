"""Browser bridge for provider OAuth flows started from the mobile app.

The provider packages' ``connect`` views are session-authenticated web views.
A native app has a device token, not a session cookie — so the app opens
``/bridge/connect/<slug>/?t=<single-use token>`` in the system browser, this
view exchanges the token for a logged-in session, and hands off to the
package's own connect view. After the provider callback, the package
redirects to ``/bridge/done/`` (via ``*_CONNECT_SUCCESS_URL``), which tells
the user to head back to the app.
"""

from __future__ import annotations

from django.contrib.auth import login as session_login
from django.http import HttpRequest, HttpResponse, HttpResponseForbidden
from django.shortcuts import redirect, render
from django.urls import reverse

from . import providers
from .models import BridgeToken


def connect(request: HttpRequest, slug: str) -> HttpResponse:
    provider = providers.PROVIDERS.get(slug)
    if provider is None:
        return HttpResponseForbidden("unknown provider")
    token = BridgeToken.consume(request.GET.get("t", ""), slug)
    if token is None:
        return HttpResponseForbidden(
            "This connect link has expired — go back to the app and try again."
        )
    session_login(
        request, token.customer, backend="django.contrib.auth.backends.ModelBackend"
    )
    return redirect(reverse(provider.connect_url_name))


def done(request: HttpRequest) -> HttpResponse:
    return render(request, "bridge/done.html")
