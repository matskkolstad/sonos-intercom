"""Core announcement logic for Sonos Intercom.

Strategy:
- announce=True  -> rely on Sonos' native overlay (ducks current audio and
  restores it automatically). We only set the announce volume via `extra`.
- announce=False -> snapshot the speakers, optionally group them for synced
  playback, play the media, wait for it to finish, then restore.

Chimes:
- A chime can be played before the message. When both a chime and a message
  (TTS) or recording are present, they are combined into a single MP3 with
  ffmpeg so they play seamlessly in one announcement.
- A chime can also be played on its own (no message/audio_url).
"""
from __future__ import annotations

import asyncio
import logging
import os
import time
import urllib.parse
from functools import partial

from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.network import get_url

from .const import (
    CHIME_NONE,
    CHIME_URL_BASE,
    CHIMES,
    CONF_DEFAULT_TTS,
    CONF_STORAGE_DIR,
    DEFAULT_STORAGE_DIR,
)

_LOGGER = logging.getLogger(__name__)

MAX_WAIT_SECONDS = 60


def build_local_url(hass: HomeAssistant, path: str) -> str:
    """Return an absolute URL Sonos can fetch from, given an HA-served path."""
    base = get_url(hass, prefer_external=False, allow_internal=True)
    return f"{base}{path}"


def _build_tts_media(message: str, tts_engine: str | None, options: dict) -> str:
    """Build a media-source TTS id for the given message."""
    engine = tts_engine or options.get(CONF_DEFAULT_TTS)
    if not engine:
        raise HomeAssistantError(
            "No TTS engine configured. Set a default TTS engine in the Sonos "
            "Intercom options, or pass 'tts_engine' to the service call."
        )
    encoded = urllib.parse.quote(message or "")
    return f"media-source://tts/{engine}?message={encoded}"


def _build_media(
    message: str | None,
    audio_url: str | None,
    tts_engine: str | None,
    options: dict,
) -> tuple[str, str]:
    """Resolve the media_content_id / media_content_type to play (no chime)."""
    if audio_url:
        return audio_url, "music"
    return _build_tts_media(message, tts_engine, options), "music"


def _chime_path(chime: str | None) -> str | None:
    """Return the absolute filesystem path of a bundled chime, or None."""
    if not chime or chime == CHIME_NONE:
        return None
    entry = CHIMES.get(chime)
    if not entry:
        _LOGGER.warning("Unknown chime '%s'", chime)
        return None
    path = os.path.join(os.path.dirname(__file__), "www", "chimes", entry[0])
    return path if os.path.exists(path) else None


def _coordinator_volume(volume, coordinator: str) -> int | None:
    if volume is None:
        return None
    if isinstance(volume, dict):
        value = volume.get(coordinator)
        return int(value) if value is not None else None
    return int(volume)


def _write_bytes(path: str, data: bytes) -> None:
    with open(path, "wb") as file:
        file.write(data)


async def _set_volumes(hass: HomeAssistant, targets: list[str], volume) -> None:
    for entity_id in targets:
        value = volume.get(entity_id) if isinstance(volume, dict) else volume
        if value is None:
            continue
        await hass.services.async_call(
            "media_player",
            "volume_set",
            {"entity_id": entity_id, "volume_level": max(0, min(100, int(value))) / 100},
            blocking=True,
        )


async def _wait_until_idle(hass: HomeAssistant, entity_id: str) -> None:
    waited = 0.0
    step = 0.5
    await asyncio.sleep(1.0)
    while waited < MAX_WAIT_SECONDS:
        state = hass.states.get(entity_id)
        if state is None or state.state != "playing":
            return
        await asyncio.sleep(step)
        waited += step


async def _resolve_main_audio(
    hass: HomeAssistant,
    options: dict,
    message: str | None,
    audio_url: str | None,
    tts_engine: str | None,
) -> str:
    """Return a local filesystem path to the main audio (TTS or recording)."""
    storage_rel = options.get(CONF_STORAGE_DIR, DEFAULT_STORAGE_DIR)
    out_dir = hass.config.path(storage_rel)
    await hass.async_add_executor_job(partial(os.makedirs, out_dir, exist_ok=True))

    if message:
        from homeassistant.components.tts import async_get_media_source_audio

        media_id = _build_tts_media(message, tts_engine, options)
        extension, data = await async_get_media_source_audio(hass, media_id)
        path = os.path.join(out_dir, f"_tts_{int(time.time() * 1000)}.{extension}")
        await hass.async_add_executor_job(_write_bytes, path, data)
        return path

    # Recording / local file: map a /local/... URL back to the filesystem.
    marker = "/local/"
    if audio_url and marker in audio_url:
        rel = audio_url.split(marker, 1)[1]
        return hass.config.path("www", *rel.split("/"))

    raise HomeAssistantError(
        "Cannot combine a chime with an external audio_url; only local "
        "recordings (served under /local/) are supported."
    )


async def _ffmpeg_concat(first: str, second: str, dst: str) -> bool:
    """Concatenate two audio files into a single MP3."""
    try:
        proc = await asyncio.create_subprocess_exec(
            "ffmpeg", "-y", "-i", first, "-i", second,
            "-filter_complex", "[0:a][1:a]concat=n=2:v=0:a=1",
            "-codec:a", "libmp3lame", "-qscale:a", "4", dst,
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.PIPE,
        )
    except FileNotFoundError:
        _LOGGER.error("ffmpeg not found on the system PATH")
        return False
    _, stderr = await proc.communicate()
    if proc.returncode != 0:
        _LOGGER.error("ffmpeg concat failed: %s", stderr.decode(errors="ignore")[-400:])
        return False
    return True


async def _combine_chime(
    hass: HomeAssistant, options: dict, chime_path: str, main_path: str
) -> str:
    """Combine chime + main audio into one MP3 and return its local URL."""
    storage_rel = options.get(CONF_STORAGE_DIR, DEFAULT_STORAGE_DIR)
    out_dir = hass.config.path(storage_rel)
    await hass.async_add_executor_job(partial(os.makedirs, out_dir, exist_ok=True))
    fname = f"chime_{int(time.time() * 1000)}.mp3"
    dst = os.path.join(out_dir, fname)

    if not await _ffmpeg_concat(chime_path, main_path, dst):
        raise HomeAssistantError("Failed to combine chime with the message audio.")

    rel = storage_rel.replace("\\", "/")
    if not rel.startswith("www"):
        raise HomeAssistantError(
            "Storage dir must be under www/ for chime playback to be reachable."
        )
    local_path = f"/local/{rel[len('www'):].strip('/')}/{fname}".replace("//", "/")
    return build_local_url(hass, local_path)


async def _resolve_media(
    hass: HomeAssistant,
    options: dict,
    *,
    message: str | None,
    audio_url: str | None,
    tts_engine: str | None,
    chime: str | None,
) -> tuple[str, str]:
    """Resolve the final media to play, combining a chime if requested."""
    chime_path = _chime_path(chime)
    has_main = bool(message or audio_url)

    if chime_path and has_main:
        main_path = await _resolve_main_audio(
            hass, options, message, audio_url, tts_engine
        )
        url = await _combine_chime(hass, options, chime_path, main_path)
        return url, "music"

    if chime_path and not has_main:
        entry = CHIMES[chime]
        return build_local_url(hass, f"{CHIME_URL_BASE}/{entry[0]}"), "music"

    if has_main:
        return _build_media(message, audio_url, tts_engine, options)

    raise HomeAssistantError("Provide 'message', 'audio_url' or 'chime'.")


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
    chime: str | None = None,
) -> None:
    """Play a TTS message and/or chime/clip on one or more Sonos speakers."""
    if not targets:
        raise HomeAssistantError("No target speakers provided.")

    media_content_id, media_content_type = await _resolve_media(
        hass,
        options,
        message=message,
        audio_url=audio_url,
        tts_engine=tts_engine,
        chime=chime,
    )

    coordinator = targets[0]
    members = targets[1:]
    group = sync and len(targets) > 1
    use_snapshot = not announce

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

    except Exception as err:  # noqa: BLE001
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
