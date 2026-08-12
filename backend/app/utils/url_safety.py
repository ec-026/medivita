"""Strict URL validation and canonicalization for trusted-source retrieval."""

from __future__ import annotations

import ipaddress
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

TRACKING_KEYS = {"fbclid", "gclid", "mc_cid", "mc_eid", "ref", "source"}


def is_trusted_https_url(url: str, domain: str) -> bool:
    try:
        parsed = urlparse(url)
        hostname = (parsed.hostname or "").lower().rstrip(".")
        expected = domain.lower().rstrip(".")
        if parsed.scheme.lower() != "https" or not hostname or parsed.username or parsed.password:
            return False
        if parsed.port not in (None, 443):
            return False
        try:
            ipaddress.ip_address(hostname)
            return False
        except ValueError:
            pass
        return hostname == expected or hostname.endswith(f".{expected}")
    except ValueError:
        return False


def is_allowed_https_url(url: str, domains: set[str]) -> bool:
    return any(is_trusted_https_url(url, domain) for domain in domains)


def canonical_url(url: str) -> str:
    parsed = urlparse(url)
    hostname = (parsed.hostname or "").lower().rstrip(".")
    netloc = hostname if parsed.port in (None, 443) else parsed.netloc.lower()
    path = parsed.path.rstrip("/") or "/"
    query = urlencode(
        sorted(
            (key, value)
            for key, value in parse_qsl(parsed.query, keep_blank_values=True)
            if not key.lower().startswith("utm_") and key.lower() not in TRACKING_KEYS
        )
    )
    return urlunparse((parsed.scheme.lower(), netloc, path, "", query, ""))

