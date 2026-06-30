from __future__ import annotations

import hashlib
import json
from typing import Literal, Protocol

import httpx
from pydantic import BaseModel, Field
from redis.asyncio import Redis

from app.core.config import Settings, get_settings

GRAMMAR_RULE_CONFIG_VERSION = "2026-06-phase5-v2"


class GrammarServiceError(Exception):
    pass


class NormalizedSuggestion(BaseModel):
    id: str
    rule_id: str
    category: str
    message: str
    short_message: str
    offset: int = Field(ge=0)
    length: int = Field(ge=1)
    replacements: list[str]
    severity: Literal["INFO", "WARNING", "ERROR"] = "WARNING"


class GrammarAdapter(Protocol):
    async def check(self, text: str, language: str = "en-US") -> list[NormalizedSuggestion]:
        ...


def normalized_cache_key(text: str, language: str) -> str:
    normalized = text.replace("\r\n", "\n").replace("\r", "\n").strip().lower()
    digest = hashlib.sha256(normalized.encode("utf-8")).hexdigest()
    return f"grammar:{language}:{GRAMMAR_RULE_CONFIG_VERSION}:{digest}"


class LanguageToolGrammarAdapter:
    def __init__(self, base_url: str, timeout_seconds: float = 5.0) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout_seconds = timeout_seconds

    async def check(self, text: str, language: str = "en-US") -> list[NormalizedSuggestion]:
        try:
            async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
                response = await client.post(
                    f"{self.base_url}/v2/check",
                    data={"text": text, "language": language},
                    headers={"accept": "application/json"},
                )
            response.raise_for_status()
            payload = response.json()
        except Exception as exc:
            raise GrammarServiceError("Grammar service unavailable.") from exc

        suggestions: list[NormalizedSuggestion] = []
        for index, match in enumerate(payload.get("matches", [])):
            rule = match.get("rule") or {}
            category = rule.get("category") or {}
            replacements = [
                str(replacement.get("value"))
                for replacement in match.get("replacements", [])[:5]
                if replacement.get("value")
            ]
            offset = int(match.get("offset", 0))
            length = int(match.get("length", 1))
            rule_id = str(rule.get("id") or f"LANGUAGETOOL_{index}")
            suggestions.append(
                NormalizedSuggestion(
                    id=f"{rule_id}:{offset}:{offset + length}",
                    rule_id=rule_id,
                    category=str(category.get("id") or "GRAMMAR"),
                    message=str(match.get("message") or "Grammar suggestion."),
                    short_message=str(match.get("shortMessage") or "Suggestion"),
                    offset=offset,
                    length=max(1, length),
                    replacements=replacements,
                )
            )
        return suggestions


def get_grammar_adapter(settings: Settings | None = None) -> GrammarAdapter:
    settings = settings or get_settings()
    provider = settings.grammar_provider.strip().lower()
    if provider in {"languagetool", "language_tool"}:
        if not settings.grammar_service_url:
            raise GrammarServiceError("GRAMMAR_SERVICE_URL is required for LanguageTool.")
        return LanguageToolGrammarAdapter(settings.grammar_service_url)
    raise GrammarServiceError(f"Unsupported grammar provider: {settings.grammar_provider}")


async def check_grammar_with_cache(
    text: str,
    *,
    language: str = "en-US",
    redis_client: Redis | None = None,
    adapter: GrammarAdapter | None = None,
    settings: Settings | None = None,
) -> tuple[list[NormalizedSuggestion], bool, str]:
    settings = settings or get_settings()
    adapter = adapter or get_grammar_adapter(settings)
    cache_key = normalized_cache_key(text, language)
    owns_redis = redis_client is None
    redis = redis_client or Redis.from_url(settings.redis_url, encoding="utf-8", decode_responses=True)

    try:
        cached = await redis.get(cache_key)
        if cached:
            data = json.loads(cached)
            return [NormalizedSuggestion.model_validate(item) for item in data], True, "ok"
    except Exception:
        cached = None

    try:
        suggestions = await adapter.check(text, language)
        service_status = "ok"
    except GrammarServiceError:
        suggestions = []
        service_status = "unavailable"

    try:
        await redis.setex(
            cache_key,
            settings.grammar_cache_ttl_seconds,
            json.dumps([suggestion.model_dump() for suggestion in suggestions]),
        )
    except Exception:
        pass
    finally:
        if owns_redis:
            await redis.aclose()

    return suggestions, False, service_status
