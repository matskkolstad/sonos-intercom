"""Chime discovery and resolution (bundled + user-uploaded custom chimes).

Bundled chimes ship inside the integration and are served from the static path
(``/sonos_intercom_static/chimes``). Custom chimes live under a user folder
(``custom_chime_dir``, default ``www/sonos_intercom_chimes``) which must be under
``www/`` so Sonos can fetch them over ``/local/``.
"""
from __future__ import annotations

import os
from functools import partial

from homeassistant.core import HomeAssistant
from homeassistant.helpers.dispatcher import async_dispatcher_send

from .const import (
    CHIME_NONE,
    CHIME_URL_BASE,
    CHIMES,
    CONF_CUSTOM_CHIME_DIR,
    DATA_CHIMES,
    DEFAULT_CUSTOM_CHIME_DIR,
    DOMAIN,
    SIGNAL_UPDATE,
)


def _pretty_label(stem: str) -> str:
    """Turn a filename stem into a human label."""
    label = stem.replace("_", " ").replace("-", " ").strip()
    return label[:1].upper() + label[1:] if label else stem


def custom_chime_dir(hass: HomeAssistant, options: dict) -> str:
    """Absolute filesystem path of the custom chime folder."""
    rel = options.get(CONF_CUSTOM_CHIME_DIR, DEFAULT_CUSTOM_CHIME_DIR)
    return hass.config.path(rel)


def custom_chime_url_base(options: dict) -> str | None:
    """Relative ``/local/...`` URL base for custom chimes, or None if unreachable."""
    rel = options.get(CONF_CUSTOM_CHIME_DIR, DEFAULT_CUSTOM_CHIME_DIR).replace("\\", "/")
    if not rel.startswith("www"):
        return None
    return f"/local/{rel[len('www'):].strip('/')}".replace("//", "/")


def _scan_custom(out_dir: str) -> list[str]:
    """Return sorted .mp3 filenames in out_dir (sync; run in executor)."""
    if not os.path.isdir(out_dir):
        return []
    return sorted(
        name
        for name in os.listdir(out_dir)
        if name.lower().endswith(".mp3") and os.path.isfile(os.path.join(out_dir, name))
    )


def list_bundled() -> list[dict]:
    """List the bundled chimes as serializable dicts."""
    return [
        {"id": cid, "label": entry[1], "custom": False, "url": f"{CHIME_URL_BASE}/{entry[0]}"}
        for cid, entry in CHIMES.items()
    ]


async def async_list_chimes(hass: HomeAssistant, options: dict) -> list[dict]:
    """List all available chimes (bundled + custom) as serializable dicts."""
    chimes = list_bundled()
    files = await hass.async_add_executor_job(_scan_custom, custom_chime_dir(hass, options))
    url_base = custom_chime_url_base(options)
    for filename in files:
        stem = os.path.splitext(filename)[0]
        if stem in CHIMES:
            continue  # bundled ids win
        chimes.append(
            {
                "id": stem,
                "label": _pretty_label(stem),
                "custom": True,
                "url": f"{url_base}/{filename}" if url_base else "",
            }
        )
    return chimes


def resolve_chime(
    hass: HomeAssistant, options: dict, chime_id: str | None
) -> tuple[str, str] | tuple[None, None]:
    """Return (filesystem_path, relative_url) for a chime id, or (None, None)."""
    if not chime_id or chime_id == CHIME_NONE:
        return None, None

    entry = CHIMES.get(chime_id)
    if entry:
        path = os.path.join(os.path.dirname(__file__), "www", "chimes", entry[0])
        return (path, f"{CHIME_URL_BASE}/{entry[0]}") if os.path.exists(path) else (None, None)

    # Custom chime: look for "<id>.mp3" in the custom folder.
    filename = f"{chime_id}.mp3"
    path = os.path.join(custom_chime_dir(hass, options), filename)
    if os.path.exists(path):
        url_base = custom_chime_url_base(options)
        return path, (f"{url_base}/{filename}" if url_base else "")
    return None, None


async def async_make_custom_dir(hass: HomeAssistant, options: dict) -> str:
    """Ensure the custom chime folder exists and return its path."""
    out_dir = custom_chime_dir(hass, options)
    await hass.async_add_executor_job(partial(os.makedirs, out_dir, exist_ok=True))
    return out_dir


async def async_refresh_chimes(hass: HomeAssistant, options: dict) -> list[dict]:
    """Recompute the available chimes, cache them, and notify listeners."""
    chimes = await async_list_chimes(hass, options)
    hass.data.setdefault(DOMAIN, {})[DATA_CHIMES] = chimes
    async_dispatcher_send(hass, SIGNAL_UPDATE)
    return chimes
