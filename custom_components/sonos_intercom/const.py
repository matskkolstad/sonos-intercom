"""Constants for the Sonos Intercom integration."""

DOMAIN = "sonos_intercom"

# Config / options keys
CONF_DEFAULT_VOLUME = "default_volume"
CONF_DEFAULT_TTS = "default_tts_engine"
CONF_STORAGE_DIR = "storage_dir"
CONF_RETENTION_HOURS = "retention_hours"

# Defaults
DEFAULT_VOLUME = 40
DEFAULT_STORAGE_DIR = "www/sonos_intercom"
DEFAULT_RETENTION_HOURS = 24  # prune generated files older than this (0 disables)

DEFAULT_OPTIONS = {
    CONF_DEFAULT_VOLUME: DEFAULT_VOLUME,
    CONF_DEFAULT_TTS: "",
    CONF_STORAGE_DIR: DEFAULT_STORAGE_DIR,
    CONF_RETENTION_HOURS: DEFAULT_RETENTION_HOURS,
}

# Services
SERVICE_ANNOUNCE = "announce"
SERVICE_REPLAY = "replay"

ATTR_MESSAGE = "message"
ATTR_AUDIO_URL = "audio_url"
ATTR_TARGETS = "targets"
ATTR_VOLUME = "volume"
ATTR_ANNOUNCE = "announce"
ATTR_TTS_ENGINE = "tts_engine"
ATTR_SYNC = "sync"
ATTR_CHIME = "chime"
ATTR_CHIME_VOLUME = "chime_volume"

# Frontend / static serving
STATIC_BASE = "/sonos_intercom_static"
CARD_FILENAME = "sonos-intercom-card.js"
CARD_URL = f"{STATIC_BASE}/{CARD_FILENAME}"
CARD_VERSION = "0.3.0"  # bump to force browsers to reload the card
CHIME_URL_BASE = f"{STATIC_BASE}/chimes"

# Bundled chimes: id -> (filename, label)
CHIMES = {
    "airport": ("airport.mp3", "Flyplass"),
    "ding_dong": ("ding_dong.mp3", "Ding-dong"),
    "soft_ping": ("soft_ping.mp3", "Mykt pling"),
    "marimba": ("marimba.mp3", "Marimba"),
    "gong": ("gong.mp3", "Gong"),
}

CHIME_NONE = "none"
