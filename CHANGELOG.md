# Changelog

All notable changes to the **Sonos Intercom** integration are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

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
