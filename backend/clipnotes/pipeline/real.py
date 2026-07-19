"""Real media pipeline: yt-dlp resolves and fetches media, faster-whisper
transcribes it locally (no API key needed).

Media files live only inside a per-job temp directory and are deleted the
moment transcription finishes — only the transcript is kept.
"""

from __future__ import annotations

import asyncio
import logging
import math
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import yt_dlp

from ..config import Settings
from ..models import (
    ErrorCode,
    FrameObservation,
    Platform,
    ResolvedMedia,
    Transcript,
    TranscriptSegment,
)
from ..urls import detect_platform, normalize_url
from .base import PipelineError

log = logging.getLogger(__name__)

_UNSUPPORTED_MESSAGE = (
    "This link isn't from a supported platform. ClipNotes supports "
    "YouTube Shorts, TikTok, Instagram Reels, and Facebook Reels."
)

_YDL_BASE_OPTS = {
    "quiet": True,
    "no_warnings": True,
    "noprogress": True,
    "noplaylist": True,
    "socket_timeout": 20,
}


def _map_ytdlp_error(error: Exception) -> PipelineError:
    """Translate yt-dlp failures into typed, user-facing errors."""
    message = str(error).lower()
    if "unsupported url" in message:
        return PipelineError(ErrorCode.unsupported_platform, _UNSUPPORTED_MESSAGE, retryable=False)
    if "not a bot" in message or "403" in message:
        # Platforms bot-block datacenter/VPN egress IPs; the same request
        # usually works from a home network.
        return PipelineError(
            ErrorCode.media_unavailable,
            "The platform is blocking automated access from this server's network. "
            "This usually works when the backend runs on a home network; try again later.",
            retryable=True,
        )
    if "private" in message or "login" in message or "sign in" in message or "not available in your country" in message:
        return PipelineError(
            ErrorCode.private_or_geoblocked,
            "This video is private, requires a login, or isn't available in your region.",
            retryable=False,
        )
    if "unavailable" in message or "removed" in message or "does not exist" in message or "terminated" in message:
        return PipelineError(
            ErrorCode.media_unavailable,
            "The video could not be fetched. It may have been removed or made unavailable.",
            retryable=True,
        )
    return PipelineError(
        ErrorCode.media_unavailable,
        "The video could not be fetched from the platform. This is sometimes temporary — try again.",
        retryable=True,
    )


class YtDlpResolver:
    """URL → media metadata via yt-dlp (no download at this stage)."""

    async def resolve(self, url: str) -> ResolvedMedia:
        platform = detect_platform(url)
        if platform is None:
            raise PipelineError(ErrorCode.unsupported_platform, _UNSUPPORTED_MESSAGE, retryable=False)
        try:
            info = await asyncio.to_thread(self._extract_info, url)
        except PipelineError:
            raise
        except Exception as error:
            log.warning("resolve failed for %s: %s", url, error)
            raise _map_ytdlp_error(error) from error

        published_at = None
        upload_date = info.get("upload_date")
        if upload_date:
            try:
                published_at = datetime.strptime(upload_date, "%Y%m%d").replace(tzinfo=timezone.utc)
            except ValueError:
                pass

        handle = info.get("uploader_id") or info.get("channel") or info.get("uploader") or "unknown"
        duration = info.get("duration")
        return ResolvedMedia(
            canonical_url=info.get("webpage_url") or normalize_url(url),
            platform=platform,
            title=info.get("title") or "Untitled video",
            creator_handle=str(handle),
            # Some platforms omit duration in metadata; treat unknown as 0 so
            # the cap doesn't false-positive (the clip is still fetched below).
            duration_seconds=int(duration) if duration else 0,
            thumbnail_url=info.get("thumbnail"),
            published_at=published_at,
        )

    @staticmethod
    def _extract_info(url: str) -> dict:
        with yt_dlp.YoutubeDL({**_YDL_BASE_OPTS, "skip_download": True}) as ydl:
            return ydl.extract_info(url, download=False)


class WhisperTranscriber:
    """Downloads the audio track and transcribes it with local Whisper.

    The model is loaded lazily (first job downloads it from Hugging Face) and
    transcriptions are serialised — they're CPU-bound, so running them
    concurrently on a laptop just thrashes.
    """

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._model = None
        self._lock = asyncio.Lock()

    async def transcribe(self, media: ResolvedMedia) -> Optional[Transcript]:
        async with self._lock:
            return await asyncio.to_thread(self._transcribe_sync, media)

    def _transcribe_sync(self, media: ResolvedMedia) -> Optional[Transcript]:
        with tempfile.TemporaryDirectory(prefix="clipnotes-") as tmpdir:
            audio_path = self._download_audio(media.canonical_url, Path(tmpdir))
            language, segments = self._run_whisper(audio_path)
        # Temp dir (and the media file) is gone here — only text survives.
        if not segments:
            return None
        logprobs = [avg_logprob for _, _, _, avg_logprob in segments]
        confidence = clamp01(math.exp(sum(logprobs) / len(logprobs)))
        return Transcript(
            language=language or "unknown",
            segments=[
                TranscriptSegment(start_s=start, end_s=end, text=text)
                for start, end, text, _ in segments
            ],
            audio_confidence=confidence,
        )

    @staticmethod
    def _download_audio(url: str, tmpdir: Path) -> Path:
        opts = {
            **_YDL_BASE_OPTS,
            # Audio only where the platform offers it; some (e.g. Instagram)
            # only serve muxed files — Whisper decodes those fine via PyAV.
            "format": "bestaudio/best",
            "outtmpl": str(tmpdir / "media.%(ext)s"),
        }
        try:
            with yt_dlp.YoutubeDL(opts) as ydl:
                ydl.extract_info(url, download=True)
        except Exception as error:
            log.warning("audio download failed for %s: %s", url, error)
            raise _map_ytdlp_error(error) from error
        files = sorted(tmpdir.glob("media.*"))
        if not files:
            raise PipelineError(
                ErrorCode.media_unavailable,
                "The platform returned no downloadable media for this video.",
                retryable=True,
            )
        return files[0]

    def _run_whisper(self, audio_path: Path) -> tuple[str, list[tuple[float, float, str, float]]]:
        if self._model is None:
            from faster_whisper import WhisperModel

            log.info("loading whisper model %r (first use downloads it)", self._settings.whisper_model)
            self._model = WhisperModel(
                self._settings.whisper_model,
                device="cpu",
                compute_type=self._settings.whisper_compute_type,
            )
        segments, info = self._model.transcribe(str(audio_path), vad_filter=True)
        results: list[tuple[float, float, str, float]] = []
        for segment in segments:
            text = segment.text.strip()
            if text:
                results.append((float(segment.start), float(segment.end), text, float(segment.avg_logprob)))
        return info.language or "", results


class NoopVision:
    """The vision path isn't built yet; the transcript carries the note.

    Synthesisers must reflect this honestly (visual confidence 0 + caveat).
    """

    async def analyse(self, media: ResolvedMedia) -> list[FrameObservation]:
        return []


def clamp01(value: float) -> float:
    if math.isnan(value):
        return 0.0
    return max(0.0, min(1.0, value))
