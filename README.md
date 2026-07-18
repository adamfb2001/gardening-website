# ClipNotes

Turns short-form videos (YouTube Shorts, TikTok, Instagram Reels, Facebook
Reels) into a personal, searchable knowledge library. Share a video to
ClipNotes from the platform's share sheet; a backend pipeline transcribes the
audio, reads the visuals, and distils structured notes you can browse, search,
and organise offline. A reference library, not a feed — no social features.

## Repository layout

| Path | Contents |
|---|---|
| `backend/` | FastAPI ingest service (Python 3.11, async, containerised) — see [backend/README.md](backend/README.md) |
| `ios/` | SwiftUI app (iOS 17+, SwiftData) — arrives in M3 |

## Milestones

- [x] **M1 — Backend skeleton.** Full API contract (jobs, device auth, rate
  limits, typed errors), async worker pool, stub pipeline, Dockerfile,
  contract tests.
- [ ] **M2 — YouTube Shorts end to end.** Real resolver + Whisper +
  synthesiser for YouTube only.
- [ ] **M3 — iOS app shell.** SwiftData model, Library, Note detail, Search,
  manual URL paste.
- [ ] **M4 — Share Extension.** App Group queue, fast dismiss, background
  submission, notifications.
- [ ] **M5 — Vision path.** Keyframes → VLM observations → merged synthesis.
- [ ] **M6 — Multi-platform.** TikTok / Instagram / Facebook resolvers with
  graceful degradation.
- [ ] **M7 — Organisation & polish.** Collections, editing, export,
  accessibility.
- [ ] **M8 — Hardening.** Retries, caching, cost telemetry, TestFlight.

## Principles baked in

- No API keys in the client; all model calls are server-side.
- Ingest is async; the share sheet dismisses in under ~300 ms.
- Never fabricate: low-confidence or failed analysis is surfaced honestly.
- YouTube Shorts is the reliable path; other platforms degrade gracefully
  with typed, user-facing errors.
- Derived notes only — media files are never persisted; attribution to the
  original creator is always retained.
