"""Network helpers for outbound AI API requests."""

import time

import requests
from django.conf import settings
from urllib3.util import connection


def configure_ai_network() -> None:
    """Prefer IPv4 when the host has IPv6 DNS but no working IPv6 route."""
    if settings.AI_FORCE_IPV4:
        connection.HAS_IPV6 = False


def request_with_retry(request_callable, *, attempts=None, backoff=None, retry_statuses=None):
    """Jalankan request idempoten dengan retry terukur untuk jaringan tidak stabil."""
    max_attempts = max(1, int(attempts or getattr(settings, 'AI_REQUEST_RETRIES', 2) + 1))
    delay = float(backoff if backoff is not None else getattr(settings, 'AI_RETRY_BACKOFF_SECONDS', 1))
    statuses = set(retry_statuses or {408, 425, 429, 500, 502, 503, 504})
    last_error = None
    for attempt in range(max_attempts):
        try:
            response = request_callable()
            if response.status_code not in statuses or attempt == max_attempts - 1:
                return response
            response.close()
        except requests.RequestException as exc:
            last_error = exc
            if attempt == max_attempts - 1:
                raise
        time.sleep(delay * (2 ** attempt))
    if last_error:
        raise last_error
    raise requests.RequestException('Request gagal tanpa respons.')
