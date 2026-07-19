# ClipNotes mobile app (Expo)

React Native app built with Expo so it runs in **Expo Go** on a real iPhone
with no Mac, no Xcode, and no Apple developer account. Implements the M3
shell: library, search, note detail, manual link ingest, processing tray with
live status, favourites, and settings — talking to the ClipNotes backend.

## Test it on your iPhone

**Prerequisites:** [Expo Go](https://apps.apple.com/app/expo-go/id982107779)
from the App Store, Node 18+, and your iPhone + computer on the **same Wi-Fi
network**.

Terminal 1 — the backend (note `--host 0.0.0.0`, so your phone can reach it):

```bash
cd backend
python3 -m venv .venv && .venv/bin/pip install -e ".[dev]"   # first time only
.venv/bin/uvicorn clipnotes.main:app --host 0.0.0.0 --port 8000
```

Terminal 2 — the app:

```bash
cd mobile
npm install        # first time only
npx expo start
```

Scan the QR code with the iPhone camera → it opens in Expo Go. The app
automatically targets port 8000 **on the same machine that serves it the JS
bundle**, so if the backend runs next to Metro there is zero configuration.
Verify under Settings → "Test connection".

### Things to try

- Open YouTube, find any Short → Share → **Copy link** → in ClipNotes tap
  **Paste link**. Watch it move through fetching → transcribing → analysing →
  writing, then read the note — **real notes from the actual audio**: the
  backend downloads the clip, transcribes it with local Whisper (first job
  downloads the model, so it's slower), and synthesises notes. Set
  `ANTHROPIC_API_KEY` in the backend's environment for distilled AI notes;
  without it you get honest extractive notes. The full transcript is on the
  note's detail screen and is searchable.
- Failure states: paste a link with `stub-unavailable`, `stub-private`,
  `stub-toolong` or `stub-crash` in the path (e.g.
  `https://youtube.com/shorts/stub-private`) — each fails with a specific,
  honest message and a retry where it makes sense. An unsupported site
  (e.g. a Vimeo link) is rejected as unsupported.
- Search, category chips, favourites, duplicate detection (paste the same
  link twice), delete-all in Settings.
- Offline: once notes exist, airplane mode — reading and searching still work.

### If the QR connection fails

Some networks block phone↔laptop traffic (client isolation). Fall back to:

```bash
npx expo start --tunnel
```

The JS then arrives via Expo's tunnel, but the tunnel does **not** carry the
backend — set the backend URL by hand in the app's Settings (your machine's
LAN IP, e.g. `http://192.168.1.23:8000`, or a public tunnel to port 8000
such as `cloudflared`/`ngrok`).

### Optional: share-sheet-ish flow via Shortcuts

Until the native share extension (needs a dev build, M4), you can approximate
it: iOS **Shortcuts** app → new shortcut → accepts URLs from the Share Sheet →
action "URL Encode" on the Shortcut Input → action "Open URL" with
`exp://<your-laptop-LAN-IP>:8081/--/ingest?url=<encoded input>`. Sharing a
video to that shortcut opens Expo Go and saves the link. Works only while
`expo start` is running.

## What Expo Go can't do (yet)

These need a development build (`expo run:ios` / EAS) rather than Expo Go, and
are deliberately deferred:

- Real share-sheet extension (M4) — the Shortcuts trick above stands in.
- Local notifications on job completion (M4).
- Keychain-grade token storage — the device token currently lives in
  AsyncStorage, fine for development.

## Development

```bash
npx tsc --noEmit     # typecheck
npx expo export      # verify the bundle compiles
npm run lint
```

Structure: `src/app/` (expo-router screens: library, `note/[id]`, settings,
`ingest` deep link) · `src/lib/` (backend client, offline store/polling,
config) · `src/components/` (cards, chips, themed primitives).
