"""URL normalisation and platform detection (spec §4.1).

This module is real (not stub) logic: it feeds dedup today and remains the
front door of the M2 resolver. Short-link *expansion* (vm.tiktok.com et al.
require a network round-trip) is deliberately deferred to the M2 resolver;
here short-link hosts are mapped to their platform directly.
"""

from __future__ import annotations

from typing import Optional
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

from .models import Platform

# Share-sheet URLs carry per-share tracking params that must not defeat dedup.
_TRACKING_PARAMS = {
    "si", "feature", "fbclid", "gclid", "igsh", "igshid", "mibextid",
    "share_id", "sender_device", "sender_web_id", "_t", "_r", "t", "s",
}

_PLATFORM_HOSTS: dict[str, Platform] = {
    "youtube.com": Platform.youtube_shorts,
    "youtu.be": Platform.youtube_shorts,
    "tiktok.com": Platform.tiktok,
    "vm.tiktok.com": Platform.tiktok,
    "vt.tiktok.com": Platform.tiktok,
    "instagram.com": Platform.instagram_reels,
    "facebook.com": Platform.facebook_reels,
    "fb.com": Platform.facebook_reels,
    "fb.watch": Platform.facebook_reels,
}


def _clean_host(netloc: str) -> str:
    host = netloc.lower().split("@")[-1].split(":")[0]
    for prefix in ("www.", "m.", "web."):
        if host.startswith(prefix):
            host = host[len(prefix):]
            break
    return host


def normalize_url(url: str) -> str:
    """Canonicalise a shared URL: lower-case host, strip mobile/www prefixes,
    tracking params, and fragments, so re-shares of the same clip dedup."""
    parsed = urlparse(url)
    host = _clean_host(parsed.netloc)
    path = parsed.path.rstrip("/") or "/"
    params = [
        (key, value)
        for key, value in parse_qsl(parsed.query, keep_blank_values=True)
        if key.lower() not in _TRACKING_PARAMS and not key.lower().startswith("utm_")
    ]
    query = urlencode(sorted(params))
    return urlunparse((parsed.scheme.lower(), host, path, "", query, ""))


def detect_platform(url: str) -> Optional[Platform]:
    """Map a URL's host to a supported platform, or None if unsupported.

    Kept permissive per platform in M1 (e.g. any youtube.com path counts as
    youtube_shorts); the M2 resolver narrows by media type, and the generic
    duration cap already rejects long-form video.
    """
    host = _clean_host(urlparse(url).netloc)
    if host in _PLATFORM_HOSTS:
        return _PLATFORM_HOSTS[host]
    # Fall back to registrable-domain match for unlisted subdomains
    # (music.youtube.com, mbasic.facebook.com, ...).
    for known, platform in _PLATFORM_HOSTS.items():
        if host.endswith("." + known):
            return platform
    return None
