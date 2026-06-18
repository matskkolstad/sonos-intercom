"""HTTP endpoint that receives a browser recording and converts it to MP3."""
from __future__ import annotations

import asyncio
import base64
import logging
import os
import time
from functools import partial

from homeassistant.components.http import HomeAssistantView

from .announce import build_local_url
from .const import CONF_STORAGE_DIR, DEFAULT_STORAGE_DIR, DOMAIN

_LOGGER = logging.getLogger(__name__)


def _write_bytes(path: str, data: bytes) -> None:
    with open(path, "wb") as file:
        file.write(data)


def _safe_remove(path: str) -> None:
    try:
        os.remove(path)
    except OSError:
        pass


async def _ffmpeg_to_mp3(src: str, dst: str) -> bool:
    """Convert the source recording to MP3 using ffmpeg."""
    try:
        proc = await asyncio.create_subprocess_exec(
            "ffmpeg",
            "-y",
            "-i",
            src,
            "-codec:a",
            "libmp3lame",
            "-qscale:a",
            "4",
            dst,
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.PIPE,
        )
    except FileNotFoundError:
        _LOGGER.error("ffmpeg not found on the system PATH")
        return False

    _, stderr = await proc.communicate()
    if proc.returncode != 0:
        _LOGGER.error("ffmpeg failed: %s", stderr.decode(errors="ignore")[-500:])
        return False
    return True


class IntercomUploadView(HomeAssistantView):
    """Receive a base64-encoded recording, convert to MP3, return a URL."""

    url = "/api/sonos_intercom/upload"
    name = "api:sonos_intercom:upload"
    requires_auth = True

    async def post(self, request):
        """Handle the upload."""
        hass = request.app["hass"]

        try:
            body = await request.json()
        except ValueError:
            return self.json_message("Invalid JSON body", 400)

        audio_b64 = body.get("audio")
        fmt = body.get("format", "webm")
        if not audio_b64:
            return self.json_message("Missing 'audio' field", 400)

        try:
            raw = base64.b64decode(audio_b64)
        except (ValueError, TypeError):
            return self.json_message("Invalid base64 audio", 400)

        options = next(
            (
                opts
                for key, opts in hass.data.get(DOMAIN, {}).items()
                if not str(key).startswith("_")
            ),
            {},
        )
        storage_rel = options.get(CONF_STORAGE_DIR, DEFAULT_STORAGE_DIR)
        out_dir = hass.config.path(storage_rel)
        await hass.async_add_executor_job(partial(os.makedirs, out_dir, exist_ok=True))

        stamp = int(time.time() * 1000)
        fname = f"intercom_{stamp}.mp3"
        src = os.path.join(out_dir, f"_tmp_{stamp}.{fmt}")
        dst = os.path.join(out_dir, fname)

        await hass.async_add_executor_job(_write_bytes, src, raw)
        ok = await _ffmpeg_to_mp3(src, dst)
        await hass.async_add_executor_job(_safe_remove, src)

        if not ok:
            return self.json_message("Audio conversion failed", 500)

        # Build a URL Sonos can fetch locally.
        if storage_rel.replace("\\", "/").startswith("www"):
            rel = storage_rel.replace("\\", "/")[len("www"):].strip("/")
            local_path = f"/local/{rel}/{fname}".replace("//", "/")
            url = build_local_url(hass, local_path)
        else:
            # Stored outside www/ - not directly reachable; return the file path.
            url = ""
            _LOGGER.warning(
                "Storage dir '%s' is not under www/; recording is not reachable "
                "by Sonos over HTTP.",
                storage_rel,
            )

        return self.json({"url": url, "filename": fname})
