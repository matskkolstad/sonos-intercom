"""Config flow for Sonos Intercom."""
from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant.config_entries import (
    ConfigEntry,
    ConfigFlow,
    OptionsFlow,
)
from homeassistant.core import callback
from homeassistant.data_entry_flow import FlowResult

from .const import (
    CONF_DEFAULT_TTS,
    CONF_DEFAULT_VOLUME,
    CONF_RETENTION_HOURS,
    CONF_STORAGE_DIR,
    DEFAULT_OPTIONS,
    DEFAULT_RETENTION_HOURS,
    DEFAULT_STORAGE_DIR,
    DEFAULT_VOLUME,
    DOMAIN,
)


class SonosIntercomConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Sonos Intercom."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        if self._async_current_entries():
            return self.async_abort(reason="single_instance_allowed")

        if user_input is not None:
            return self.async_create_entry(
                title="Sonos Intercom", data={}, options=dict(DEFAULT_OPTIONS)
            )

        return self.async_show_form(step_id="user")

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> OptionsFlow:
        """Get the options flow for this handler."""
        return SonosIntercomOptionsFlow(config_entry)


class SonosIntercomOptionsFlow(OptionsFlow):
    """Handle options for Sonos Intercom."""

    def __init__(self, config_entry: ConfigEntry) -> None:
        """Initialize options flow."""
        self._entry = config_entry

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Manage the options."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        opts = self._entry.options
        schema = vol.Schema(
            {
                vol.Optional(
                    CONF_DEFAULT_VOLUME,
                    default=opts.get(CONF_DEFAULT_VOLUME, DEFAULT_VOLUME),
                ): vol.All(vol.Coerce(int), vol.Range(min=0, max=100)),
                vol.Optional(
                    CONF_DEFAULT_TTS,
                    default=opts.get(CONF_DEFAULT_TTS, ""),
                ): str,
                vol.Optional(
                    CONF_STORAGE_DIR,
                    default=opts.get(CONF_STORAGE_DIR, DEFAULT_STORAGE_DIR),
                ): str,
                vol.Optional(
                    CONF_RETENTION_HOURS,
                    default=opts.get(
                        CONF_RETENTION_HOURS, DEFAULT_RETENTION_HOURS
                    ),
                ): vol.All(vol.Coerce(int), vol.Range(min=0, max=8760)),
            }
        )
        return self.async_show_form(step_id="init", data_schema=schema)
