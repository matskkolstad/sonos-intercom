# CLAUDE.md — Sonos Intercom

Context for working on this repo with Claude Code. Read this first.

## What this is

A custom Home Assistant integration (`sonos_intercom`), distributed via HACS, that
turns Sonos speakers into an intercom: announce **text-to-speech** or a
**microphone recording** (captured in the browser) on selected speakers, with
volume, ducking ("announce"), and optional **chimes** before the message.

The user (Mats) runs Home Assistant + HACS with **Sonos S2** speakers only.
UI-facing text in the card is in **Norwegian**. Communicate with the user in
Norwegian.

Full design doc: `docs/Sonos-Intercom-Spec.md`.

## Architecture (3 layers)

1. **Frontend** — `custom_components/sonos_intercom/www/sonos-intercom-card.js`
   (vanilla custom element). Records audio via `MediaRecorder` (browser, needs
   HTTPS), or sends TTS text. Calls the `sonos_intercom.announce` service.
2. **Backend** — Python integration. HTTP endpoint receives a base64 recording,
   converts to MP3 with ffmpeg, serves it; `announce` service plays media.
3. **Playback** — uses HA's built-in Sonos integration (`media_player.play_media`
   with `announce: true`). Sonos fetches the audio file from HA over the LAN.

## Repo layout

```
custom_components/sonos_intercom/
  __init__.py       # setup, service registration, static + Lovelace-resource registration
  announce.py       # core play logic + chime combine (ffmpeg)
  http.py           # /api/sonos_intercom/upload  (recording -> ffmpeg -> mp3)
  config_flow.py    # options: default_volume, default_tts_engine, storage_dir
  const.py          # DOMAIN, CHIMES, CARD_VERSION, etc.
  services.yaml     # UI schema for the announce service
  www/sonos-intercom-card.js
  www/chimes/*.mp3  # 5 bundled chimes (airport, ding_dong, soft_ping, marimba, gong)
  translations/ (en, nb)
docs/Sonos-Intercom-Spec.md
hacs.json
```

## Key decisions (don't undo without reason)

- **Playback:** rely on HA's native Sonos `announce: true` (ducks + auto-restores).
  No dependency on Chime TTS.
- **announce=True** path: native overlay, just sets announce volume via `extra`.
  **announce=False** path: `sonos.snapshot` -> optional group (`media_player.join`)
  -> play -> wait -> `media_player.unjoin` + `sonos.restore`.
- **Multi-speaker sync:** temporarily group speakers (coordinator + members) so they
  play in sync. This is the area most needing real-hardware testing.
- **Recordings:** MP3 only (FLAC has known issues with announce). Stored under
  `config/www/sonos_intercom/` so Sonos can fetch via `/local/...`.
- **Chimes:** bundled MP3s. When a chime + message is sent, they are concatenated
  into one MP3 with ffmpeg (TTS bytes fetched via `tts.async_get_media_source_audio`;
  recordings mapped from their `/local/` URL back to a filesystem path). A chime can
  also be played alone (served from the static path).
- **Card loading:** registered as a **Lovelace resource** (deterministic load) with a
  `?v={CARD_VERSION}` cache-buster, with fallback to `add_extra_js_url` for YAML mode.

## CRITICAL dev gotcha

**Whenever you change `www/sonos-intercom-card.js`, bump `CARD_VERSION` in `const.py`**
(and the console banner string + `manifest.json` version). Otherwise the browser /
HA service worker serves a stale cached card and changes won't appear. This caused
real debugging pain early on.

## Dev / test workflow

- The user pushes to GitHub themselves (`git push origin main`) — earlier the
  sandbox couldn't push. Local git identity is already set.
- To test: user updates the integration in HACS, restarts HA, then hard-refreshes
  the browser (Ctrl+Shift+R). The version bump handles cache.
- Validate before committing:
  - `python3 -m py_compile custom_components/sonos_intercom/*.py`
  - `node --check custom_components/sonos_intercom/www/sonos-intercom-card.js`
  - JSON/YAML: `python3 -c "import json;json.load(open('...'))"` / `import yaml`
  - Clean up `__pycache__` afterwards (it's gitignored).

## Requirements / constraints

- Sonos **S2** only. HA **2024.6+**.
- Microphone needs **HTTPS** in the browser; TTS works regardless.
- A TTS engine id must be set (options `default_tts_engine`, e.g. `tts.home_assistant_cloud`).
- Sonos network: TCP 1443 + 1400 reachable from HA.

## Status

Current version: **0.2.2**. Working: TTS, browser recording over HTTPS, 5 chimes
(preview in browser, play alone on speakers, combine before message), stable card
loading. Confirmed working on the user's setup.

## Roadmap (next ideas)

- v2: predefined quick messages (buttons), zones/speaker groups, replay, message
  history, chime volume independent of message.
- v3: two-way intercom, generic `media_player` support beyond Sonos.
