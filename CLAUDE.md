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
   HTTPS), or sends TTS text. Reads `sensor.sonos_intercom_last_message` to render
   the dynamic chime dropdown, the inbox/history, and quiet-hours state. Calls the
   `sonos_intercom.announce` / `replay` / `acknowledge` services.
2. **Backend** — Python integration. HTTP endpoints receive a base64 recording or a
   custom-chime upload, convert to MP3 with ffmpeg, serve them; `announce` service
   plays media and pushes to the history sensor. Non-Sonos `media_player` targets are
   supported (Sonos-specific steps skipped).
3. **Playback** — uses HA's built-in Sonos integration (`media_player.play_media`
   with `announce: true`). Sonos fetches the audio file from HA over the LAN. For
   non-Sonos targets, `play_media` is used without the Sonos snapshot/group steps.

## Repo layout

```
custom_components/sonos_intercom/
  __init__.py       # setup, service registration, static + Lovelace-resource registration
  announce.py       # core play logic + chime combine (ffmpeg); fires sonos_intercom_announced
  chimes.py         # bundled + custom chime discovery, upload conversion, resolution
  sensor.py         # sensor.sonos_intercom_last_message (state + history/chimes/quiet attrs)
  http.py           # /api/sonos_intercom/upload (recording) + /chime_upload (custom chime) -> ffmpeg -> mp3
  config_flow.py    # options: default_volume, default_tts_engine, storage_dir, retention_hours,
                    #          quiet_start, quiet_end, quiet_max_volume, custom_chime_dir, history_size
  const.py          # DOMAIN, CHIMES, CARD_VERSION, etc.
  services.yaml     # UI schema for announce / replay / acknowledge
  www/sonos-intercom-card.js
  www/chimes/*.mp3  # 5 bundled chimes (airport, ding_dong, soft_ping, marimba, gong)
  translations/ (en, nb)
docs/Sonos-Intercom-Spec.md
hacs.json
```

Custom chimes live in `custom_chime_dir` (default `www/sonos_intercom_chimes`, relative
to config) so Sonos can fetch them via `/local/`. Uploaded files are converted to MP3.

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

## CRITICAL dev gotchas

**Whenever you change `www/sonos-intercom-card.js`, bump `CARD_VERSION` in `const.py`**
(and the console banner string + `manifest.json` version). Otherwise the browser /
HA service worker serves a stale cached card and changes won't appear. This caused
real debugging pain early on.

**When adding or changing a feature, update `README.md` (and `CHANGELOG.md`) as part of
the same change — documentation is required, not optional.** Don't merge a behavior
change without the matching doc update.

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

- Designed for Sonos **S2**; HA **2024.6+**. As of 0.4.0 `announce` also works on
  generic non-Sonos `media_player` entities (Sonos-specific snapshot/restore +
  join/unjoin steps are skipped for them). Generic support is **untested** by the
  maintainer (Sonos-only setup).
- **Two-way is not live voice.** Sonos speakers have no microphone, so "two-way" is a
  message inbox + reply/acknowledge flow (compose-and-send back to the sender's zone).
- Microphone needs **HTTPS** in the browser; TTS works regardless.
- A TTS engine id must be set (options `default_tts_engine`, e.g. `tts.home_assistant_cloud`).
- Sonos network: TCP 1443 + 1400 reachable from HA.

## Status

Current version: **0.4.0**. Working core: TTS, browser recording over HTTPS, 5 bundled
chimes (preview in browser, play alone on speakers, combine before message), stable card
loading. 0.4.0 adds: **custom chimes** (upload from card / drop into `custom_chime_dir`),
**quiet hours** (`quiet_start`/`quiet_end`/`quiet_max_volume`), **TTS language/voice**,
**recording preview** + **persisted card settings**, an **inbox/history** with reply +
acknowledge (first-cut two-way, no mic), the `sensor.sonos_intercom_last_message` entity,
the `sonos_intercom_announced` event, the `acknowledge` service, `replay` by `index`, and
**generic `media_player`** support. Up through 0.2.2 confirmed working on the user's
setup; 0.3.0 and 0.4.0 features need real-hardware confirmation.

## Roadmap (next ideas)

- Remaining: predefined quick messages (preset buttons), zones/speaker groups,
  per-speaker volume UI in the card, live two-way voice, full verification of generic
  `media_player` support.
- Landed in 0.4.0: custom chimes, quiet hours, TTS language/voice, inbox/history with
  reply + acknowledge, `sensor.sonos_intercom_last_message`, `sonos_intercom_announced`
  event, `replay` by `index`, generic `media_player` (untested).

## Service reference (quick)

Service: `sonos_intercom.announce`. Params: `message` OR `audio_url` (or neither,
if only `chime`); `targets` (required, list of media_player entity_ids); `volume`
(0-100 number, or a dict mapping entity_id -> 0-100 for per-speaker); `announce`
(bool, default true); `tts_engine` (overrides default); `sync` (bool, default true);
`chime` (a bundled id — airport, ding_dong, soft_ping, marimba, gong — OR a custom
chime id = uploaded file name without extension); `chime_volume` (0-100, loudness of
the chime relative to the message; only applies when a chime is combined with a
message/recording — implemented as an ffmpeg `volume` gain on the chime stream during
concat). **New in 0.4.0:** `language` (TTS language code, e.g. `nb`, `en`); `voice`
(TTS voice, engine-specific, passed as a TTS option); `source` (free-text label of
who/where the message came from; shown in history/inbox and used for replies).

Service: `sonos_intercom.acknowledge` (0.4.0). Sends a quick acknowledgement
("Mottatt") back — a thin wrapper around `announce` with a default chime. Params:
`targets` (optional; defaults to the last message's source/targets), `message`
(optional short text), `chime` (optional, default `soft_ping`), `volume` (optional).

Service: `sonos_intercom.replay`. Replays an announcement from history. Optional
`index` (int, default 0 = most recent) selects which history item to replay; optional
`targets` and `volume` override the stored ones. Pure-TTS replays always work
(regenerated from the media-source id); recording/combined-chime replays depend on the
file still existing (may have been pruned — see storage cleanup).

Entity: `sensor.sonos_intercom_last_message` (0.4.0). State = last message text
(`[Opptak]` for a recording, `[Chime]` for chime-only, `Ingen` if none). Attributes:
`messages` (recent items: time, kind, message, audio_url, chime, targets, source,
volume), `chimes` (available chimes incl. custom: id, label, custom, url),
`quiet_active`, `last_source`, `last_targets`. The card reads this to render the chime
dropdown, the inbox/history, and quiet-hours state. History size = `history_size`
option (default 20; in-memory, lost on HA restart).

Event: `sonos_intercom_announced` (0.4.0). Fired on every `announce` (and
`acknowledge`) with data `{message, audio_url, chime, targets, volume, source}` — a
hook for user automations.

Custom chimes (0.4.0): uploaded via the card (`POST /api/sonos_intercom/chime_upload`,
"➕ Last opp chime") or dropped as MP3s into `custom_chime_dir` (default
`www/sonos_intercom_chimes`). Uploaded files are converted to MP3 (ffmpeg) and appear
in the card's chime dropdown alongside the bundled five.

Quiet hours (0.4.0): options `quiet_start`/`quiet_end` (HH:MM, empty = disabled) and
`quiet_max_volume` (0-100, default 20). During quiet hours the announcement volume is
capped to `quiet_max_volume`; if it is 0, announcements are skipped entirely.

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
# TTS with language/voice and a source label (shown in the inbox)
action: sonos_intercom.announce
data:
  message: "Middagen er klar"
  language: nb
  voice: "nb-NO-Standard-A"
  source: "Kjøkkenet"
  targets: [media_player.stue]
```
```yaml
# Chime alone (bundled or custom id)
action: sonos_intercom.announce
data:
  chime: ding_dong
  targets: [media_player.stue]
```
```yaml
# Replay a specific history item (0 = most recent)
action: sonos_intercom.replay
data:
  index: 0
  targets: [media_player.stue]   # optional; reuses stored targets if omitted
```
```yaml
# Acknowledge the last message ("Mottatt")
action: sonos_intercom.acknowledge
data:
  message: "Mottatt"             # optional
  chime: soft_ping               # optional, default soft_ping
  targets: [media_player.kjokken] # optional; defaults to last message's source/targets
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

## Next steps / TODO

The historical, numbered TODO list has been removed — what shipped is tracked in
`CHANGELOG.md` and `README.md`, and the forward-looking items live in the **Roadmap**
section above.

Remaining ideas: quick messages (preset buttons), zones/speaker groups, per-speaker
volume UI in the card, live two-way voice, full generic `media_player` verification.

## Conventions

- **Documentation is required, not optional.** When adding or changing a feature,
  update `README.md` (and `CHANGELOG.md`) as part of the same change. (See the CRITICAL
  dev gotchas section.)
- Service domain `sonos_intercom`; card UI text in Norwegian; reply to the user in
  Norwegian.
- Before committing: `python3 -m py_compile custom_components/sonos_intercom/*.py`
  and `node --check .../www/sonos-intercom-card.js`; validate changed JSON/YAML.
- Bump versions together when the card changes: `manifest.json` version,
  `CARD_VERSION` in const.py, and the console banner string in the card.
- Single HACS integration repo; the card is bundled and auto-registered (no separate
  frontend repo, no manual resource step for the user).
