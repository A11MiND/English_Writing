from __future__ import annotations

from app.core.config import Settings
from app.services.llm import LLMGenerationResponse, LLMUsage
from app.services.paragraph_coach import (
    analyse_paragraph_with_cache,
    fallback_paragraph_suggestions,
    paragraph_cache_key,
)


class FakeRedis:
    def __init__(self) -> None:
        self.values: dict[str, str] = {}

    async def get(self, key: str) -> str | None:
        return self.values.get(key)

    async def setex(self, key: str, _ttl: int, value: str) -> bool:
        self.values[key] = value
        return True

    async def aclose(self) -> None:
        return None


class FakeParagraphAdapter:
    calls = 0

    async def generate_json(self, request) -> LLMGenerationResponse:
        self.calls += 1
        system_prompt = request.messages[0].content
        assert "relationships across sentences" in system_prompt
        assert "Do not report spelling" in system_prompt
        payload = {
            "suggestions": [
                {
                    "focus": "LINKING",
                    "title": "Connect the middle idea",
                    "message": "The second event arrives suddenly after the first one.",
                    "evidence": "I opened the door. The dog ran away.",
                    "action": "Add a phrase such as ‘A moment later’ before the second event.",
                }
            ]
        }
        return LLMGenerationResponse(
            provider="minimax",
            model="MiniMax-M3",
            content="{}",
            json_data=payload,
            usage=LLMUsage(input_tokens=40, output_tokens=70, total_tokens=110),
            raw_metadata={},
        )


async def test_paragraph_coach_uses_separate_ai_analysis_and_cache() -> None:
    redis = FakeRedis()
    adapter = FakeParagraphAdapter()
    text = "I opened the door. The dog ran away. I called my brother for help."

    first = await analyse_paragraph_with_cache(
        text,
        adapter=adapter,
        redis_client=redis,
        settings=Settings(grammar_cache_ttl_seconds=60),
    )
    second = await analyse_paragraph_with_cache(
        text,
        adapter=adapter,
        redis_client=redis,
        settings=Settings(grammar_cache_ttl_seconds=60),
    )

    assert first.service_status == "ok"
    assert first.suggestions[0].level == "PARAGRAPH"
    assert first.suggestions[0].focus == "LINKING"
    assert first.total_tokens == 110
    assert second.cached is True
    assert adapter.calls == 1
    assert paragraph_cache_key(text) in redis.values


async def test_paragraph_coach_fallback_detects_cross_sentence_repetition() -> None:
    text = "My dog is friendly. My dog likes food. My dog sleeps near me."

    suggestions = fallback_paragraph_suggestions(text)

    assert len(suggestions) == 1
    assert suggestions[0].level == "PARAGRAPH"
    assert suggestions[0].focus == "REPETITION"
    assert "sentence openings" in suggestions[0].title.lower()


async def test_paragraph_coach_fallback_is_available_without_ai_provider() -> None:
    result = await analyse_paragraph_with_cache(
        "I saw a bird. It flew away. I walked home.",
        adapter=None,
        redis_client=FakeRedis(),
        settings=Settings(grammar_cache_ttl_seconds=60),
    )

    assert result.service_status == "fallback"
    assert result.suggestions[0].level == "PARAGRAPH"
