# ClipNotes backend

FastAPI service that turns short-form video URLs into structured, searchable
notes. **Current state: M1** — the full API contract, device auth, job queue,
and worker pool are real; the media pipeline (resolver → Whisper → vision →
synthesis) is stubbed and produces clearly-labelled placeholder notes. M2
replaces the stubs for YouTube Shorts.

## Quickstart

```bash
cd backend
python3 -m venv .venv
.venv/bin/pip install -e ".[dev]"
.venv/bin/uvicorn clipnotes.main:app --port 8000
```

Walk the whole flow with curl:

```bash
# 1. Register an anonymous device → signed token (no sign-up wall in v1)
TOKEN=$(curl -s -X POST localhost:8000/v1/devices | python3 -c "import sys,json; print(json.load(sys.stdin)['token'])")

# 2. Enqueue a video (returns in milliseconds — the share sheet depends on it)
curl -s -X POST localhost:8000/v1/jobs \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"client_id":"11111111-1111-1111-1111-111111111111","url":"https://www.youtube.com/shorts/dQw4w9WgXcQ","locale":"en-GB"}'

# 3. Poll — watch it move queued → resolving → transcribing → analysing →
#    synthesising → complete, then read the note
curl -s localhost:8000/v1/jobs/<job_id> -H "Authorization: Bearer $TOKEN"
```

Interactive OpenAPI docs at `http://localhost:8000/docs`.

## API

| Endpoint | Purpose |
|---|---|
| `POST /v1/devices` | Anonymous device registration → `{device_id, token, expires_at}` |
| `POST /v1/jobs` | Enqueue a URL. `201 {job_id, status, dedup_of}`. Replaying a `client_id` returns the existing job (`200`), so share-extension retries are safe. `dedup_of` points at a prior job for the same canonical URL within 24 h. |
| `GET /v1/jobs/{id}` | `{job_id, status, progress, note, error, url, created_at, updated_at}` |
| `GET /v1/jobs?since=<iso8601>` | Batch poll on app foreground |
| `POST /v1/jobs/{id}/retry` | Re-enqueue a **failed** job (409 otherwise) |
| `DELETE /v1/jobs/{id}` | Remove a job; cancels it if still in flight |
| `GET /healthz` | Liveness |

All `/v1/jobs*` endpoints require `Authorization: Bearer <device token>`.
Failures are typed (`error.code`): `unsupported_platform`,
`media_unavailable`, `private_or_geoblocked`, `media_too_long`,
`no_extractable_content`, `rate_limited`, `internal_error` — each with a
human-readable `message` and a `retryable` flag. Rate limit: 30 jobs/hour,
200/day per device (`429` + `Retry-After`).

## Stub pipeline markers

Until M2 lands, URL substrings drive every path for client development and
tests (any supported-platform URL works around them):

| Marker in URL | Result |
|---|---|
| *(none)* | `complete`, placeholder note labelled as a stub |
| `stub-unavailable` | `failed` / `media_unavailable` (retryable) |
| `stub-private` | `failed` / `private_or_geoblocked` |
| `stub-nocontent` | `failed` / `no_extractable_content` |
| `stub-toolong` | resolves at 900 s → `failed` / `media_too_long` |
| `stub-nospeech` | `complete`, visuals-only note, `confidence.audio = 0` |
| `stub-crash` | `failed` / `internal_error` (retryable) |

Unsupported hosts (anything that isn't YouTube/TikTok/Instagram/Facebook)
fail with `unsupported_platform` — no marker needed.

## Configuration

Environment variables, all prefixed `CLIPNOTES_`:

| Variable | Default | Notes |
|---|---|---|
| `SECRET_KEY` | dev value | **Must** be set in deployments; signs device tokens |
| `TOKEN_TTL_DAYS` | 180 | |
| `WORKER_CONCURRENCY` | 2 | |
| `STAGE_DELAY_SECONDS` | 0.2 | Simulated per-stage latency of the stub pipeline; 0 in tests |
| `MAX_DURATION_SECONDS` | 300 | Duration cap (spec §4.1) |
| `DEDUP_WINDOW_HOURS` | 24 | |
| `RATE_LIMIT_PER_HOUR` / `RATE_LIMIT_PER_DAY` | 30 / 200 | |

## Tests

```bash
.venv/bin/python -m pytest
```

Contract tests drive the app over ASGI: endpoint shapes, note-schema
validity, typed failures, idempotency/dedup, auth, rate limiting, URL
canonicalisation.

## Docker

```bash
docker build -t clipnotes-backend backend/
docker run -p 8000:8000 -e CLIPNOTES_SECRET_KEY=<random-32B+> clipnotes-backend
```

## Layout

| Module | Responsibility | M1 status |
|---|---|---|
| `clipnotes/main.py` | App factory; singletons on `app.state` | real |
| `clipnotes/routes/` | HTTP endpoints | real |
| `clipnotes/auth.py` | Device registration, JWT verify | real |
| `clipnotes/ratelimit.py` | Sliding-window per-device limits | real (in-memory) |
| `clipnotes/store.py` | Job persistence | real logic, in-memory (jobs are transient; notes live on-device) |
| `clipnotes/worker.py` | Async worker pool, job lifecycle, duration cap | real |
| `clipnotes/urls.py` | URL canonicalisation + platform detection | real |
| `clipnotes/pipeline/base.py` | Stage interfaces (Resolver/Transcriber/Vision/Synthesiser) | real seams |
| `clipnotes/pipeline/stub.py` | Placeholder implementations | **stub — replaced from M2** |

Design notes: media is never persisted (only derived notes — spec §7);
stub notes are explicit about being placeholders (never-fabricate rule);
resolvers are pluggable per platform so one can be disabled by config
without touching the pipeline.
