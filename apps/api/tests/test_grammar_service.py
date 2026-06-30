from __future__ import annotations

import re

from app.core.config import Settings
from app.services.grammar import (
    NormalizedSuggestion,
    check_grammar_with_cache,
    normalized_cache_key,
)


class FakeRedis:
    def __init__(self) -> None:
        self.values: dict[str, str] = {}
        self.ttl: dict[str, int] = {}
        self.closed = False

    async def get(self, key: str) -> str | None:
        return self.values.get(key)

    async def setex(self, key: str, ttl: int, value: str) -> bool:
        self.values[key] = value
        self.ttl[key] = ttl
        return True

    async def aclose(self) -> None:
        self.closed = True


class RuleBasedTestGrammarAdapter:
    patterns = [
        (
            re.compile(r"\bteh\b", re.IGNORECASE),
            "MORFOLOGIK_RULE_EN_US",
            "TYPOS",
            "Possible spelling mistake.",
            "Spelling",
            ["the"],
        ),
        (
            re.compile(r"\bdont\b", re.IGNORECASE),
            "EN_CONTRACTION_DONT",
            "GRAMMAR",
            "Use an apostrophe in this contraction.",
            "Contraction",
            ["don't"],
        ),
        (
            re.compile(r" {2,}"),
            "EN_DOUBLE_SPACE",
            "TYPOGRAPHY",
            "Use a single space.",
            "Spacing",
            [" "],
        ),
        (
            re.compile(r"\bi\b"),
            "UPPERCASE_I",
            "CASING",
            "The pronoun I should be capitalised.",
            "Capitalisation",
            ["I"],
        ),
    ]

    async def check(self, text: str, language: str = "en-US") -> list[NormalizedSuggestion]:
        suggestions: list[NormalizedSuggestion] = []
        for pattern, rule_id, category, message, short_message, replacements in self.patterns:
            for match in pattern.finditer(text):
                suggestions.append(
                    NormalizedSuggestion(
                        id=f"{rule_id}:{match.start()}:{match.end()}",
                        rule_id=rule_id,
                        category=category,
                        message=message,
                        short_message=short_message,
                        offset=match.start(),
                        length=match.end() - match.start(),
                        replacements=replacements,
                    )
                )
        return sorted(suggestions, key=lambda suggestion: (suggestion.offset, suggestion.rule_id))


async def test_test_grammar_adapter_returns_normalized_spans() -> None:
    suggestions = await RuleBasedTestGrammarAdapter().check("i dont like teh  mistake.")

    assert [suggestion.rule_id for suggestion in suggestions] == [
        "UPPERCASE_I",
        "EN_CONTRACTION_DONT",
        "MORFOLOGIK_RULE_EN_US",
        "EN_DOUBLE_SPACE",
    ]
    spelling = suggestions[2]
    assert spelling.offset == 12
    assert spelling.length == 3
    assert spelling.replacements == ["the"]


async def test_grammar_cache_avoids_duplicate_adapter_calls() -> None:
    redis = FakeRedis()
    settings = Settings(grammar_cache_ttl_seconds=60)

    first, first_cached, _ = await check_grammar_with_cache(
        "teh mistake",
        redis_client=redis,
        adapter=RuleBasedTestGrammarAdapter(),
        settings=settings,
    )
    second, second_cached, _ = await check_grammar_with_cache(
        "teh mistake",
        redis_client=redis,
        adapter=RuleBasedTestGrammarAdapter(),
        settings=settings,
    )

    assert first_cached is False
    assert second_cached is True
    assert second[0].model_dump() == first[0].model_dump()
    assert normalized_cache_key("teh mistake", "en-US") in redis.values


def test_grammar_cache_key_preserves_internal_spacing() -> None:
    assert normalized_cache_key("the error", "en-US") != normalized_cache_key(
        "the  error",
        "en-US",
    )
