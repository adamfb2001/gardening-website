"""Note synthesis.

Two implementations behind the same interface:

- ClaudeSynthesiser — sends transcript + metadata to the Claude API and gets
  back a schema-validated note. Requires ANTHROPIC_API_KEY (or another SDK
  credential) on the *backend*; the phone never sees it. Falls back to the
  heuristic synthesiser on any failure, with an honest caveat.
- HeuristicSynthesiser — keyless: extractive summary, keyword categorisation.
  Every note says plainly that it was built without AI synthesis.

Both are honest about the missing vision path: visual confidence is 0 and a
caveat says on-screen content wasn't analysed.
"""

from __future__ import annotations

import logging
import os
import re
from collections import Counter
from typing import Optional

from pydantic import BaseModel, Field

from ..config import Settings
from ..models import (
    Category,
    Confidence,
    Entities,
    FrameObservation,
    Note,
    Platform,
    Quote,
    ResolvedMedia,
    Step,
    Transcript,
)
from .real import clamp01

log = logging.getLogger(__name__)

_NO_VISION_CAVEAT = "Visual content (on-screen text, captions, demonstrations) was not analysed."

_PLATFORM_LABELS: dict[Platform, str] = {
    Platform.youtube_shorts: "YouTube Short",
    Platform.tiktok: "TikTok",
    Platform.instagram_reels: "Instagram Reel",
    Platform.facebook_reels: "Facebook Reel",
}


def build_synthesiser(settings: Settings):
    heuristic = HeuristicSynthesiser()
    mode = settings.synthesis_mode.lower()
    has_credentials = bool(os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("ANTHROPIC_AUTH_TOKEN"))
    if mode == "claude" or (mode == "auto" and has_credentials):
        log.info("synthesis: Claude (%s) with heuristic fallback", settings.anthropic_model)
        return ClaudeSynthesiser(settings, fallback=heuristic)
    log.info("synthesis: heuristic (no Anthropic credential; set ANTHROPIC_API_KEY to enable Claude)")
    return heuristic


def _finalise(note: Note, media: ResolvedMedia, transcript: Optional[Transcript]) -> Note:
    """Attach backend-owned fields and enforce invariants no synthesiser may
    break: title length, clamped confidence, zero visual confidence (no
    vision path), and the no-vision caveat."""
    caveats = list(note.caveats)
    if not any("visual" in caveat.lower() for caveat in caveats):
        caveats.append(_NO_VISION_CAVEAT)
    audio = clamp01(note.confidence.audio)
    overall = min(clamp01(note.confidence.overall), audio) if transcript else 0.0
    return note.model_copy(
        update={
            "title": note.title[:70],
            "confidence": Confidence(audio=audio, visual=0.0, overall=overall),
            "caveats": caveats,
            "transcript": transcript.full_text if transcript else None,
            "creator_handle": media.creator_handle,
            "video_title": media.title,
        }
    )


# ---------------------------------------------------------------------------
# Heuristic (keyless) synthesis


_SENTENCE_SPLIT = re.compile(r"(?<=[.!?])\s+")
_URL_PATTERN = re.compile(r"https?://[^\s\"'<>]+")
_WORD_PATTERN = re.compile(r"[a-zA-Z][a-zA-Z'-]{3,}")

_STOPWORDS = {
    "this", "that", "with", "have", "will", "your", "just", "like", "what",
    "when", "they", "them", "then", "than", "there", "here", "about", "because",
    "really", "going", "gonna", "want", "need", "make", "little", "very",
    "you're", "it's", "don't", "doesn't", "can't", "that's", "we're", "i'm",
    "into", "over", "some", "more", "much", "only", "also", "been", "were",
    "from", "would", "could", "should", "these", "those", "which", "where",
    "thing", "things", "know", "right", "okay", "yeah", "actually", "look",
}

_CATEGORY_KEYWORDS: dict[Category, tuple[str, ...]] = {
    Category.cooking_food: ("recipe", "cook", "bake", "oven", "ingredient", "sauce", "chef", "flavour", "flavor", "dish", "kitchen", "food", "pasta", "meat", "butter", "delicious"),
    Category.fitness_health: ("workout", "exercise", "gym", "muscle", "protein", "calorie", "stretch", "cardio", "health", "diet", "reps", "training"),
    Category.finance_money: ("money", "invest", "stock", "saving", "budget", "tax", "income", "debt", "credit", "salary", "portfolio", "compound"),
    Category.tech_software: ("app", "software", "code", "computer", "iphone", "android", "tech", "program", "website", "gadget", "settings", "shortcut"),
    Category.diy_home: ("diy", "repair", "paint", "drill", "garden", "clean", "wall", "wood", "screw", "renovation", "hack", "glue"),
    Category.career_productivity: ("job", "career", "interview", "resume", "productivity", "meeting", "boss", "linkedin", "habit", "focus", "deadline", "email"),
    Category.travel: ("travel", "flight", "hotel", "airport", "trip", "destination", "visa", "pack", "tour", "beach", "itinerary", "country"),
    Category.learning_science: ("science", "history", "brain", "study", "learn", "math", "physics", "space", "experiment", "fact", "theory", "research"),
    Category.style_grooming: ("outfit", "fashion", "style", "hair", "skin", "makeup", "wear", "grooming", "beard", "clothes", "skincare", "fit"),
}


class HeuristicSynthesiser:
    """Extractive notes with zero external dependencies. Honest by
    construction: excerpts, not understanding."""

    async def synthesise(
        self,
        media: ResolvedMedia,
        transcript: Optional[Transcript],
        observations: list[FrameObservation],
        locale: str,
    ) -> Note:
        label = _PLATFORM_LABELS[media.platform]
        title = (media.title or f"Notes: {label}").strip()[:70]

        if transcript is None or not transcript.segments:
            note = Note(
                title=title,
                summary=(
                    f"No speech was detected in this {label} by {media.creator_handle}, and visual "
                    "analysis isn't built yet, so only the video's metadata is available."
                ),
                category=self._categorise(media.title or ""),
                tags=[],
                confidence=Confidence(audio=0.0, visual=0.0, overall=0.0),
                caveats=["No speech was detected; this note contains metadata only."],
            )
            return _finalise(note, media, transcript)

        text = transcript.full_text
        sentences = [s.strip() for s in _SENTENCE_SPLIT.split(text) if s.strip()]
        summary = " ".join(sentences[:2])[:300] or text[:300]
        key_points = self._sample_key_points(sentences, skip=2)
        audio_confidence = clamp01(transcript.audio_confidence or 0.5)

        note = Note(
            title=title,
            summary=summary,
            key_points=key_points,
            entities=Entities(links_mentioned=_URL_PATTERN.findall(text)[:5]),
            category=self._categorise(f"{media.title or ''} {text}"),
            tags=self._tags(text),
            # Overall is discounted: excerpting is not understanding.
            confidence=Confidence(audio=audio_confidence, visual=0.0, overall=audio_confidence * 0.5),
            caveats=[
                "Generated without AI synthesis: the summary and key points are excerpts "
                "from the transcript, not a distilled summary. Set ANTHROPIC_API_KEY on "
                "the backend for full notes.",
            ],
        )
        return _finalise(note, media, transcript)

    @staticmethod
    def _sample_key_points(sentences: list[str], skip: int, limit: int = 5) -> list[str]:
        candidates = [s for s in sentences[skip:] if len(s) > 25]
        if not candidates:
            return []
        if len(candidates) <= limit:
            picked = candidates
        else:
            step = len(candidates) / limit
            picked = [candidates[int(i * step)] for i in range(limit)]
        return [point[:180] for point in picked]

    @staticmethod
    def _categorise(text: str) -> Category:
        lowered = text.lower()
        scores = {
            category: sum(lowered.count(keyword) for keyword in keywords)
            for category, keywords in _CATEGORY_KEYWORDS.items()
        }
        best = max(scores, key=lambda category: scores[category])
        return best if scores[best] >= 2 else Category.other

    @staticmethod
    def _tags(text: str) -> list[str]:
        words = [w.lower() for w in _WORD_PATTERN.findall(text)]
        counts = Counter(w for w in words if w not in _STOPWORDS)
        return [word for word, count in counts.most_common(4) if count >= 2]


# ---------------------------------------------------------------------------
# Claude synthesis


class _SynthesisedNote(BaseModel):
    """What Claude fills in — the §4.4 schema minus backend-owned fields.
    Kept constraint-free; _finalise() enforces the invariants."""

    title: str = Field(description="≤70 chars, descriptive not clickbait")
    summary: str = Field(description="1-3 sentences capturing the actual takeaway")
    key_points: list[str]
    steps: list[Step]
    entities: Entities
    quotes: list[Quote]
    category: Category
    tags: list[str]
    confidence: Confidence
    caveats: list[str]


_SYNTH_SYSTEM_PROMPT = """You turn transcripts of short-form videos into concise reference notes for a personal knowledge library. The reader saved this video because it seemed useful and wants the substance without rewatching.

Rules:
- Everything you assert must be traceable to the transcript or the video metadata. Never invent facts, numbers, names, or steps.
- key_points: the distilled substance (not excerpts). Omit filler, hype, and calls to action.
- steps: fill ONLY if the video actually teaches a procedure, in order; otherwise [].
- quotes: at most 2, verbatim from the transcript, ≤15 words, only where exact wording matters; timestamp_s is the start time of the segment the words come from. Prefer none.
- entities: only people/products/places/tools actually mentioned. links_mentioned: only URLs spoken or written in the transcript.
- category: exactly one from the fixed list. tags: 3-6 short lowercase topical tags.
- Visual content was NOT analysed (no frames were extracted). Set confidence.visual to 0.0 and reflect in caveats that on-screen content may be missing. If the transcript suggests key info was shown on screen rather than spoken, say so in caveats.
- confidence.audio: how reliable the transcript seems (an ASR confidence hint is provided). confidence.overall: your confidence that the note captures the video's substance.
- caveats: honest limitations only — unclear audio, missing visual context, claims by the creator you cannot verify. Never pad."""


class ClaudeSynthesiser:
    def __init__(self, settings: Settings, fallback: HeuristicSynthesiser, client=None) -> None:
        import anthropic

        self._settings = settings
        self._fallback = fallback
        # Zero-arg client resolves ANTHROPIC_API_KEY / ANTHROPIC_AUTH_TOKEN /
        # an `ant auth login` profile from the environment.
        self._client = client or anthropic.AsyncAnthropic()

    async def synthesise(
        self,
        media: ResolvedMedia,
        transcript: Optional[Transcript],
        observations: list[FrameObservation],
        locale: str,
    ) -> Note:
        if transcript is None or not transcript.segments:
            # Nothing for the model to work from (no speech, no vision yet).
            return await self._fallback.synthesise(media, transcript, observations, locale)
        try:
            fields = await self._call_claude(media, transcript, locale)
        except Exception as error:
            log.warning("Claude synthesis failed (%s: %s); using heuristic fallback", type(error).__name__, error)
            note = await self._fallback.synthesise(media, transcript, observations, locale)
            return note.model_copy(
                update={"caveats": [f"AI synthesis was unavailable ({type(error).__name__}); these notes are transcript excerpts.", *note.caveats[1:]]}
            )
        note = Note(
            # Truncate before construction — Note enforces max_length=70, and a
            # verbose title must not turn a good synthesis into a crash.
            title=fields.title[:70],
            summary=fields.summary,
            key_points=fields.key_points,
            steps=fields.steps,
            entities=fields.entities,
            quotes=fields.quotes,
            category=fields.category,
            tags=fields.tags,
            confidence=fields.confidence,
            caveats=fields.caveats,
        )
        return _finalise(note, media, transcript)

    async def _call_claude(self, media: ResolvedMedia, transcript: Transcript, locale: str) -> _SynthesisedNote:
        lines = [f"[{segment.start_s:.1f}s] {segment.text}" for segment in transcript.segments]
        asr_hint = (
            f"{transcript.audio_confidence:.2f}" if transcript.audio_confidence is not None else "unknown"
        )
        user_message = (
            f"Platform: {_PLATFORM_LABELS[media.platform]}\n"
            f"Video title: {media.title}\n"
            f"Creator: {media.creator_handle}\n"
            f"Duration: {media.duration_seconds}s\n"
            f"Transcript language: {transcript.language} (ASR confidence ≈ {asr_hint})\n"
            f"Reader locale: {locale}\n\n"
            f"Transcript with segment start times:\n" + "\n".join(lines)[:60_000]
        )
        response = await self._client.messages.parse(
            model=self._settings.anthropic_model,
            max_tokens=16000,
            thinking={"type": "adaptive"},
            system=_SYNTH_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_message}],
            output_format=_SynthesisedNote,
        )
        parsed = response.parsed_output
        if parsed is None:
            raise ValueError(f"no parsed output (stop_reason={response.stop_reason})")
        return parsed
