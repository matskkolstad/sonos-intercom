"""Constants for the Sonos Intercom integration."""

DOMAIN = "sonos_intercom"

# Config / options keys
CONF_DEFAULT_VOLUME = "default_volume"
CONF_DEFAULT_TTS = "default_tts_engine"
CONF_STORAGE_DIR = "storage_dir"

# Defaults
DEFAULT_VOLUME = 40
DEFAULT_STORAGE_DIR = "www/sonos_intercom"

DEFAULT_OPTIONS = {
    CONF_DEFAULT_VOLUME: DEFAULT_VOLUME,
    CONF_DEFAULT_TTS: "",
    CONF_STORAGE_DIR: DEFAULT_STORAGE_DIR,
}

# Service
SERVICE_ANNOUNCE = "announce"

ATTR_MESSAGE = "message"
ATTR_AUDIO_URL = "audio_url"
ATTR_TARGETS = "targets"
ATTR_VOLUME = "volume"
ATTR_ANNOUNCE = "announce"
ATTR_TTS_ENGINE = "tts_engine"
ATTR_SYNC = "sync"

# Frontend card
CARD_URL = "/sonos_intercom_static/sonos-intercom-card.js"
CARD_FILENAME = "sonos-intercom-card.js"
