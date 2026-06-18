# Changelog

All notable changes to the **Sonos Intercom** integration are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.4.0] - 2026-06-18

### Added

- **Custom chimes.** Upload your own chime audio directly from the card (file picker,
  "➕ Last opp chime"), or drop MP3 files into the custom chime folder. Uploaded files
  are converted to MP3 with ffmpeg and stored in `custom_chime_dir` (default
  `www/sonos_intercom_chimes`). Custom chimes then appear in the card's chime dropdown
  alongside the 5 bundled ones, and the `chime` service param accepts custom ids (the
  uploaded file name without extension). New upload endpoint:
  `POST /api/sonos_intercom/chime_upload`.
- **Quiet hours / night mode.** New options `quiet_start` and `quiet_end` (HH:MM) plus
  `quiet_max_volume` (0-100, default 20). During quiet hours the announcement volume is
  capped to `quiet_max_volume`; if it is 0, announcements are skipped entirely.
- **TTS language and voice.** The `announce` service accepts `language` (e.g. `nb`,
  `en`) and `voice` (engine-specific). The card exposes them in a new "Avansert"
  section in text mode.
- **`sonos_intercom.acknowledge` service.** Sends a quick acknowledgement ("Mottatt")
  back to the last message's source/targets. Params: `targets` (optional), `message`
  (optional), `chime` (optional, default `soft_ping`), `volume` (optional). A thin
  wrapper around `announce` with a default chime.
- **Inbox / message history (first-cut two-way intercom).** Recent messages are kept in
  memory (`history_size` option, default 20) and exposed through the new
  `sensor.sonos_intercom_last_message` entity. The card renders an "Innboks / Historikk"
  section with per-item replay ("▶") and reply ("↩︎ Svar", presets the sender's
  speakers), plus an acknowledge button ("✔ Kvitter"). Because Sonos speakers have no
  microphone, "two-way" is a compose-and-send message inbox + reply/acknowledge flow,
  not live voice.
- **`sensor.sonos_intercom_last_message` entity.** State is the last message text
  (`[Opptak]` for a recording, `[Chime]` for chime-only, `Ingen` if none). Attributes:
  `messages` (recent items: time, kind, message, audio_url, chime, targets, source,
  volume), `chimes` (available chimes incl. custom: id, label, custom, url),
  `quiet_active`, `last_source`, `last_targets`. The card reads this entity to render
  the chime dropdown, the inbox/history, and quiet-hours state.
- **`sonos_intercom_announced` event.** Fired on every `announce` (and `acknowledge`)
  with data `{message, audio_url, chime, targets, volume, source}` — a hook for user
  automations.
- **`source` param** on `announce`: free-text label of who/where the message came from,
  shown in the history/inbox and used for replies.
- **Recording preview in the card.** Listen to a browser recording before sending
  ("▶ Lytt").
- **Persisted card settings.** The card remembers volume, chime, chime volume, announce
  toggle, and language/voice between sessions via `localStorage`.
- **Generic `media_player` support.** `announce` now also works on non-Sonos
  `media_player` entities. Sonos-specific steps (snapshot/restore, join/unjoin grouping)
  are applied only to Sonos entities (detected via the entity registry); non-Sonos
  targets just use `play_media` with the announce flag and skip grouping. Untested by
  the maintainer (Sonos-only setup).

### Changed

- **`sonos_intercom.replay`** now accepts an optional `index` (integer, default 0 =
  most recent) to replay a specific item from the history, in addition to the existing
  optional `targets` / `volume` overrides.
- The card now dims/disables unavailable speakers, and its chime list is dynamic
  (bundled + custom) instead of a fixed list of five.

## [0.3.0] - 2026-06-18

### Added

- **Independent chime volume.** The `sonos_intercom.announce` service now accepts a
  `chime_volume` field (0-100) that controls the chime's loudness relative to the
  message. A "Chime-volum" slider was added to the card.
- **Replay.** A new `sonos_intercom.replay` service replays the last announcement,
  with optional `targets` and `volume` overrides. A "Spill av igjen" button was added
  to the card.
- **Automatic storage cleanup.** Old generated files (TTS clips, combined chime clips,
  and uploaded recordings) under the storage directory are now pruned automatically
  based on a new `retention_hours` option (default 24 hours; set to 0 to disable).

## [0.2.2] - 2026-06-18

### Fixed

- Fixed flaky card loading: the card is now registered as a Lovelace resource for a
  deterministic load order, with a guard against defining the custom element twice.
  This resolves the intermittent "custom element doesn't exist" flicker.

## [0.2.1] - 2026-06-18

### Fixed

- Cache-bust the card with a `?v=` version query string so browsers and the Home
  Assistant service worker reliably pick up the latest card instead of serving a
  stale copy (which previously hid the chime UI).

## [0.2.0] - 2026-06-18

### Added

- **Chimes.** Five bundled chimes (airport, ding-dong, soft ping, marimba, gong).
- Preview chimes directly in the browser from the card.
- Play a chime on its own on the selected speakers.
- Combine a chime with a message: the chime and the TTS/recording are concatenated
  into a single MP3 with ffmpeg before playback.

## [0.1.0] - 2026-06-18

### Added

- Initial release: core `sonos_intercom` integration scaffold.
- `sonos_intercom.announce` service for announcing **text-to-speech** or a
  **browser microphone recording** on selected Sonos speakers.
- Browser recording via `MediaRecorder`, uploaded to an HTTP endpoint and converted
  to MP3 with ffmpeg.
- Ducking via Home Assistant's native Sonos `announce: true` overlay.
- Multi-speaker sync by temporarily grouping speakers (`join`/`unjoin`).
- Config flow options: `default_volume`, `default_tts_engine`, and `storage_dir`.
- Bundled Lovelace card (`sonos-intercom-card.js`) for sending announcements.
