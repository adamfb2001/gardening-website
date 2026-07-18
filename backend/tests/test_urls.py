"""URL normalisation and platform detection (spec §4.1)."""

import pytest

from clipnotes.models import Platform
from clipnotes.urls import detect_platform, normalize_url


@pytest.mark.parametrize(
    "raw,expected",
    [
        # Share-tracking params stripped, host lower-cased and de-prefixed
        (
            "https://www.YouTube.com/shorts/abc123?si=xyz&utm_source=share",
            "https://youtube.com/shorts/abc123",
        ),
        ("https://m.youtube.com/shorts/abc123/", "https://youtube.com/shorts/abc123"),
        ("https://youtu.be/abc123?feature=share#t=5", "https://youtu.be/abc123"),
        # Meaningful params survive
        ("https://www.youtube.com/watch?v=abc123&si=x", "https://youtube.com/watch?v=abc123"),
        (
            "https://www.tiktok.com/@chef/video/7300000000000000000?_t=8k&_r=1",
            "https://tiktok.com/@chef/video/7300000000000000000",
        ),
        ("https://www.instagram.com/reel/Cxyz/?igsh=abc", "https://instagram.com/reel/Cxyz"),
    ],
)
def test_normalize_url(raw, expected):
    assert normalize_url(raw) == expected


@pytest.mark.parametrize(
    "url,platform",
    [
        ("https://www.youtube.com/shorts/abc", Platform.youtube_shorts),
        ("https://youtu.be/abc", Platform.youtube_shorts),
        ("https://music.youtube.com/watch?v=abc", Platform.youtube_shorts),
        ("https://www.tiktok.com/@user/video/123", Platform.tiktok),
        ("https://vm.tiktok.com/ZMabcdef/", Platform.tiktok),
        ("https://vt.tiktok.com/ZSabcdef/", Platform.tiktok),
        ("https://www.instagram.com/reel/Cxyz/", Platform.instagram_reels),
        ("https://www.facebook.com/reel/123456", Platform.facebook_reels),
        ("https://fb.watch/abcdef/", Platform.facebook_reels),
    ],
)
def test_detect_platform(url, platform):
    assert detect_platform(url) == platform


@pytest.mark.parametrize(
    "url",
    [
        "https://vimeo.com/12345",
        "https://example.com/watch?v=abc",
        "https://notyoutube.com/shorts/abc",  # suffix spoofing must not match
        "https://youtube.com.evil.example/shorts/abc",
    ],
)
def test_unsupported_hosts(url):
    assert detect_platform(url) is None
