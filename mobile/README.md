# ClipNotes mobile app (Expo)

React Native app built with Expo so it runs in **Expo Go** on a real iPhone
with no Mac, no Xcode, and no Apple developer account. Implements the M3
shell: library, search, note detail, manual link ingest, processing tray with
live status, favourites, and settings — talking to the ClipNotes backend.

> **Pinned to Expo SDK 54 on purpose.** The App Store's Expo Go build (54.x)
> runs exactly one SDK version, and newer SDKs exist on npm before Expo Go
> supports them. If you ever see *"Project is incompatible with this version
> of Expo Go"*, the project and the store app have drifted apart again —
> check the store's Expo Go version number (it tracks the SDK it supports)
> and align the project with
> `npx expo install expo@^<that version> && npx expo install --fix`.

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

### If you updated the repo and the app won't load

Dependency versions change with the pinned SDK — after `git pull`, refresh
the install and clear Metro's cache:

```bash
cd mobile
rm -rf node_modules
npm install
npx expo start -c
```

### If the QR connection fails

Some networks block phone↔laptop traffic (client isolation). Fall back to:

```bash
npx expo start --tunnel
```

The JS then arrives via Expo's tunnel, but the tunnel does **not** carry the
backend — set the backend URL by hand in the app's Settings (your machine's
LAN IP, e.g. `http://192.168.1.23:8000`, or a public tunnel to port 8000
such as `cloudflared`/`ngrok`).

### Getting a "Save to ClipNotes" entry in the iOS share sheet (Shortcuts)

Expo Go has no share extension of its own, so it can't appear in the share
sheet's app row. A native ClipNotes target there requires a signed dev build
(see below). As a **works-today stand-in**, an iOS **Shortcut** puts a
"Save to ClipNotes" item in the share sheet that forwards the shared link to
ClipNotes running in Expo Go. The receiving deep link (`/ingest?url=…`) is
verified end-to-end.

Setup (once, on the iPhone):

1. Run `npx expo start` and note the `exp://<IP>:8081` URL it prints — that
   `<IP>` is your computer's LAN address.
2. **Shortcuts** app → **+** → the **ⓘ** (details) → turn on **Show in Share
   Sheet**, and set **Share Sheet Types** to **URLs** only.
3. Name it **Save to ClipNotes**.
4. Add these actions in order:
   - **URL Encode** — Input: **Shortcut Input**
   - **Text** — value: `exp://<IP>:8081/--/ingest?url=` immediately followed by
     the **Encoded Text** variable from the previous step
   - **Open URLs** — Input: the **Text** from the previous step
5. Save.

Now: in YouTube (or any app), share a video → **Save to ClipNotes**. Expo Go
opens, the link is submitted, and you land in the library with it processing.

Caveats: works only while `npx expo start` is running on the same Wi-Fi;
update `<IP>` in the Text action when your network changes. It appears in the
share sheet's **actions** list as a Shortcut, not as a native app icon in the
top app row — that native placement is the dev-build path below.

## What Expo Go can't do (yet)

These need a development build (`expo run:ios` / EAS) rather than Expo Go, and
are deliberately deferred:

- Real share-sheet extension — a native ClipNotes target in the share-sheet
  app row (next to WhatsApp) is a separate signed app extension; it needs a
  dev build (EAS or `expo run:ios`) + Apple signing. The Shortcut above is the
  Expo-Go-compatible stand-in.
- Local notifications on job completion.
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
