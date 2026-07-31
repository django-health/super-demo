"""Registry of the wearable provider packages installed in this demo.

Everything the API needs to treat the five packages uniformly: each one
exposes ``models.<X>Connection`` (OneToOne on customer, ``status`` +
``connected_at``), ``ingest.sync_user(connection, *, start, end) ->
SyncResult`` and ``oauth.revoke(connection)``, plus an ``urls.py`` with a
session-authenticated ``connect`` view — so a dataclass of dotted names is
all the glue required.
"""

from __future__ import annotations

from dataclasses import dataclass
from importlib import import_module
from typing import Any

from django.conf import settings


@dataclass(frozen=True)
class Provider:
    slug: str
    label: str
    module: str
    connection_class: str
    settings_prefix: str
    connect_url_name: str
    data_source: str  # healthdatamodel DataSource value written by sync


PROVIDERS: dict[str, Provider] = {
    p.slug: p
    for p in [
        Provider(
            slug="google-health",
            label="Google Health",
            module="googlehealth",
            connection_class="GoogleHealthConnection",
            settings_prefix="GOOGLE_HEALTH",
            connect_url_name="googlehealth:connect",
            data_source="google_health",
        ),
        Provider(
            slug="garmin",
            label="Garmin",
            module="garmin",
            connection_class="GarminConnection",
            settings_prefix="GARMIN",
            connect_url_name="garmin:connect",
            data_source="garmin",
        ),
        Provider(
            slug="oura",
            label="Oura",
            module="oura",
            connection_class="OuraConnection",
            settings_prefix="OURA",
            connect_url_name="oura:connect",
            data_source="oura",
        ),
        Provider(
            slug="strava",
            label="Strava",
            module="strava",
            connection_class="StravaConnection",
            settings_prefix="STRAVA",
            connect_url_name="strava:connect",
            data_source="strava",
        ),
        Provider(
            slug="whoop",
            label="WHOOP",
            module="whoop",
            connection_class="WhoopConnection",
            settings_prefix="WHOOP",
            connect_url_name="whoop:connect",
            data_source="whoop",
        ),
    ]
}


def is_configured(provider: Provider) -> bool:
    return bool(getattr(settings, f"{provider.settings_prefix}_CLIENT_ID", ""))


def connection_model(provider: Provider) -> Any:
    return getattr(import_module(f"{provider.module}.models"), provider.connection_class)


def get_connection(provider: Provider, customer: Any) -> Any | None:
    return connection_model(provider).objects.filter(customer=customer).first()


def sync_user(provider: Provider, connection: Any, *, start, end) -> Any:
    return import_module(f"{provider.module}.ingest").sync_user(
        connection, start=start, end=end
    )


def revoke(provider: Provider, connection: Any) -> None:
    import_module(f"{provider.module}.oauth").revoke(connection)
