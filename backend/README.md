# ClipNotes backend

FastAPI service that turns short-form video URLs into structured, searchable
notes. The pipeline is **real by default**:

1. **Resolve** — yt-dlp fetches the video's metadata (title, creator,
   duration, thumbnail) for YouTube Shorts, TikTok, Instagram Reels, and
   Facebook Reels (non-YouTube platforms are best-effort and fail with
   honest, typed errors when the platform blocks access).
2. **Transcribe** — the audio track is downloaded to a temp dir and
   transcribed with **local Whisper** (faster-whisper; no API key needed; the
   model auto-downloads on first use). The media file is deleted the moment
   transcription ends — only text is kept.
3. **Synthesise** — with `ANTHROPIC_API_KEY` set on the backend, Claude turns
   the transcript into distilled notes (key points, steps, quotes, category,
   honest caveats), schema-validated. Without a key, a heuristic synthesiser
   produces extractive notes that say plainly they were built without AI.

The vision path (on-screen text/frames) is not built yet — every note carries
`confidence.visual = 0` and a caveat saying so.

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

With `CLIPNOTES_PIPELINE_MODE=stub` the deterministic placeholder pipeline
runs instead (used by the test suite; handy for offline UI work). URL
substrings then drive every path:

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
| `PIPELINE_MODE` | `auto` | `real` (yt-dlp + Whisper), `stub`, or `auto` (real, degrading to stub only if deps are missing) |
| `WHISPER_MODEL` | `base` | faster-whisper model: `tiny`/`base`/`small`/`large-v3` — bigger = better + slower |
| `SYNTHESIS_MODE` | `auto` | `claude` / `heuristic` / `auto` (Claude when an Anthropic credential env var is present) |
| `ANTHROPIC_MODEL` | `claude-opus-4-8` | Model used for note synthesis |
| `TOKEN_TTL_DAYS` | 180 | |
| `WORKER_CONCURRENCY` | 2 | Transcriptions are serialised regardless (CPU-bound) |
| `STAGE_DELAY_SECONDS` | 0.2 | Simulated per-stage latency of the **stub** pipeline; 0 in tests |
| `MAX_DURATION_SECONDS` | 300 | Duration cap |
| `DEDUP_WINDOW_HOURS` | 24 | |
| `RATE_LIMIT_PER_HOUR` / `RATE_LIMIT_PER_DAY` | 30 / 200 | |

`ANTHROPIC_API_KEY` (unprefixed — it's the SDK's own variable) enables Claude
synthesis. The key lives only on the backend; the app never sees it.

> **Hosting note:** video platforms bot-block many datacenter/VPN IPs (media
> downloads 403 even though metadata works). Running the backend on a home
> network avoids this; failures surface as an honest, retryable
> `media_unavailable` error.

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

| Module | Responsibility |
|---|---|
| `clipnotes/main.py` | App factory; singletons on `app.state` |
| `clipnotes/routes/` | HTTP endpoints |
| `clipnotes/auth.py` | Device registration, JWT verify |
| `clipnotes/ratelimit.py` | Sliding-window per-device limits (in-memory) |
| `clipnotes/store.py` | Job persistence (in-memory; jobs are transient — notes live on-device) |
| `clipnotes/worker.py` | Async worker pool, job lifecycle, duration cap |
| `clipnotes/urls.py` | URL canonicalisation + platform detection |
| `clipnotes/pipeline/base.py` | Stage interfaces (Resolver/Transcriber/Vision/Synthesiser) |
| `clipnotes/pipeline/real.py` | yt-dlp resolver + downloader, local Whisper transcription |
| `clipnotes/pipeline/synth.py` | Claude synthesis (schema-validated) + keyless heuristic fallback |
| `clipnotes/pipeline/stub.py` | Deterministic placeholders (tests, offline UI work) |

Design notes: media files are never persisted — deleted within the job's
lifetime, only transcript + metadata retained; every note is honest about
uncertainty (ASR confidence, missing vision path, heuristic-vs-AI synthesis);
failures are typed and user-facing, never silent.
