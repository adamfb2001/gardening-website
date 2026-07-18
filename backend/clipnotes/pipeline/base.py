"""Pipeline stage interfaces (spec §4).

Each stage is a small protocol so implementations can be swapped per platform
or per milestone (stub today; yt-dlp/Whisper/VLM/LLM from M2 on) without
touching the worker or the API layer.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Protocol

from ..models import (
    ErrorCode,
    FrameObservation,
    Note,
    ResolvedMedia,
    Transcript,
)


class PipelineError(Exception):
    """A typed, user-surfaceable failure in any pipeline stage."""

    def __init__(self, code: ErrorCode, message: str, retryable: bool) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.retryable = retryable


class Resolver(Protocol):
    async def resolve(self, url: str) -> ResolvedMedia:
        """URL → media metadata. Raises PipelineError on unsupported or
        unavailable media."""
        ...


class Transcriber(Protocol):
    async def transcribe(self, media: ResolvedMedia) -> Optional[Transcript]:
        """Audio → transcript. Returns None for no-speech clips (music only);
        the vision path carries the note instead (spec §4.2)."""
        ...


class VisionAnalyser(Protocol):
    async def analyse(self, media: ResolvedMedia) -> list[FrameObservation]:
        """Keyframes → per-frame observations of information-bearing content."""
        ...


class Synthesiser(Protocol):
    async def synthesise(
        self,
        media: ResolvedMedia,
        transcript: Optional[Transcript],
        observations: list[FrameObservation],
        locale: str,
    ) -> Note:
        """Transcript + observations + metadata → structured note (spec §4.4)."""
        ...


@dataclass
class Pipeline:
    resolver: Resolver
    transcriber: Transcriber
    vision: VisionAnalyser
    synthesiser: Synthesiser
