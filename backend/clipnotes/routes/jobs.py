"""Job endpoints (spec §6)."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from math import ceil
from typing import Annotated, Optional
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status

from ..auth import require_device
from ..models import (
    ErrorCode,
    Job,
    JobCreateRequest,
    JobCreateResponse,
    JobListResponse,
    JobStatus,
    JobView,
)
from ..urls import normalize_url

router = APIRouter(prefix="/v1/jobs", tags=["jobs"])

DeviceId = Annotated[str, Depends(require_device)]


@router.post("", status_code=status.HTTP_201_CREATED, response_model=JobCreateResponse)
async def create_job(
    payload: JobCreateRequest,
    device_id: DeviceId,
    request: Request,
    response: Response,
) -> JobCreateResponse:
    state = request.app.state

    # Idempotent replay: the share extension may fire the same client_id twice
    # (fast enqueue + background submission). Return the existing job, don't
    # charge the rate limit.
    existing = await state.store.find_by_client_id(device_id, payload.client_id)
    if existing is not None:
        response.status_code = status.HTTP_200_OK
        return JobCreateResponse(
            job_id=existing.job_id, status=existing.status, dedup_of=existing.dedup_of
        )

    retry_after = state.limiter.try_acquire(device_id)
    if retry_after is not None:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail={
                "code": ErrorCode.rate_limited.value,
                "message": "Too many videos submitted. Please try again later.",
                "retryable": True,
            },
            headers={"Retry-After": str(ceil(retry_after))},
        )

    normalized = normalize_url(payload.url)
    duplicate = await state.store.find_dedup(
        device_id, normalized, timedelta(hours=state.settings.dedup_window_hours)
    )

    now = datetime.now(timezone.utc)
    job = Job(
        job_id=uuid4().hex,
        device_id=device_id,
        client_id=payload.client_id,
        url=payload.url,
        normalized_url=normalized,
        locale=payload.locale,
        dedup_of=duplicate.job_id if duplicate else None,
        created_at=now,
        updated_at=now,
    )
    await state.store.create(job)
    await state.worker_pool.submit(job.job_id)
    return JobCreateResponse(job_id=job.job_id, status=job.status, dedup_of=job.dedup_of)


@router.get("", response_model=JobListResponse)
async def list_jobs(
    device_id: DeviceId,
    request: Request,
    since: Annotated[Optional[str], Query(description="ISO 8601 timestamp")] = None,
) -> JobListResponse:
    parsed_since: Optional[datetime] = None
    if since is not None:
        try:
            parsed_since = datetime.fromisoformat(since)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail={"code": "invalid_since", "message": "since must be an ISO 8601 timestamp"},
            )
        if parsed_since.tzinfo is None:
            parsed_since = parsed_since.replace(tzinfo=timezone.utc)
    jobs = await request.app.state.store.list_for_device(device_id, parsed_since)
    return JobListResponse(jobs=[JobView.from_job(job) for job in jobs])


@router.get("/{job_id}", response_model=JobView)
async def get_job(job_id: str, device_id: DeviceId, request: Request) -> JobView:
    job = await _job_or_404(request, job_id, device_id)
    return JobView.from_job(job)


@router.post("/{job_id}/retry", response_model=JobView)
async def retry_job(job_id: str, device_id: DeviceId, request: Request) -> JobView:
    state = request.app.state
    job = await _job_or_404(request, job_id, device_id)
    if job.status is not JobStatus.failed:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"code": "not_retryable", "message": "Only failed jobs can be retried."},
        )
    updated = await state.store.update(
        job_id, status=JobStatus.queued, progress=0.0, error=None, note=None
    )
    if updated is None:
        raise _not_found()
    await state.worker_pool.submit(job_id)
    return JobView.from_job(updated)


@router.delete("/{job_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_job(job_id: str, device_id: DeviceId, request: Request) -> None:
    await _job_or_404(request, job_id, device_id)
    # Removing the record is also the cancellation signal: in-flight workers
    # notice the job is gone at the next stage boundary and stop.
    await request.app.state.store.delete(job_id)


async def _job_or_404(request: Request, job_id: str, device_id: str) -> Job:
    job = await request.app.state.store.get_for_device(job_id, device_id)
    if job is None:
        raise _not_found()
    return job


def _not_found() -> HTTPException:
    # Same 404 whether the job never existed or belongs to another device, so
    # job IDs can't be probed across devices.
    return HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail={"code": "not_found", "message": "No such job."},
    )
