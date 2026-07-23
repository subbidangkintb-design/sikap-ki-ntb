"""Network helpers for outbound AI API requests."""

from django.conf import settings
from urllib3.util import connection


def configure_ai_network() -> None:
    """Prefer IPv4 when the host has IPv6 DNS but no working IPv6 route."""
    if settings.AI_FORCE_IPV4:
        connection.HAS_IPV6 = False
