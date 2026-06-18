"""Core announcement logic for Sonos Intercom.

Strategy:
- announce=True  -> rely on Sonos' native overlay (ducks current audio and
  restores it automatically). We only set the announce volume via `extra`.
- announce=False -> snapshot the speakers, optionally group them for synced
  playback, play the media, wait for it to finish, then restore.

The multi-speaker synced playback (join/unjoin) is the part most in need of
real-world testing on actual hardware - see the project spec.
"""
from __future__ import annotations

import asyncio
import logging
import urllib.parse

from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.network import get_url

from .const import CONF_DEFAULT_TTS

_LOGGER = logging.getLogger(__name__)

MAX_WAIT_SECONDS = 60


def _build_media(
    message: str | None,
    audio_url: str | None,
    tts_engine: str | None,
    options: dict,
) -> tuple[str, str]:
    """Resolve the media_content_id / media_content_type to play."""
    if audio_url:
        return audio_url, "music"

    engine = tts_engine or options.get(CONF_DEFAULT_TTS)
    if not engine:
        raise HomeAssistantError(
            "No TTS engine configured. Set a default TTS engine in the Sonos "
            "Intercom options, or pass 'tts_engine' to the service call."
        )
    encoded = urllib.parse.quote(message or "")
    media_id = f"media-source://tts/{engine}?message={encoded}"
    return media_id, "music"


def _coordinator_volume(volume, coordinator: str) -> int | None:
    """Return the announce volume (0-100) for the coordinator speaker."""
    if volume is None:
        return None
    if isinstance(volume, dict):
        value = volume.get(coordinator)
        return int(value) if value is not None else None
    return int(volume)


async def _set_volumes(hass: HomeAssistant, targets: list[str], volume) -> None:
    """Explicitly set volume on each target (used when not relying on announce)."""
    for entity_id in targets:
        if isinstance(volume, dict):
            value = volume.get(entity_id)
        else:
            value = volume
        if value is None:
            continue
        await hass.services.async_call(
            "media_player",
            "volume_set",
            {"entity_id": entity_id, "volume_level": max(0, min(100, int(value))) / 100},
            blocking=True,
        )


async def _wait_until_idle(hass: HomeAssistant, entity_id: str) -> None:
    """Best-effort wait until the speaker has stopped playing the clip."""
    waited = 0.0
    step = 0.5
    # Give playback a moment to start.
    await asyncio.sleep(1.0)
    while waited < MAX_WAIT_SECONDS:
        state = hass.states.get(entity_id)
        if state is None or state.state != "playing":
            return
        await asyncio.sleep(step)
        waited += step


async def async_announce(
    hass: HomeAssistant,
    options: dict,
    *,
    message: str | None = None,
    audio_url: str | None = None,
    targets: list[str],
    volume=None,
    announce: bool = True,
    tts_engine: str | None = None,
    sync: bool = True,
) -> None:
    """Play a TTS message or audio clip on one or more Sonos speakers."""
    if not targets:
        raise HomeAssistantError("No target speakers provided.")
    if not message and not audio_url:
        raise HomeAssistantError("Provide either 'message' or 'audio_url'.")

    media_content_id, media_content_type = _build_media(
        message, audio_url, tts_engine, options
    )

    coordinator = targets[0]
    members = targets[1:]
    group = sync and len(targets) > 1
    use_snapshot = not announce  # native announce restores audio by itself

    if use_snapshot:
        await hass.services.async_call(
            "sonos", "snapshot", {"entity_id": targets, "with_group": True}, blocking=True
        )

    try:
        if group:
            await hass.services.async_call(
                "media_player",
                "join",
                {"entity_id": coordinator, "group_members": members},
                blocking=True,
            )

        # Per-speaker volume (or any volume when not using native announce) is set
        # explicitly; otherwise the announce volume is passed via `extra`.
        if volume is not None and (not announce or isinstance(volume, dict)):
            await _set_volumes(hass, targets, volume)

        play_data = {
            "entity_id": [coordinator] if group else targets,
            "media_content_id": media_content_id,
            "media_content_type": media_content_type,
            "announce": announce,
        }
        coord_vol = _coordinator_volume(volume, coordinator)
        if announce and coord_vol is not None:
            play_data["extra"] = {"volume": coord_vol}

        await hass.services.async_call(
            "media_player", "play_media", play_data, blocking=True
        )

        if use_snapshot:
            await _wait_until_idle(hass, coordinator)

    except Exception as err:  # noqa: BLE001 - log and re-raise after cleanup
        _LOGGER.error("Sonos Intercom announcement failed: %s", err)
        raise
    finally:
        if group:
            try:
                await hass.services.async_call(
                    "media_player", "unjoin", {"entity_id": members}, blocking=True
                )
            except Exception as err:  # noqa: BLE001
                _LOGGER.warning("Could not ungroup speakers: %s", err)
        if use_snapshot:
            try:
                await hass.services.async_call(
                    "sonos",
                    "restore",
                    {"entity_id": targets, "with_group": True},
                    blocking=True,
                )
            except Exception as err:  # noqa: BLE001
                _LOGGER.warning("Could not restore speakers: %s", err)


def build_local_url(hass: HomeAssistant, path: str) -> str:
    """Return an absolute URL Sonos can fetch from, given a local /local/... path."""
    base = get_url(hass, prefer_external=False, allow_internal=True)
    return f"{base}{path}"
