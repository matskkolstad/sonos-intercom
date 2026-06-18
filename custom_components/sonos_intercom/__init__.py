"""The Sonos Intercom integration."""
from __future__ import annotations

import logging
import os

import voluptuous as vol

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.helpers import config_validation as cv

from .announce import async_announce
from .const import (
    ATTR_ANNOUNCE,
    ATTR_AUDIO_URL,
    ATTR_MESSAGE,
    ATTR_SYNC,
    ATTR_TARGETS,
    ATTR_TTS_ENGINE,
    ATTR_VOLUME,
    CARD_FILENAME,
    CARD_URL,
    CONF_DEFAULT_VOLUME,
    CONF_DEFAULT_TTS,
    DEFAULT_OPTIONS,
    DOMAIN,
    SERVICE_ANNOUNCE,
)
from .http import IntercomUploadView

_LOGGER = logging.getLogger(__name__)

ANNOUNCE_SCHEMA = vol.Schema(
    {
        vol.Exclusive(ATTR_MESSAGE, "content"): cv.string,
        vol.Exclusive(ATTR_AUDIO_URL, "content"): cv.string,
        vol.Required(ATTR_TARGETS): cv.entity_ids,
        vol.Optional(ATTR_VOLUME): vol.Any(
            vol.All(vol.Coerce(int), vol.Range(min=0, max=100)),
            {cv.entity_id: vol.All(vol.Coerce(int), vol.Range(min=0, max=100))},
        ),
        vol.Optional(ATTR_ANNOUNCE, default=True): cv.boolean,
        vol.Optional(ATTR_TTS_ENGINE): cv.string,
        vol.Optional(ATTR_SYNC, default=True): cv.boolean,
    }
)


def get_options(hass: HomeAssistant) -> dict:
    """Return the merged options from the first config entry (single instance)."""
    data = hass.data.get(DOMAIN, {})
    for options in data.values():
        return options
    return dict(DEFAULT_OPTIONS)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Sonos Intercom from a config entry."""
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = {**DEFAULT_OPTIONS, **entry.options}

    # Register the upload endpoint (only once).
    if not hass.data[DOMAIN].get("_view_registered"):
        hass.http.register_view(IntercomUploadView())
        hass.data[DOMAIN]["_view_registered"] = True

    # Serve and auto-register the Lovelace card.
    await _async_register_card(hass)

    # Register the announce service (only once).
    if not hass.services.has_service(DOMAIN, SERVICE_ANNOUNCE):

        async def handle_announce(call: ServiceCall) -> None:
            options = get_options(hass)
            volume = call.data.get(ATTR_VOLUME, options.get(CONF_DEFAULT_VOLUME))
            await async_announce(
                hass,
                options,
                message=call.data.get(ATTR_MESSAGE),
                audio_url=call.data.get(ATTR_AUDIO_URL),
                targets=call.data[ATTR_TARGETS],
                volume=volume,
                announce=call.data.get(ATTR_ANNOUNCE, True),
                tts_engine=call.data.get(ATTR_TTS_ENGINE) or options.get(CONF_DEFAULT_TTS),
                sync=call.data.get(ATTR_SYNC, True),
            )

        hass.services.async_register(
            DOMAIN, SERVICE_ANNOUNCE, handle_announce, schema=ANNOUNCE_SCHEMA
        )

    entry.async_on_unload(entry.add_update_listener(_async_update_listener))
    return True


async def _async_register_card(hass: HomeAssistant) -> None:
    """Serve the card as a static file and add it as an extra JS module."""
    from homeassistant.components.frontend import add_extra_js_url
    from homeassistant.components.http import StaticPathConfig

    card_path = os.path.join(os.path.dirname(__file__), "www", CARD_FILENAME)
    try:
        await hass.http.async_register_static_paths(
            [StaticPathConfig(CARD_URL, card_path, False)]
        )
    except RuntimeError:
        # Path already registered (e.g. reload) - ignore.
        pass
    add_extra_js_url(hass, CARD_URL)


async def _async_update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Handle options update."""
    hass.data[DOMAIN][entry.entry_id] = {**DEFAULT_OPTIONS, **entry.options}


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    hass.data.get(DOMAIN, {}).pop(entry.entry_id, None)

    # If this was the last entry, drop the service.
    remaining = [k for k in hass.data.get(DOMAIN, {}) if not k.startswith("_")]
    if not remaining and hass.services.has_service(DOMAIN, SERVICE_ANNOUNCE):
        hass.services.async_remove(DOMAIN, SERVICE_ANNOUNCE)

    return True
