"""Constants for the Sonos Intercom integration."""

DOMAIN = "sonos_intercom"

PLATFORMS = ["sensor"]

# Config / options keys
CONF_DEFAULT_VOLUME = "default_volume"
CONF_DEFAULT_TTS = "default_tts_engine"
CONF_STORAGE_DIR = "storage_dir"
CONF_RETENTION_HOURS = "retention_hours"
CONF_CUSTOM_CHIME_DIR = "custom_chime_dir"
CONF_QUIET_START = "quiet_start"
CONF_QUIET_END = "quiet_end"
CONF_QUIET_MAX_VOLUME = "quiet_max_volume"
CONF_HISTORY_SIZE = "history_size"

# Defaults
DEFAULT_VOLUME = 40
DEFAULT_STORAGE_DIR = "www/sonos_intercom"
DEFAULT_RETENTION_HOURS = 24  # prune generated files older than this (0 disables)
DEFAULT_CUSTOM_CHIME_DIR = "www/sonos_intercom_chimes"
DEFAULT_QUIET_START = ""  # "HH:MM"; empty disables quiet hours
DEFAULT_QUIET_END = ""
DEFAULT_QUIET_MAX_VOLUME = 20  # cap volume during quiet hours (0 = skip entirely)
DEFAULT_HISTORY_SIZE = 20

DEFAULT_OPTIONS = {
    CONF_DEFAULT_VOLUME: DEFAULT_VOLUME,
    CONF_DEFAULT_TTS: "",
    CONF_STORAGE_DIR: DEFAULT_STORAGE_DIR,
    CONF_RETENTION_HOURS: DEFAULT_RETENTION_HOURS,
    CONF_CUSTOM_CHIME_DIR: DEFAULT_CUSTOM_CHIME_DIR,
    CONF_QUIET_START: DEFAULT_QUIET_START,
    CONF_QUIET_END: DEFAULT_QUIET_END,
    CONF_QUIET_MAX_VOLUME: DEFAULT_QUIET_MAX_VOLUME,
    CONF_HISTORY_SIZE: DEFAULT_HISTORY_SIZE,
}

# Services
SERVICE_ANNOUNCE = "announce"
SERVICE_REPLAY = "replay"
SERVICE_ACKNOWLEDGE = "acknowledge"

ATTR_MESSAGE = "message"
ATTR_AUDIO_URL = "audio_url"
ATTR_TARGETS = "targets"
ATTR_VOLUME = "volume"
ATTR_ANNOUNCE = "announce"
ATTR_TTS_ENGINE = "tts_engine"
ATTR_SYNC = "sync"
ATTR_CHIME = "chime"
ATTR_CHIME_VOLUME = "chime_volume"
ATTR_LANGUAGE = "language"
ATTR_VOICE = "voice"
ATTR_SOURCE = "source"
ATTR_INDEX = "index"

# Events / dispatcher signals
EVENT_ANNOUNCED = "sonos_intercom_announced"
SIGNAL_UPDATE = f"{DOMAIN}_update"

# hass.data keys (underscore-prefixed so they are skipped when iterating options)
DATA_LAST = "_last"
DATA_HISTORY = "_history"
DATA_CHIMES = "_chimes"

# Frontend / static serving
STATIC_BASE = "/sonos_intercom_static"
CARD_FILENAME = "sonos-intercom-card.js"
CARD_URL = f"{STATIC_BASE}/{CARD_FILENAME}"
CARD_VERSION = "0.4.0"  # bump to force browsers to reload the card
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
