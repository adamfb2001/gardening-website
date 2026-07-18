"""Job persistence.

In-memory for M1 (jobs are transient work items; the durable source of truth
for notes is the device's SwiftData store). The interface is kept narrow so a
database-backed implementation can replace it without touching routes or
workers.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Optional
from uuid import UUID

import asyncio

from .models import Job, JobStatus


class JobStore:
    def __init__(self) -> None:
        self._jobs: dict[str, Job] = {}
        self._by_client: dict[tuple[str, UUID], str] = {}
        self._lock = asyncio.Lock()

    async def create(self, job: Job) -> Job:
        async with self._lock:
            self._jobs[job.job_id] = job.model_copy(deep=True)
            self._by_client[(job.device_id, job.client_id)] = job.job_id
            return job.model_copy(deep=True)

    async def get(self, job_id: str) -> Optional[Job]:
        async with self._lock:
            job = self._jobs.get(job_id)
            return job.model_copy(deep=True) if job else None

    async def get_for_device(self, job_id: str, device_id: str) -> Optional[Job]:
        job = await self.get(job_id)
        if job is None or job.device_id != device_id:
            return None
        return job

    async def find_by_client_id(self, device_id: str, client_id: UUID) -> Optional[Job]:
        """Look up a prior submission with the same client-generated UUID, so
        share-extension retries are idempotent."""
        async with self._lock:
            job_id = self._by_client.get((device_id, client_id))
            if job_id is None:
                return None
            job = self._jobs.get(job_id)
            if job is None:  # job was deleted; allow the client_id to be reused
                del self._by_client[(device_id, client_id)]
                return None
            return job.model_copy(deep=True)

    async def find_dedup(
        self, device_id: str, normalized_url: str, window: timedelta
    ) -> Optional[Job]:
        """Most recent non-failed job for the same device and canonical URL
        within the dedup window (spec §4.1: re-shares are cheap)."""
        cutoff = datetime.now(timezone.utc) - window
        async with self._lock:
            candidates = [
                job
                for job in self._jobs.values()
                if job.device_id == device_id
                and job.normalized_url == normalized_url
                and job.status != JobStatus.failed
                and job.created_at >= cutoff
            ]
            if not candidates:
                return None
            newest = max(candidates, key=lambda job: job.created_at)
            return newest.model_copy(deep=True)

    async def list_for_device(
        self, device_id: str, since: Optional[datetime] = None
    ) -> list[Job]:
        async with self._lock:
            jobs = [
                job.model_copy(deep=True)
                for job in self._jobs.values()
                if job.device_id == device_id
                and (since is None or job.updated_at > since)
            ]
        jobs.sort(key=lambda job: job.updated_at, reverse=True)
        return jobs

    async def update(self, job_id: str, **fields: object) -> Optional[Job]:
        """Apply field updates and bump updated_at.

        Returns the updated job, or None if the job no longer exists (it was
        deleted mid-flight) — workers treat None as a cancellation signal.
        """
        async with self._lock:
            job = self._jobs.get(job_id)
            if job is None:
                return None
            updated = job.model_copy(update={**fields, "updated_at": datetime.now(timezone.utc)})
            self._jobs[job_id] = updated
            return updated.model_copy(deep=True)

    async def delete(self, job_id: str) -> bool:
        async with self._lock:
            return self._jobs.pop(job_id, None) is not None
