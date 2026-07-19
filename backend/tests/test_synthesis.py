"""Unit tests for the real pipeline's synthesisers and error mapping."""

import asyncio
from types import SimpleNamespace

import pytest

from clipnotes.models import (
    Category,
    Confidence,
    Entities,
    Platform,
    ResolvedMedia,
    Transcript,
    TranscriptSegment,
)
from clipnotes.pipeline.base import PipelineError
from clipnotes.pipeline.real import YtDlpResolver, _map_ytdlp_error
from clipnotes.pipeline.synth import (
    ClaudeSynthesiser,
    HeuristicSynthesiser,
    _SynthesisedNote,
)
from conftest import make_settings

MEDIA = ResolvedMedia(
    canonical_url="https://youtube.com/shorts/abc123",
    platform=Platform.youtube_shorts,
    title="Perfect scrambled eggs in 60 seconds",
    creator_handle="@chef",
    duration_seconds=58,
)

COOKING_TRANSCRIPT = Transcript(
    language="en",
    audio_confidence=0.9,
    segments=[
        TranscriptSegment(start_s=0.0, end_s=5.0, text="Today I'll show you how to cook perfect scrambled eggs."),
        TranscriptSegment(start_s=5.0, end_s=10.0, text="Start with butter in a cold pan, then add the eggs."),
        TranscriptSegment(start_s=10.0, end_s=15.0, text="Keep the heat low and stir constantly for a creamy dish."),
        TranscriptSegment(start_s=15.0, end_s=20.0, text="Season with salt only at the end, in the kitchen that matters."),
        TranscriptSegment(start_s=20.0, end_s=25.0, text="A great chef never rushes the recipe with high heat."),
    ],
)


def run(coro):
    return asyncio.run(coro)


# ---------------------------------------------------------------------------
# Heuristic synthesiser


def test_heuristic_produces_honest_extractive_note():
    note = run(HeuristicSynthesiser().synthesise(MEDIA, COOKING_TRANSCRIPT, [], "en"))

    assert note.title == "Perfect scrambled eggs in 60 seconds"
    assert note.category == Category.cooking_food
    assert note.summary.startswith("Today I'll show you")
    assert note.key_points  # excerpts from later sentences
    assert note.steps == []  # heuristics never invent procedures
    assert note.confidence.visual == 0.0
    assert 0.0 < note.confidence.overall < note.confidence.audio
    assert any("without AI" in caveat for caveat in note.caveats)
    assert any("isual" in caveat for caveat in note.caveats)
    assert note.transcript == COOKING_TRANSCRIPT.full_text
    assert note.creator_handle == "@chef"
    assert note.video_title == MEDIA.title


def test_heuristic_no_speech_note_is_metadata_only():
    note = run(HeuristicSynthesiser().synthesise(MEDIA, None, [], "en"))
    assert note.confidence.overall == 0.0
    assert note.transcript is None
    assert any("No speech" in caveat for caveat in note.caveats)


def test_heuristic_uncategorisable_content_falls_to_other():
    transcript = Transcript(
        language="en",
        segments=[TranscriptSegment(start_s=0, end_s=2, text="Wow amazing unbelievable moments compilation.")],
    )
    note = run(HeuristicSynthesiser().synthesise(MEDIA.model_copy(update={"title": "Wow"}), transcript, [], "en"))
    assert note.category == Category.other


# ---------------------------------------------------------------------------
# Claude synthesiser (faked client — no network)


class FakeMessages:
    def __init__(self, result=None, error=None):
        self.result = result
        self.error = error
        self.last_kwargs = None

    async def parse(self, **kwargs):
        self.last_kwargs = kwargs
        if self.error is not None:
            raise self.error
        return SimpleNamespace(parsed_output=self.result, stop_reason="end_turn")


def make_claude(result=None, error=None):
    fake = FakeMessages(result=result, error=error)
    synthesiser = ClaudeSynthesiser(
        make_settings(),
        fallback=HeuristicSynthesiser(),
        client=SimpleNamespace(messages=fake),
    )
    return synthesiser, fake


def test_claude_synthesis_is_finalised_with_invariants():
    fields = _SynthesisedNote(
        title="A very long title that exceeds the seventy character contract limit by quite a bit",
        summary="Low heat and constant stirring make creamy scrambled eggs.",
        key_points=["Start in a cold pan with butter", "Salt only at the end"],
        steps=[],
        entities=Entities(),
        quotes=[],
        category=Category.cooking_food,
        tags=["cooking", "eggs"],
        # Model claims visual confidence — the backend must zero it (no vision).
        confidence=Confidence(audio=0.9, visual=0.8, overall=0.95),
        caveats=[],
    )
    synthesiser, fake = make_claude(result=fields)
    note = run(synthesiser.synthesise(MEDIA, COOKING_TRANSCRIPT, [], "en-GB"))

    assert len(note.title) <= 70
    assert note.confidence.visual == 0.0
    assert note.confidence.overall <= note.confidence.audio
    assert any("isual" in caveat for caveat in note.caveats)
    assert note.transcript == COOKING_TRANSCRIPT.full_text
    assert note.creator_handle == "@chef"
    # The request carried the transcript with timestamps and the metadata
    prompt = fake.last_kwargs["messages"][0]["content"]
    assert "[0.0s]" in prompt and "@chef" in prompt
    assert fake.last_kwargs["output_format"] is _SynthesisedNote


def test_claude_failure_falls_back_to_heuristic_with_caveat():
    synthesiser, _ = make_claude(error=RuntimeError("api down"))
    note = run(synthesiser.synthesise(MEDIA, COOKING_TRANSCRIPT, [], "en"))
    assert note.summary.startswith("Today I'll show you")  # heuristic content
    assert any("AI synthesis was unavailable" in caveat for caveat in note.caveats)


def test_claude_skips_api_when_no_speech():
    synthesiser, fake = make_claude(error=RuntimeError("should not be called"))
    note = run(synthesiser.synthesise(MEDIA, None, [], "en"))
    assert fake.last_kwargs is None  # no API call
    assert note.confidence.overall == 0.0


# ---------------------------------------------------------------------------
# Resolver error mapping


@pytest.mark.parametrize(
    "message,code,retryable",
    [
        ("ERROR: [youtube] abc: Video unavailable", "media_unavailable", True),
        ("ERROR: [youtube] abc: Private video. Sign in if you've been granted access", "private_or_geoblocked", False),
        ("ERROR: [instagram] abc: login required to access this content", "private_or_geoblocked", False),
        ("Unsupported URL: https://example.com/clip", "unsupported_platform", False),
        ("HTTP Error 500: something odd", "media_unavailable", True),
        # Bot checks and CDN 403s (datacenter/VPN egress) are retryable and
        # must not masquerade as "private video".
        ("ERROR: [youtube] abc: Sign in to confirm you're not a bot.", "media_unavailable", True),
        ("ERROR: unable to download video data: HTTP Error 403: Forbidden", "media_unavailable", True),
    ],
)
def test_ytdlp_errors_map_to_typed_codes(message, code, retryable):
    mapped = _map_ytdlp_error(Exception(message))
    assert mapped.code.value == code
    assert mapped.retryable is retryable


def test_resolver_rejects_unsupported_hosts_without_network():
    with pytest.raises(PipelineError) as excinfo:
        run(YtDlpResolver().resolve("https://vimeo.com/12345"))
    assert excinfo.value.code.value == "unsupported_platform"
