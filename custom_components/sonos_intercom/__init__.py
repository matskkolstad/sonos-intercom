"""The Sonos Intercom integration."""
from __future__ import annotations

import logging
import os

import voluptuous as vol

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.helpers import config_validation as cv

from .announce import async_announce, async_replay
from .const import (
    ATTR_ANNOUNCE,
    ATTR_AUDIO_URL,
    ATTR_CHIME,
    ATTR_CHIME_VOLUME,
    ATTR_MESSAGE,
    ATTR_SYNC,
    ATTR_TARGETS,
    ATTR_TTS_ENGINE,
    ATTR_VOLUME,
    CARD_URL,
    CARD_VERSION,
    CONF_DEFAULT_VOLUME,
    CONF_DEFAULT_TTS,
    DEFAULT_OPTIONS,
    DOMAIN,
    SERVICE_ANNOUNCE,
    SERVICE_REPLAY,
    STATIC_BASE,
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
        vol.Optional(ATTR_CHIME): cv.string,
        vol.Optional(ATTR_CHIME_VOLUME): vol.All(
            vol.Coerce(int), vol.Range(min=0, max=100)
        ),
    }
)

REPLAY_SCHEMA = vol.Schema(
    {
        vol.Optional(ATTR_TARGETS): cv.entity_ids,
        vol.Optional(ATTR_VOLUME): vol.Any(
            vol.All(vol.Coerce(int), vol.Range(min=0, max=100)),
            {cv.entity_id: vol.All(vol.Coerce(int), vol.Range(min=0, max=100))},
        ),
    }
)


def get_options(hass: HomeAssistant) -> dict:
    """Return the merged options from the first config entry (single instance)."""
    data = hass.data.get(DOMAIN, {})
    for key, options in data.items():
        if not str(key).startswith("_"):
            return options
    return dict(DEFAULT_OPTIONS)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Sonos Intercom from a config entry."""
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = {**DEFAULT_OPTIONS, **entry.options}

    if not hass.data[DOMAIN].get("_view_registered"):
        hass.http.register_view(IntercomUploadView())
        hass.data[DOMAIN]["_view_registered"] = True

    await _async_register_static(hass)
    await _async_register_card(hass)

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
                chime=call.data.get(ATTR_CHIME),
                chime_volume=call.data.get(ATTR_CHIME_VOLUME),
            )

        hass.services.async_register(
            DOMAIN, SERVICE_ANNOUNCE, handle_announce, schema=ANNOUNCE_SCHEMA
        )

    if not hass.services.has_service(DOMAIN, SERVICE_REPLAY):

        async def handle_replay(call: ServiceCall) -> None:
            await async_replay(
                hass,
                targets=call.data.get(ATTR_TARGETS),
                volume=call.data.get(ATTR_VOLUME),
            )

        hass.services.async_register(
            DOMAIN, SERVICE_REPLAY, handle_replay, schema=REPLAY_SCHEMA
        )

    entry.async_on_unload(entry.add_update_listener(_async_update_listener))
    return True


async def _async_register_static(hass: HomeAssistant) -> None:
    """Serve the integration's www folder (card + chimes) as static files."""
    from homeassistant.components.http import StaticPathConfig

    www_dir = os.path.join(os.path.dirname(__file__), "www")
    try:
        await hass.http.async_register_static_paths(
            [StaticPathConfig(STATIC_BASE, www_dir, False)]
        )
    except RuntimeError:
        # Already registered (e.g. reload) - ignore.
        pass


async def _async_register_card(hass: HomeAssistant) -> None:
    """Register the card as a Lovelace resource so it loads deterministically.

    Falls back to add_extra_js_url for YAML-mode dashboards or if the Lovelace
    resource collection is unavailable.
    """
    from homeassistant.components.frontend import add_extra_js_url

    full_url = f"{CARD_URL}?v={CARD_VERSION}"

    data = hass.data.get("lovelace")
    resources = getattr(data, "resources", None)
    if resources is None and isinstance(data, dict):
        resources = data.get("resources")

    # Storage-mode resource collection supports async_create_item.
    if resources is None or not hasattr(resources, "async_create_item"):
        add_extra_js_url(hass, full_url)
        return

    try:
        if hasattr(resources, "loaded") and not resources.loaded:
            await resources.async_load()
            resources.loaded = True

        for item in list(resources.async_items()):
            if item.get("url", "").split("?")[0] == CARD_URL:
                if item.get("url") != full_url:
                    await resources.async_update_item(item["id"], {"url": full_url})
                return

        await resources.async_create_item({"res_type": "module", "url": full_url})
    except Exception as err:  # noqa: BLE001
        _LOGGER.warning(
            "Could not register Lovelace resource, falling back to extra_js_url: %s",
            err,
        )
        add_extra_js_url(hass, full_url)


async def _async_update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Handle options update."""
    hass.data[DOMAIN][entry.entry_id] = {**DEFAULT_OPTIONS, **entry.options}


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    hass.data.get(DOMAIN, {}).pop(entry.entry_id, None)
    remaining = [k for k in hass.data.get(DOMAIN, {}) if not str(k).startswith("_")]
    if not remaining:
        if hass.services.has_service(DOMAIN, SERVICE_ANNOUNCE):
            hass.services.async_remove(DOMAIN, SERVICE_ANNOUNCE)
        if hass.services.has_service(DOMAIN, SERVICE_REPLAY):
            hass.services.async_remove(DOMAIN, SERVICE_REPLAY)
    return True
