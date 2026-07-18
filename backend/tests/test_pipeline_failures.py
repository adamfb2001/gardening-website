"""Every failure is typed, honest, and surfaced — never silent (spec §2, §6)."""

import pytest


@pytest.mark.parametrize(
    "url,code,retryable",
    [
        ("https://www.tiktok.com/@user/video/stub-unavailable", "media_unavailable", True),
        ("https://www.instagram.com/reel/stub-private/", "private_or_geoblocked", False),
        ("https://fb.watch/stub-nocontent/", "no_extractable_content", False),
        ("https://vimeo.com/12345678", "unsupported_platform", False),
        ("https://www.youtube.com/shorts/stub-toolong", "media_too_long", False),
        ("https://www.youtube.com/shorts/stub-crash", "internal_error", True),
    ],
)
def test_failures_are_typed(submit, wait_terminal, url, code, retryable):
    job = submit(url)
    body = wait_terminal(job["job_id"])
    assert body["status"] == "failed"
    assert body["note"] is None
    assert body["error"]["code"] == code
    assert body["error"]["retryable"] is retryable
    assert body["error"]["message"]  # always a human-readable reason


def test_no_speech_clip_still_produces_note_from_visuals(submit, wait_terminal):
    """Music-only clips skip transcription cleanly; the vision path carries
    the note (spec §4.2)."""
    job = submit("https://www.youtube.com/shorts/stub-nospeech")
    body = wait_terminal(job["job_id"])
    assert body["status"] == "complete"
    note = body["note"]
    assert note["confidence"]["audio"] == 0.0
    assert any("no speech" in caveat.lower() for caveat in note["caveats"])
