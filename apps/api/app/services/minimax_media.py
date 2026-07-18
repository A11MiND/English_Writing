import asyncio
import base64
from dataclasses import dataclass

import httpx

from app.core.config import Settings, get_settings


class MiniMaxMediaError(Exception):
    pass


@dataclass(frozen=True)
class MediaAsset:
    content: bytes
    mime_type: str
    model: str


class MiniMaxMediaClient:
    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()
        self._keys = self.settings.minimax_key_pool
        self._next_key = 0
        self._lock = asyncio.Lock()

    @property
    def configured(self) -> bool:
        return bool(self._keys)

    async def _ordered_keys(self) -> list[str]:
        async with self._lock:
            if not self._keys:
                return []
            start = self._next_key % len(self._keys)
            self._next_key = (start + 1) % len(self._keys)
        return self._keys[start:] + self._keys[:start]

    async def _post(self, path: str, payload: dict) -> dict:
        keys = await self._ordered_keys()
        if not keys:
            raise MiniMaxMediaError("MiniMax media is not configured.")

        last_message = "MiniMax media request failed."
        for key in keys:
            try:
                async with httpx.AsyncClient(timeout=self.settings.minimax_timeout_seconds) as client:
                    response = await client.post(
                        f"{self.settings.minimax_base_url.rstrip('/')}/{path.lstrip('/')}",
                        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
                        json=payload,
                    )
            except httpx.HTTPError:
                last_message = "MiniMax media service is unavailable."
                continue

            if response.status_code in {401, 403, 429}:
                last_message = "MiniMax media capacity is temporarily unavailable."
                continue
            if response.status_code >= 400:
                raise MiniMaxMediaError(f"MiniMax media request failed ({response.status_code}).")

            try:
                body = response.json()
            except ValueError as exc:
                raise MiniMaxMediaError("MiniMax returned an invalid response.") from exc
            base_response = body.get("base_resp") or {}
            provider_code = int(base_response.get("status_code") or 0)
            if provider_code != 0:
                last_message = str(base_response.get("status_msg") or "MiniMax media request failed.")
                if provider_code in {1004, 1008, 1026, 1027, 1039, 1041}:
                    continue
                raise MiniMaxMediaError(last_message)
            return body
        raise MiniMaxMediaError(last_message)

    async def synthesize_speech(self, text: str) -> MediaAsset:
        body = await self._post(
            "t2a_v2",
            {
                "model": self.settings.minimax_speech_model,
                "text": text,
                "stream": False,
                "voice_setting": {
                    "voice_id": self.settings.minimax_speech_voice,
                    "speed": 0.95,
                    "vol": 1.0,
                    "pitch": 0,
                },
                "audio_setting": {"sample_rate": 32000, "bitrate": 128000, "format": "mp3", "channel": 1},
            },
        )
        audio_hex = str((body.get("data") or {}).get("audio") or "")
        if not audio_hex:
            raise MiniMaxMediaError("MiniMax did not return speech audio.")
        try:
            content = bytes.fromhex(audio_hex)
        except ValueError as exc:
            raise MiniMaxMediaError("MiniMax returned invalid speech audio.") from exc
        return MediaAsset(content=content, mime_type="audio/mpeg", model=self.settings.minimax_speech_model)

    async def generate_image(self, prompt: str) -> MediaAsset:
        body = await self._post(
            "image_generation",
            {
                "model": self.settings.minimax_image_model,
                "prompt": prompt,
                "aspect_ratio": "16:9",
                "response_format": "base64",
                "n": 1,
                "prompt_optimizer": True,
                "aigc_watermark": True,
            },
        )
        data = body.get("data") or {}
        images = data.get("image_base64") or data.get("images") or []
        encoded = images[0] if isinstance(images, list) and images else images
        if isinstance(encoded, dict):
            encoded = encoded.get("base64") or encoded.get("image_base64")
        if not isinstance(encoded, str) or not encoded:
            raise MiniMaxMediaError("MiniMax did not return an image.")
        if encoded.startswith("data:"):
            encoded = encoded.split(",", 1)[-1]
        try:
            content = base64.b64decode(encoded, validate=True)
        except ValueError as exc:
            raise MiniMaxMediaError("MiniMax returned invalid image data.") from exc
        return MediaAsset(content=content, mime_type="image/jpeg", model=self.settings.minimax_image_model)
