"""Runtime configuration, overridable via CLIPNOTES_* environment variables."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="CLIPNOTES_")

    # Signing key for device tokens. The default exists so the dev server and
    # tests run without setup; deployments must set CLIPNOTES_SECRET_KEY.
    secret_key: str = "dev-secret-do-not-use-in-production"
    token_ttl_days: int = 180

    worker_concurrency: int = 2
    # Simulated latency per pipeline stage so the status flow is visible when
    # driving the stub backend by hand. Tests set this to 0. Ignored by the
    # real pipeline, whose stages take real time.
    stage_delay_seconds: float = 0.2

    # "real" = yt-dlp + Whisper pipeline, "stub" = deterministic placeholders,
    # "auto" = real (falls back to stub only if the real deps aren't installed).
    pipeline_mode: str = "auto"

    # Local Whisper (faster-whisper). Model downloads from Hugging Face on
    # first use. "base" is fast on CPU; "small"/"large-v3" are more accurate.
    whisper_model: str = "base"
    whisper_compute_type: str = "int8"

    # Note synthesis: "claude" = Claude API (needs ANTHROPIC_API_KEY on the
    # backend — the key never reaches the phone), "heuristic" = keyless
    # extractive notes, "auto" = claude when a key env var is present.
    synthesis_mode: str = "auto"
    anthropic_model: str = "claude-opus-4-8"

    max_duration_seconds: int = 300
    dedup_window_hours: int = 24

    rate_limit_per_hour: int = 30
    rate_limit_per_day: int = 200

    # Comma-separated allowed origins for browser clients (the native app
    # doesn't need CORS). Empty string disables the middleware.
    cors_allow_origins: str = "*"
