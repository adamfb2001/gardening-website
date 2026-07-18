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
| `mobile/` | Expo (React Native) app, testable on a real iPhone via **Expo Go** — see [mobile/README.md](mobile/README.md) for phone setup |

> **Stack note:** the original plan specified SwiftUI/SwiftData. The app is
> built with Expo/React Native instead so it can be tested on-device through
> Expo Go with no Mac, Xcode, or Apple developer account. The share
> extension (M4) will need an Expo development build rather than Expo Go.

## Milestones

- [x] **M1 — Backend skeleton.** Full API contract (jobs, device auth, rate
  limits, typed errors), async worker pool, stub pipeline, Dockerfile,
  contract tests.
- [ ] **M2 — YouTube Shorts end to end.** Real resolver + Whisper +
  synthesiser for YouTube only.
- [x] **M3 — app shell.** Library, Note detail, Search, manual URL paste,
  processing tray, favourites, offline store — delivered as an Expo app that
  runs in Expo Go against the real backend.
- [ ] **M4 — Share Extension.** Share-sheet ingest, background submission,
  notifications (requires an Expo dev build; a Shortcuts-based stand-in is
  documented in mobile/README.md).
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
