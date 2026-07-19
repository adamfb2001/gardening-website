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
required or pkill matches your own shell's command line and kills it. The
kill must also run in its OWN Bash call: a compound command that both pkills
and (re)launches contains the literal launch string, which the pattern
matches, killing the shell (exit 144).

Pipeline modes: `CLIPNOTES_PIPELINE_MODE=stub` for fast deterministic runs
(what the tests and UI drives use); `real` for yt-dlp + Whisper. In this
datacenter container, YouTube/TikTok metadata resolution works but media
CDNs return 403 (bot-blocking of the egress IP) — verify the
transcription+synthesis half by patching `WhisperTranscriber._download_audio`
to copy a local audio file (a spoken-Wikipedia .ogg from Wikimedia Commons
downloads fine) and calling `transcriber.transcribe(media)`; whisper "base"
model (~75 MB) downloads from Hugging Face on first use.

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

## Mobile app (mobile/, Expo)

No phone in this environment — drive the web build in the bundled Chromium
instead (same JS, same store/API logic as Expo Go):

```bash
cd mobile
npx tsc --noEmit                                   # typecheck
CI=1 npx expo export --platform web --output-dir /tmp/export-web
(cd /tmp/export-web && python3 -m http.server 8081 &)   # serve static build
# backend must be running on :8000 (CORS is enabled by default)
```

Then Playwright (`npm i playwright` in scratchpad; launch with
`executablePath: '/opt/pw-browsers/chromium'`, viewport 390×844) against
http://localhost:8081. Gotchas: navigate to /settings via the in-app link
(the static server doesn't rewrite paths); `getByText` needs
`{ exact: true }` for PROCESSING/Failed (substring collisions); inputs carry
`data-testid` `url-input`, `search-input`, `baseurl-input`. Also run
`CI=1 npx expo export --platform ios` to confirm the native bundle compiles.

## Worth checking after changes

- Enqueue latency (must stay milliseconds — the share sheet depends on it).
- Status progression shows *every* stage: resolving → transcribing →
  analysing → synthesising → complete.
- Failed jobs carry `error.{code,message,retryable}`; notes carry honest
  caveats.
- Cross-device access to a job returns 404, not 403.
