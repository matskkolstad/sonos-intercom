"""Sensor exposing the last Sonos Intercom message + history + chimes.

The Lovelace card reads this entity's attributes to render the dynamic chime
dropdown, the inbox/history (with replay and reply), and quiet-hours state.
History is in-memory and resets when Home Assistant restarts.
"""
from __future__ import annotations

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .announce import quiet_active
from .const import DATA_CHIMES, DATA_HISTORY, DOMAIN, SIGNAL_UPDATE


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up the Sonos Intercom sensor."""
    async_add_entities([SonosIntercomLastMessage(hass, entry)])


class SonosIntercomLastMessage(SensorEntity):
    """Reports the most recent announcement and exposes history/chimes."""

    _attr_icon = "mdi:bullhorn"
    _attr_should_poll = False

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        self.hass = hass
        self._entry = entry
        self._attr_unique_id = f"{DOMAIN}_last_message"
        self._attr_name = "Sonos Intercom last message"

    async def async_added_to_hass(self) -> None:
        self.async_on_remove(
            async_dispatcher_connect(self.hass, SIGNAL_UPDATE, self._handle_update)
        )

    @callback
    def _handle_update(self) -> None:
        self.async_write_ha_state()

    def _options(self) -> dict:
        for key, opts in self.hass.data.get(DOMAIN, {}).items():
            if not str(key).startswith("_"):
                return opts
        return {}

    def _history(self) -> list[dict]:
        return self.hass.data.get(DOMAIN, {}).get(DATA_HISTORY) or []

    @property
    def native_value(self):
        history = self._history()
        if not history:
            return "Ingen"
        item = history[0]
        if item.get("message"):
            return item["message"][:255]
        if item.get("kind") == "recording":
            return "[Opptak]"
        return "[Chime]"

    @property
    def extra_state_attributes(self) -> dict:
        history = self._history()
        last = history[0] if history else {}
        return {
            "messages": history,
            "chimes": self.hass.data.get(DOMAIN, {}).get(DATA_CHIMES) or [],
            "quiet_active": quiet_active(self.hass, self._options()),
            "last_source": last.get("source"),
            "last_targets": last.get("targets"),
        }
