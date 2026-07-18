---
name: verify
description: Build, launch, and drive the ClipNotes backend to verify changes end-to-end
---

# Verifying the ClipNotes backend

## Build + launch

```bash
cd backend
python3 -m venv .venv && .venv/bin/pip install -e ".[dev]"   # once
(CLIPNOTES_SECRET_KEY="verify-secret-0123456789abcdef-0123456789" \
  nohup .venv/bin/uvicorn clipnotes.main:app --port 8123 > /tmp/uvicorn.log 2>&1 &)
sleep 1.5 && curl -s http://127.0.0.1:8123/healthz   # {"status":"ok",...}
```

Stop it with `pkill -f "uvicorn[ ]clipnotes"` — the `[ ]` bracket trick is
required or pkill matches your own shell's command line and kills it.

## Drive the surface

Flow: `POST /v1/devices` → Bearer token → `POST /v1/jobs` with
`{client_id: <uuid>, url, locale}` → poll `GET /v1/jobs/{id}` until
`complete`/`failed`. Default stub stage delay is 0.2 s/stage, so a job
finishes in ~1 s; poll every ~50 ms to see each status.

Use the venv's Python with `httpx` for scripting (installed as a dev dep);
plain curl works too. Gotcha: pass `since` timestamps via proper query
encoding (`params=` in httpx) — a raw `+00:00` in the URL arrives as a space
and 422s.

Stub URL markers (see backend/README.md) drive every failure path:
`stub-unavailable`, `stub-private`, `stub-nocontent`, `stub-toolong`,
`stub-nospeech`, `stub-crash`; unsupported hosts (e.g. vimeo.com) fail with
`unsupported_platform`.

## Worth checking after changes

- Enqueue latency (must stay milliseconds — the share sheet depends on it).
- Status progression shows *every* stage: resolving → transcribing →
  analysing → synthesising → complete.
- Failed jobs carry `error.{code,message,retryable}`; notes carry honest
  caveats.
- Cross-device access to a job returns 404, not 403.
