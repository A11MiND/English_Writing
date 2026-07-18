import base64

import pytest

from app.core.config import Settings
from app.services.minimax_media import MiniMaxMediaClient


class FakeResponse:
    def __init__(self, status_code: int, payload: dict) -> None:
        self.status_code = status_code
        self._payload = payload

    def json(self) -> dict:
        return self._payload


class FakeAsyncClient:
    def __init__(self, responses: list[FakeResponse], calls: list[dict]) -> None:
        self.responses = responses
        self.calls = calls

    async def __aenter__(self) -> "FakeAsyncClient":
        return self

    async def __aexit__(self, *_args) -> None:
        return None

    async def post(self, url: str, *, headers: dict, json: dict) -> FakeResponse:
        self.calls.append({"url": url, "headers": headers, "json": json})
        return self.responses.pop(0)


@pytest.mark.asyncio
async def test_speech_rotates_to_next_key_after_capacity_error(monkeypatch) -> None:
    calls: list[dict] = []
    responses = [
        FakeResponse(429, {}),
        FakeResponse(200, {"base_resp": {"status_code": 0}, "data": {"audio": "494433"}}),
    ]
    monkeypatch.setattr(
        "app.services.minimax_media.httpx.AsyncClient",
        lambda **_kwargs: FakeAsyncClient(responses, calls),
    )
    client = MiniMaxMediaClient(
        Settings(minimax_api_keys="key-one,key-two", minimax_base_url="https://example.test/v1")
    )

    asset = await client.synthesize_speech("A short school story.")

    assert asset.content == b"ID3"
    assert asset.mime_type == "audio/mpeg"
    assert [call["headers"]["Authorization"] for call in calls] == [
        "Bearer key-one",
        "Bearer key-two",
    ]
    assert calls[-1]["json"]["model"] == "speech-2.8-hd"


@pytest.mark.asyncio
async def test_image_decodes_provider_base64(monkeypatch) -> None:
    calls: list[dict] = []
    encoded = base64.b64encode(b"jpeg-bytes").decode()
    responses = [
        FakeResponse(
            200,
            {"base_resp": {"status_code": 0}, "data": {"image_base64": [encoded]}},
        )
    ]
    monkeypatch.setattr(
        "app.services.minimax_media.httpx.AsyncClient",
        lambda **_kwargs: FakeAsyncClient(responses, calls),
    )
    client = MiniMaxMediaClient(Settings(minimax_api_keys="key-one"))

    asset = await client.generate_image("A warm primary school storybook scene")

    assert asset.content == b"jpeg-bytes"
    assert asset.mime_type == "image/jpeg"
    assert calls[0]["json"]["aspect_ratio"] == "16:9"
    assert calls[0]["json"]["aigc_watermark"] is True
