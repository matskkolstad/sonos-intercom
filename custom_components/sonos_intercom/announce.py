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

Beyond playback this module also: caps/blocks volume during quiet hours, fires
a `sonos_intercom_announced` event, records a small in-memory history (for the
inbox/replay features), and works on non-Sonos media_player targets (Sonos-only
steps like snapshot/restore and grouping are skipped for those).
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
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.dispatcher import async_dispatcher_send
from homeassistant.helpers.network import get_url
from homeassistant.util import dt as dt_util

from .chimes import resolve_chime
from .const import (
    ATTR_ANNOUNCE,
    ATTR_AUDIO_URL,
    ATTR_CHIME,
    ATTR_MESSAGE,
    ATTR_SOURCE,
    ATTR_TARGETS,
    ATTR_VOLUME,
    CONF_DEFAULT_TTS,
    CONF_HISTORY_SIZE,
    CONF_QUIET_END,
    CONF_QUIET_MAX_VOLUME,
    CONF_QUIET_START,
    CONF_RETENTION_HOURS,
    CONF_STORAGE_DIR,
    DATA_HISTORY,
    DATA_LAST,
    DEFAULT_HISTORY_SIZE,
    DEFAULT_QUIET_MAX_VOLUME,
    DEFAULT_RETENTION_HOURS,
    DEFAULT_STORAGE_DIR,
    DOMAIN,
    EVENT_ANNOUNCED,
    SIGNAL_UPDATE,
)

_LOGGER = logging.getLogger(__name__)

MAX_WAIT_SECONDS = 60

# Filename prefixes of files this integration generates under the storage dir.
# Only files matching these are eligible for automatic pruning.
PRUNE_PREFIXES = ("_tts_", "chime_", "intercom_", "_tmp_")


def build_local_url(hass: HomeAssistant, path: str) -> str:
    """Return an absolute URL Sonos can fetch from, given an HA-served path."""
    base = get_url(hass, prefer_external=False, allow_internal=True)
    return f"{base}{path}"


def _build_tts_media(
    message: str,
    tts_engine: str | None,
    options: dict,
    language: str | None = None,
    voice: str | None = None,
) -> str:
    """Build a media-source TTS id for the given message."""
    engine = tts_engine or options.get(CONF_DEFAULT_TTS)
    if not engine:
        raise HomeAssistantError(
            "No TTS engine configured. Set a default TTS engine in the Sonos "
            "Intercom options, or pass 'tts_engine' to the service call."
        )
    query = f"message={urllib.parse.quote(message or '')}"
    if language:
        query += f"&language={urllib.parse.quote(language)}"
    if voice:
        query += f"&voice={urllib.parse.quote(voice)}"
    return f"media-source://tts/{engine}?{query}"


def _build_media(
    message: str | None,
    audio_url: str | None,
    tts_engine: str | None,
    options: dict,
    language: str | None = None,
    voice: str | None = None,
) -> tuple[str, str]:
    """Resolve the media_content_id / media_content_type to play (no chime)."""
    if audio_url:
        return audio_url, "music"
    return _build_tts_media(message, tts_engine, options, language, voice), "music"


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


def _is_sonos(hass: HomeAssistant, entity_id: str) -> bool:
    """Return True if the entity is provided by the Sonos integration."""
    entry = er.async_get(hass).async_get(entity_id)
    return bool(entry and entry.platform == "sonos")


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


# ---------------------------------------------------------------------------
# Quiet hours
# ---------------------------------------------------------------------------
def _parse_hhmm(value) -> int | None:
    """Parse a "HH:MM" string into minutes-since-midnight, or None."""
    try:
        hours, minutes = str(value).split(":")
        hours, minutes = int(hours), int(minutes)
    except (ValueError, AttributeError):
        return None
    if 0 <= hours < 24 and 0 <= minutes < 60:
        return hours * 60 + minutes
    return None


def quiet_active(hass: HomeAssistant, options: dict) -> bool:
    """Return True if quiet hours are currently in effect."""
    start = _parse_hhmm(options.get(CONF_QUIET_START))
    end = _parse_hhmm(options.get(CONF_QUIET_END))
    if start is None or end is None or start == end:
        return False
    now = dt_util.now()
    current = now.hour * 60 + now.minute
    if start < end:
        return start <= current < end
    return current >= start or current < end  # window wraps past midnight


def _apply_quiet(hass: HomeAssistant, options: dict, volume):
    """Cap (or signal skip) the volume for quiet hours. Returns (volume, skip)."""
    if not quiet_active(hass, options):
        return volume, False
    try:
        cap = int(options.get(CONF_QUIET_MAX_VOLUME, DEFAULT_QUIET_MAX_VOLUME))
    except (TypeError, ValueError):
        cap = DEFAULT_QUIET_MAX_VOLUME
    if cap <= 0:
        return volume, True
    if volume is None:
        return cap, False
    if isinstance(volume, dict):
        return {key: min(int(val), cap) for key, val in volume.items()}, False
    return min(int(volume), cap), False


# ---------------------------------------------------------------------------
# Media resolution (TTS / recording / chime combine)
# ---------------------------------------------------------------------------
async def _resolve_main_audio(
    hass: HomeAssistant,
    options: dict,
    message: str | None,
    audio_url: str | None,
    tts_engine: str | None,
    language: str | None = None,
    voice: str | None = None,
) -> str:
    """Return a local filesystem path to the main audio (TTS or recording)."""
    storage_rel = options.get(CONF_STORAGE_DIR, DEFAULT_STORAGE_DIR)
    out_dir = hass.config.path(storage_rel)
    await hass.async_add_executor_job(partial(os.makedirs, out_dir, exist_ok=True))

    if message:
        from homeassistant.components.tts import async_get_media_source_audio

        media_id = _build_tts_media(message, tts_engine, options, language, voice)
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


async def _ffmpeg_concat(
    first: str, second: str, dst: str, first_gain: float | None = None
) -> bool:
    """Concatenate two audio files into a single MP3.

    If ``first_gain`` is given (and not ~1.0), a volume filter is applied to the
    first input only, so the chime can play louder/quieter than the message.
    """
    if first_gain is not None and abs(first_gain - 1.0) > 1e-3:
        filter_complex = f"[0:a]volume={first_gain:.3f}[c];[c][1:a]concat=n=2:v=0:a=1"
    else:
        filter_complex = "[0:a][1:a]concat=n=2:v=0:a=1"
    try:
        proc = await asyncio.create_subprocess_exec(
            "ffmpeg", "-y", "-i", first, "-i", second,
            "-filter_complex", filter_complex,
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


def _chime_gain(chime_volume) -> float | None:
    """Map a 0-100 chime volume to an ffmpeg amplitude gain, or None."""
    if chime_volume is None:
        return None
    try:
        value = max(0, min(100, int(chime_volume)))
    except (TypeError, ValueError):
        return None
    return value / 100.0


async def _combine_chime(
    hass: HomeAssistant,
    options: dict,
    chime_path: str,
    main_path: str,
    chime_volume=None,
) -> str:
    """Combine chime + main audio into one MP3 and return its local URL."""
    storage_rel = options.get(CONF_STORAGE_DIR, DEFAULT_STORAGE_DIR)
    out_dir = hass.config.path(storage_rel)
    await hass.async_add_executor_job(partial(os.makedirs, out_dir, exist_ok=True))
    fname = f"chime_{int(time.time() * 1000)}.mp3"
    dst = os.path.join(out_dir, fname)

    if not await _ffmpeg_concat(
        chime_path, main_path, dst, first_gain=_chime_gain(chime_volume)
    ):
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
    chime_volume=None,
    language: str | None = None,
    voice: str | None = None,
) -> tuple[str, str]:
    """Resolve the final media to play, combining a chime if requested."""
    chime_path, chime_url = resolve_chime(hass, options, chime)
    has_main = bool(message or audio_url)

    if chime_path and has_main:
        main_path = await _resolve_main_audio(
            hass, options, message, audio_url, tts_engine, language, voice
        )
        url = await _combine_chime(
            hass, options, chime_path, main_path, chime_volume=chime_volume
        )
        return url, "music"

    if chime_path and not has_main:
        return build_local_url(hass, chime_url), "music"

    if has_main:
        return _build_media(message, audio_url, tts_engine, options, language, voice)

    raise HomeAssistantError("Provide 'message', 'audio_url' or 'chime'.")


# ---------------------------------------------------------------------------
# Storage cleanup
# ---------------------------------------------------------------------------
def _prune_dir(out_dir: str, max_age_seconds: float) -> None:
    """Delete generated files older than max_age_seconds in out_dir."""
    if not os.path.isdir(out_dir):
        return
    cutoff = time.time() - max_age_seconds
    for name in os.listdir(out_dir):
        if not name.startswith(PRUNE_PREFIXES):
            continue
        path = os.path.join(out_dir, name)
        try:
            if os.path.isfile(path) and os.path.getmtime(path) < cutoff:
                os.remove(path)
        except OSError:
            pass


async def _prune_storage(hass: HomeAssistant, options: dict) -> None:
    """Prune old generated files based on the retention_hours option."""
    try:
        retention = int(options.get(CONF_RETENTION_HOURS, DEFAULT_RETENTION_HOURS))
    except (TypeError, ValueError):
        retention = DEFAULT_RETENTION_HOURS
    if retention <= 0:
        return
    storage_rel = options.get(CONF_STORAGE_DIR, DEFAULT_STORAGE_DIR)
    out_dir = hass.config.path(storage_rel)
    await hass.async_add_executor_job(_prune_dir, out_dir, retention * 3600)


# ---------------------------------------------------------------------------
# History (inbox / replay)
# ---------------------------------------------------------------------------
def _store_last(hass: HomeAssistant, item: dict) -> None:
    """Remember the last announcement so it can be replayed."""
    hass.data.setdefault(DOMAIN, {})[DATA_LAST] = item


def _record_history(hass: HomeAssistant, options: dict, item: dict) -> None:
    """Prepend an item to the in-memory history and notify listeners."""
    try:
        size = int(options.get(CONF_HISTORY_SIZE, DEFAULT_HISTORY_SIZE))
    except (TypeError, ValueError):
        size = DEFAULT_HISTORY_SIZE
    data = hass.data.setdefault(DOMAIN, {})
    history = data.setdefault(DATA_HISTORY, [])
    history.insert(0, item)
    del history[max(size, 0):]
    async_dispatcher_send(hass, SIGNAL_UPDATE)


# ---------------------------------------------------------------------------
# Playback
# ---------------------------------------------------------------------------
async def _play_media(
    hass: HomeAssistant,
    *,
    media_content_id: str,
    media_content_type: str,
    targets: list[str],
    volume=None,
    announce: bool = True,
    sync: bool = True,
) -> None:
    """Play already-resolved media on the targets, with optional sync/ducking.

    Sonos-specific steps (snapshot/restore and join/unjoin grouping) are applied
    only to Sonos entities; non-Sonos media_players just get ``play_media``.
    """
    sonos = [t for t in targets if _is_sonos(hass, t)]
    all_sonos = len(sonos) == len(targets)
    coordinator = targets[0]
    members = targets[1:]
    group = sync and len(targets) > 1 and all_sonos
    use_snapshot = (not announce) and bool(sonos)

    if use_snapshot:
        await hass.services.async_call(
            "sonos", "snapshot", {"entity_id": sonos, "with_group": True}, blocking=True
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
        _LOGGER.error("Sonos Intercom playback failed: %s", err)
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
                    {"entity_id": sonos, "with_group": True},
                    blocking=True,
                )
            except Exception as err:  # noqa: BLE001
                _LOGGER.warning("Could not restore speakers: %s", err)


def _message_kind(message: str | None, audio_url: str | None) -> str:
    if message:
        return "tts"
    if audio_url:
        return "recording"
    return "chime"


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
    chime_volume=None,
    language: str | None = None,
    voice: str | None = None,
    source: str | None = None,
) -> None:
    """Play a TTS message and/or chime/clip on one or more media_players."""
    if not targets:
        raise HomeAssistantError("No target speakers provided.")

    # Quiet hours: cap the volume, or skip entirely if the cap is 0.
    volume, skip = _apply_quiet(hass, options, volume)
    if skip:
        _LOGGER.info("Quiet hours active (max volume 0); skipping announcement")
        return

    # Clean up old generated files before creating new ones.
    await _prune_storage(hass, options)

    media_content_id, media_content_type = await _resolve_media(
        hass,
        options,
        message=message,
        audio_url=audio_url,
        tts_engine=tts_engine,
        chime=chime,
        chime_volume=chime_volume,
        language=language,
        voice=voice,
    )

    item = {
        "time": dt_util.now().isoformat(timespec="seconds"),
        "kind": _message_kind(message, audio_url),
        "message": message,
        "audio_url": audio_url,
        "chime": chime,
        "targets": list(targets),
        "source": source,
        "volume": volume,
        "announce": announce,
        "sync": sync,
        "media_content_id": media_content_id,
        "media_content_type": media_content_type,
    }
    _store_last(hass, item)
    _record_history(hass, options, item)

    hass.bus.async_fire(
        EVENT_ANNOUNCED,
        {
            ATTR_MESSAGE: message,
            ATTR_AUDIO_URL: audio_url,
            ATTR_CHIME: chime,
            ATTR_TARGETS: list(targets),
            ATTR_VOLUME: volume,
            ATTR_SOURCE: source,
            ATTR_ANNOUNCE: announce,
        },
    )

    await _play_media(
        hass,
        media_content_id=media_content_id,
        media_content_type=media_content_type,
        targets=targets,
        volume=volume,
        announce=announce,
        sync=sync,
    )


async def async_replay(
    hass: HomeAssistant,
    *,
    targets: list[str] | None = None,
    volume=None,
    index: int = 0,
) -> None:
    """Replay an announcement from the history (0 = most recent).

    Note: the stored media may have been pruned by automatic storage cleanup
    (recordings/combined chimes are files); pure TTS replays always work since
    they are regenerated from a media-source id.
    """
    data = hass.data.get(DOMAIN, {})
    history = data.get(DATA_HISTORY) or []
    if 0 <= index < len(history):
        item = history[index]
    elif index == 0 and data.get(DATA_LAST):
        item = data[DATA_LAST]
    else:
        raise HomeAssistantError("No announcement at that history position to replay.")

    await _play_media(
        hass,
        media_content_id=item["media_content_id"],
        media_content_type=item["media_content_type"],
        targets=targets or item["targets"],
        volume=volume if volume is not None else item.get("volume"),
        announce=item.get("announce", True),
        sync=item.get("sync", True),
    )


async def async_acknowledge(
    hass: HomeAssistant,
    options: dict,
    *,
    targets: list[str] | None = None,
    message: str | None = None,
    chime: str | None = "soft_ping",
    volume=None,
) -> None:
    """Send a quick acknowledgement back to the last sender (or given targets)."""
    if not targets:
        last = hass.data.get(DOMAIN, {}).get(DATA_LAST)
        targets = list(last["targets"]) if last and last.get("targets") else None
    if not targets:
        raise HomeAssistantError("No targets to acknowledge; nothing to reply to.")

    await async_announce(
        hass,
        options,
        message=message,
        targets=targets,
        volume=volume,
        announce=True,
        chime=chime,
        source="Kvittering",
    )
