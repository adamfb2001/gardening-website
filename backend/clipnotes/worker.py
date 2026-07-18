"""Async worker pool: drives jobs through the pipeline lifecycle
queued → resolving → transcribing → analysing → synthesising → complete,
or → failed with a typed reason (spec §3).
"""

from __future__ import annotations

import asyncio
import logging

from .config import Settings
from .models import STAGE_PROGRESS, ErrorCode, Job, JobError, JobStatus
from .pipeline import Pipeline, PipelineError
from .store import JobStore

log = logging.getLogger(__name__)


class WorkerPool:
    def __init__(self, store: JobStore, settings: Settings, pipeline: Pipeline) -> None:
        self._store = store
        self._settings = settings
        self._pipeline = pipeline
        self._queue: asyncio.Queue[str] = asyncio.Queue()
        self._tasks: list[asyncio.Task[None]] = []

    def start(self) -> None:
        for index in range(self._settings.worker_concurrency):
            self._tasks.append(asyncio.create_task(self._worker(), name=f"clipnotes-worker-{index}"))

    async def stop(self) -> None:
        for task in self._tasks:
            task.cancel()
        await asyncio.gather(*self._tasks, return_exceptions=True)
        self._tasks.clear()

    async def submit(self, job_id: str) -> None:
        await self._queue.put(job_id)

    async def _worker(self) -> None:
        while True:
            job_id = await self._queue.get()
            try:
                await self._process(job_id)
            except asyncio.CancelledError:
                raise
            except PipelineError as exc:
                await self._fail(job_id, JobError(code=exc.code, message=exc.message, retryable=exc.retryable))
            except Exception:
                log.exception("job %s: unhandled pipeline error", job_id)
                await self._fail(
                    job_id,
                    JobError(
                        code=ErrorCode.internal_error,
                        message="Something went wrong while processing this video. Please try again.",
                        retryable=True,
                    ),
                )
            finally:
                self._queue.task_done()

    async def _process(self, job_id: str) -> None:
        job = await self._store.get(job_id)
        if job is None or job.status is not JobStatus.queued:
            return  # deleted before we got to it, or a stale re-enqueue

        # Each _advance() call returns None if the job was deleted mid-flight,
        # which cancels the remaining stages.
        job = await self._advance(job_id, JobStatus.resolving)
        if job is None:
            return
        media = await self._pipeline.resolver.resolve(job.url)
        if media.duration_seconds > self._settings.max_duration_seconds:
            raise PipelineError(
                ErrorCode.media_too_long,
                f"This video is {media.duration_seconds}s long; the limit is {self._settings.max_duration_seconds}s.",
                retryable=False,
            )

        if await self._advance(job_id, JobStatus.transcribing) is None:
            return
        transcript = await self._pipeline.transcriber.transcribe(media)

        if await self._advance(job_id, JobStatus.analysing) is None:
            return
        observations = await self._pipeline.vision.analyse(media)

        if await self._advance(job_id, JobStatus.synthesising) is None:
            return
        note = await self._pipeline.synthesiser.synthesise(media, transcript, observations, job.locale)

        await self._store.update(job_id, status=JobStatus.complete, progress=1.0, note=note)

    async def _advance(self, job_id: str, stage: JobStatus) -> Job | None:
        job = await self._store.update(job_id, status=stage, progress=STAGE_PROGRESS[stage])
        # Sleep after the update so each stage is observable to pollers for
        # the full simulated duration (the real pipeline's stage work sits
        # here from M2 on).
        if job is not None and self._settings.stage_delay_seconds:
            await asyncio.sleep(self._settings.stage_delay_seconds)
        return job

    async def _fail(self, job_id: str, error: JobError) -> None:
        await self._store.update(job_id, status=JobStatus.failed, error=error)
