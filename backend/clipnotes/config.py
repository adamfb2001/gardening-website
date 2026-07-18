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
    # driving the stub backend by hand. Tests set this to 0.
    stage_delay_seconds: float = 0.2

    max_duration_seconds: int = 300
    dedup_window_hours: int = 24

    rate_limit_per_hour: int = 30
    rate_limit_per_day: int = 200
