"""M1 stub pipeline.

Produces deterministic placeholder notes that are honest about being
placeholders (the never-fabricate rule applies to stubs too: every stub note
carries a caveat saying no real analysis happened, and confidence is low).

URL markers let clients and tests drive every failure path without a real
resolver — see backend/README.md:

    stub-unavailable  → media_unavailable (retryable)
    stub-private      → private_or_geoblocked
    stub-nocontent    → no_extractable_content
    stub-toolong      → resolves with duration 900 s; the worker's duration
                        cap then rejects it with media_too_long
    stub-nospeech     → transcriber returns None (music-only path)
    stub-crash        → unhandled exception → internal_error
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from ..config import Settings
from ..models import (
    Category,
    Confidence,
    ErrorCode,
    FrameObservation,
    Note,
    Platform,
    Quote,
    ResolvedMedia,
    Step,
    Transcript,
    TranscriptSegment,
)
from ..urls import detect_platform, normalize_url
from .base import Pipeline, PipelineError

_UNSUPPORTED_MESSAGE = (
    "This link isn't from a supported platform. ClipNotes supports "
    "YouTube Shorts, TikTok, Instagram Reels, and Facebook Reels."
)

_FAILURE_MARKERS: list[tuple[str, ErrorCode, str, bool]] = [
    (
        "stub-unavailable",
        ErrorCode.media_unavailable,
        "The video could not be fetched. It may have been removed, or the platform may be temporarily blocking access.",
        True,
    ),
    (
        "stub-private",
        ErrorCode.private_or_geoblocked,
        "This video is private or not available in your region.",
        False,
    ),
    (
        "stub-nocontent",
        ErrorCode.no_extractable_content,
        "No speech or readable on-screen content could be extracted from this video.",
        False,
    ),
]

_PLATFORM_LABELS: dict[Platform, str] = {
    Platform.youtube_shorts: "YouTube Short",
    Platform.tiktok: "TikTok",
    Platform.instagram_reels: "Instagram Reel",
    Platform.facebook_reels: "Facebook Reel",
}

_STUB_CAVEAT = (
    "Placeholder note from the M1 stub pipeline — content is NOT derived "
    "from the actual video. Real transcription and synthesis arrive in M2."
)


class StubResolver:
    async def resolve(self, url: str) -> ResolvedMedia:
        platform = detect_platform(url)
        if platform is None:
            raise PipelineError(ErrorCode.unsupported_platform, _UNSUPPORTED_MESSAGE, retryable=False)
        for marker, code, message, retryable in _FAILURE_MARKERS:
            if marker in url:
                raise PipelineError(code, message, retryable)
        if "stub-crash" in url:
            raise RuntimeError("simulated resolver crash (stub-crash marker)")
        return ResolvedMedia(
            canonical_url=normalize_url(url),
            platform=platform,
            title=f"Stub {_PLATFORM_LABELS[platform]}",
            creator_handle="@stub.creator",
            duration_seconds=900 if "stub-toolong" in url else 47,
            thumbnail_url=None,
            published_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        )


class StubTranscriber:
    async def transcribe(self, media: ResolvedMedia) -> Optional[Transcript]:
        if "stub-nospeech" in media.canonical_url:
            return None
        return Transcript(
            language="en",
            segments=[
                TranscriptSegment(start_s=0.0, end_s=6.0, text="This is placeholder transcript text from the stub transcriber."),
                TranscriptSegment(start_s=6.0, end_s=14.0, text="Real speech-to-text lands in milestone two."),
            ],
        )


class StubVision:
    async def analyse(self, media: ResolvedMedia) -> list[FrameObservation]:
        return [
            FrameObservation(timestamp_s=2.0, text="[stub] On-screen caption placeholder."),
            FrameObservation(timestamp_s=10.0, text="[stub] Diagram/text placeholder."),
        ]


class StubSynthesiser:
    async def synthesise(
        self,
        media: ResolvedMedia,
        transcript: Optional[Transcript],
        observations: list[FrameObservation],
        locale: str,
    ) -> Note:
        label = _PLATFORM_LABELS[media.platform]
        caveats = [_STUB_CAVEAT]
        audio_confidence = 0.1
        if transcript is None:
            caveats.append("No speech detected; this note is based on visuals only.")
            audio_confidence = 0.0
        return Note(
            title=f"[Stub] Notes for a {label}"[:70],
            summary=(
                f"Placeholder summary for a {label} by {media.creator_handle}. "
                "The processing pipeline is stubbed, so this note contains sample data only."
            ),
            key_points=[segment.text for segment in transcript.segments] if transcript else [obs.text for obs in observations],
            steps=[
                Step(n=1, text="(placeholder) First demonstrated step."),
                Step(n=2, text="(placeholder) Second demonstrated step."),
            ],
            quotes=[Quote(text="placeholder quote from the stub transcript", timestamp_s=6.0)],
            category=Category.other,
            tags=["stub", media.platform.value],
            confidence=Confidence(audio=audio_confidence, visual=0.1, overall=0.1),
            caveats=caveats,
            transcript=transcript.full_text if transcript else None,
            creator_handle=media.creator_handle,
            video_title=media.title,
        )


def build_stub_pipeline(settings: Settings) -> Pipeline:
    return Pipeline(
        resolver=StubResolver(),
        transcriber=StubTranscriber(),
        vision=StubVision(),
        synthesiser=StubSynthesiser(),
    )
