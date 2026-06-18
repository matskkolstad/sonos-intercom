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

Current version: **0.3.0**. Working: TTS, browser recording over HTTPS, 5 chimes
(preview in browser, play alone on speakers, combine before message), stable card
loading. 0.3.0 adds: independent **chime volume**, **replay** of the last message,
and automatic **storage cleanup** (`retention_hours`). Up through 0.2.2 confirmed
working on the user's setup; 0.3.0 features need real-hardware confirmation.

## Roadmap (next ideas)

- v2: predefined quick messages (buttons), zones/speaker groups, message history.
  (Replay and independent chime volume landed in 0.3.0.)
- v3: two-way intercom, generic `media_player` support beyond Sonos.

## Service reference (quick)

Service: `sonos_intercom.announce`. Params: `message` OR `audio_url` (or neither,
if only `chime`); `targets` (required, list of media_player entity_ids); `volume`
(0-100 number, or a dict mapping entity_id -> 0-100 for per-speaker); `announce`
(bool, default true); `tts_engine` (overrides default); `sync` (bool, default true);
`chime` (one of: airport, ding_dong, soft_ping, marimba, gong); `chime_volume`
(0-100, loudness of the chime relative to the message; only applies when a chime is
combined with a message/recording — implemented as an ffmpeg `volume` gain on the
chime stream during concat).

Service: `sonos_intercom.replay`. Replays the last announcement (stored in
`hass.data[DOMAIN]["_last"]`: resolved media id/type + targets/volume/announce/sync).
Optional `targets` and `volume` override the stored ones. Pure-TTS replays always
work (regenerated from the media-source id); recording/combined-chime replays depend
on the file still existing (may have been pruned — see storage cleanup).

Storage cleanup: on each `announce`, files under the storage dir whose names start
with `_tts_`, `chime_`, `intercom_`, or `_tmp_` and are older than the
`retention_hours` option (default 24; 0 disables) are deleted.

```yaml
# TTS with a chime in front, chime at 60% of the message volume
action: sonos_intercom.announce
data:
  message: "Middagen er klar"
  chime: airport
  chime_volume: 60
  targets: [media_player.kjokken, media_player.stue]
  volume: 35
  announce: true
```
```yaml
# Chime alone
action: sonos_intercom.announce
data:
  chime: ding_dong
  targets: [media_player.stue]
```
```yaml
# Replay the last announcement
action: sonos_intercom.replay
data:
  targets: [media_player.stue]   # optional; reuses last targets if omitted
```

## Lessons learned (debugging history)

- **Card caching is the #1 footgun.** HA's service worker caches the card JS hard.
  Always bump `CARD_VERSION` (const.py) + console banner + `manifest.json` when the
  card changes, or stale UI is served. If still stale: hard refresh, or unregister
  the service worker (DevTools -> Application -> Service Workers).
- **"Custom element doesn't exist" flicker** was a load race from `add_extra_js_url`.
  Fixed by registering the card as a **Lovelace resource** (deterministic load) plus
  an `if (!customElements.get(...))` guard. Don't regress this.
- **TTS needs a configured engine.** Set `default_tts_engine` in the integration
  options to a TTS entity id (e.g. `tts.home_assistant_cloud`,
  `tts.google_translate_en_com`). Without it you get "No TTS engine configured".
  Find ids under Developer Tools -> States, filter `tts.`.
- **Pushing:** the Cowork sandbox cannot push to GitHub (proxy 403). The user runs
  `git push origin main` from their machine. Commit locally; let the user push.

## Open questions / verify on real hardware

- Multi-speaker **sync** via `join`/`unjoin` — confirm no echo/lag across a group.
- Exact **TTS media-source format** / which engine string is most robust.
- **Chime + TTS combine** quality (ffmpeg `concat` filter) — check seam/volume match.
- **File reachability**: Sonos must fetch recordings/combined files over LAN
  (`/local/...`); depends on HA internal URL being correct.
- **restore** edge cases (speaker already grouped, or playing a streaming source).

## Next steps / TODO (prioritized)

1. **Quick messages**: config-driven preset buttons in the card ("Middagen er klar",
   "Leggetid") that call `announce` with preset text (+ optional chime).
2. **Zones / groups**: named target groups ("Oppe", "Nede", "Alle") instead of only
   per-speaker chips.
3. **Per-speaker volume UI** in the card (service already accepts a dict volume).
4. **Message history**: keep recent recordings, allow replay of more than just the
   last one (0.3.0 replays only the most recent).
5. **Local mic over HTTP**: document split-horizon DNS so mic works without HTTPS
   round-trip when at home.
6. **v3**: two-way intercom; generic `media_player` support beyond Sonos.

Done in 0.3.0: independent chime volume (#3 old), replay last message (#4 old),
storage cleanup / `retention_hours` (#7 old).

## Conventions

- Service domain `sonos_intercom`; card UI text in Norwegian; reply to the user in
  Norwegian.
- Before committing: `python3 -m py_compile custom_components/sonos_intercom/*.py`
  and `node --check .../www/sonos-intercom-card.js`; validate changed JSON/YAML.
- Bump versions together when the card changes: `manifest.json` version,
  `CARD_VERSION` in const.py, and the console banner string in the card.
- Single HACS integration repo; the card is bundled and auto-registered (no separate
  frontend repo, no manual resource step for the user).
