"""FastAPI application factory.

App-wide singletons (settings, store, limiter, worker pool) live on
`app.state`, so tests can build isolated instances via create_app() with
custom Settings.
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncIterator, Optional

from fastapi import FastAPI

from . import __version__
from .config import Settings
from .pipeline import build_stub_pipeline
from .ratelimit import RateLimiter
from .routes import devices, jobs
from .store import JobStore
from .worker import WorkerPool


def create_app(settings: Optional[Settings] = None) -> FastAPI:
    settings = settings or Settings()
    store = JobStore()
    pool = WorkerPool(store=store, settings=settings, pipeline=build_stub_pipeline(settings))

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        pool.start()
        yield
        await pool.stop()

    app = FastAPI(
        title="ClipNotes API",
        version=__version__,
        description="Turns short-form video URLs into structured, searchable notes.",
        lifespan=lifespan,
    )
    app.state.settings = settings
    app.state.store = store
    app.state.limiter = RateLimiter(settings.rate_limit_per_hour, settings.rate_limit_per_day)
    app.state.worker_pool = pool

    app.include_router(devices.router)
    app.include_router(jobs.router)

    @app.get("/healthz", tags=["ops"])
    async def healthz() -> dict[str, str]:
        return {"status": "ok", "version": __version__}

    return app


app = create_app()
