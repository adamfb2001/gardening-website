"""Domain and API models.

The `Note` schema mirrors the synthesiser output contract (spec §4.4) exactly;
the request/response models mirror the API contract (spec §6).
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Optional
from urllib.parse import urlparse
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


class Platform(str, Enum):
    youtube_shorts = "youtube_shorts"
    tiktok = "tiktok"
    instagram_reels = "instagram_reels"
    facebook_reels = "facebook_reels"


class JobStatus(str, Enum):
    queued = "queued"
    resolving = "resolving"
    transcribing = "transcribing"
    analysing = "analysing"
    synthesising = "synthesising"
    complete = "complete"
    failed = "failed"


# Coarse progress reported while a job moves through the pipeline. A failed
# job keeps the progress of the stage it died in.
STAGE_PROGRESS: dict[JobStatus, float] = {
    JobStatus.queued: 0.0,
    JobStatus.resolving: 0.15,
    JobStatus.transcribing: 0.4,
    JobStatus.analysing: 0.65,
    JobStatus.synthesising: 0.85,
    JobStatus.complete: 1.0,
}


class ErrorCode(str, Enum):
    unsupported_platform = "unsupported_platform"
    media_unavailable = "media_unavailable"
    private_or_geoblocked = "private_or_geoblocked"
    media_too_long = "media_too_long"
    no_extractable_content = "no_extractable_content"
    rate_limited = "rate_limited"
    internal_error = "internal_error"


class Category(str, Enum):
    cooking_food = "Cooking & Food"
    fitness_health = "Fitness & Health"
    finance_money = "Finance & Money"
    tech_software = "Tech & Software"
    diy_home = "DIY & Home"
    career_productivity = "Career & Productivity"
    travel = "Travel"
    learning_science = "Learning & Science"
    style_grooming = "Style & Grooming"
    other = "Other"


class Step(BaseModel):
    n: int
    text: str


class Quote(BaseModel):
    text: str
    timestamp_s: float


class Entities(BaseModel):
    people: list[str] = Field(default_factory=list)
    products: list[str] = Field(default_factory=list)
    places: list[str] = Field(default_factory=list)
    tools: list[str] = Field(default_factory=list)
    links_mentioned: list[str] = Field(default_factory=list)


class Confidence(BaseModel):
    audio: float = Field(ge=0.0, le=1.0)
    visual: float = Field(ge=0.0, le=1.0)
    overall: float = Field(ge=0.0, le=1.0)


class Note(BaseModel):
    title: str = Field(max_length=70)
    summary: str
    key_points: list[str] = Field(default_factory=list)
    steps: list[Step] = Field(default_factory=list)
    entities: Entities = Field(default_factory=Entities)
    quotes: list[Quote] = Field(default_factory=list)
    category: Category
    tags: list[str] = Field(default_factory=list)
    confidence: Confidence
    caveats: list[str] = Field(default_factory=list)


class JobError(BaseModel):
    code: ErrorCode
    message: str
    retryable: bool


# ---------------------------------------------------------------------------
# Pipeline intermediates


class ResolvedMedia(BaseModel):
    canonical_url: str
    platform: Platform
    title: str
    creator_handle: str
    duration_seconds: int
    thumbnail_url: Optional[str] = None
    published_at: Optional[datetime] = None


class TranscriptSegment(BaseModel):
    start_s: float
    end_s: float
    text: str


class Transcript(BaseModel):
    language: str
    segments: list[TranscriptSegment]

    @property
    def full_text(self) -> str:
        return " ".join(segment.text for segment in self.segments)


class FrameObservation(BaseModel):
    timestamp_s: float
    text: str


# ---------------------------------------------------------------------------
# Stored job record


class Job(BaseModel):
    job_id: str
    device_id: str
    client_id: UUID
    url: str
    normalized_url: str
    locale: str
    status: JobStatus = JobStatus.queued
    progress: float = 0.0
    note: Optional[Note] = None
    error: Optional[JobError] = None
    dedup_of: Optional[str] = None
    created_at: datetime
    updated_at: datetime


# ---------------------------------------------------------------------------
# API request/response bodies (spec §6)


class JobCreateRequest(BaseModel):
    client_id: UUID
    url: str
    locale: str = "en"

    @field_validator("url")
    @classmethod
    def _must_be_http_url(cls, value: str) -> str:
        parsed = urlparse(value)
        if parsed.scheme not in ("http", "https") or not parsed.netloc:
            raise ValueError("url must be an absolute http(s) URL")
        return value


class JobCreateResponse(BaseModel):
    job_id: str
    status: JobStatus
    dedup_of: Optional[str] = None


class JobView(BaseModel):
    """Contract fields from spec §6, plus url/timestamps the app needs for
    display and for `?since=` polling."""

    job_id: str
    status: JobStatus
    progress: float
    note: Optional[Note] = None
    error: Optional[JobError] = None
    url: str
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_job(cls, job: Job) -> "JobView":
        return cls(
            job_id=job.job_id,
            status=job.status,
            progress=job.progress,
            note=job.note,
            error=job.error,
            url=job.url,
            created_at=job.created_at,
            updated_at=job.updated_at,
        )


class JobListResponse(BaseModel):
    jobs: list[JobView]


class DeviceRegistration(BaseModel):
    device_id: str
    token: str
    expires_at: datetime
