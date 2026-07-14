from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.models import AIProviderSetting
from app.services.llm import LLMAdapter, build_llm_adapter, get_provider_preset


@dataclass(frozen=True)
class ResolvedAISettings:
    provider: str
    provider_display_name: str
    model: str
    base_url: str | None
    api_key: str | None
    api_key_configured: bool
    base_url_configured: bool
    timeout_seconds: float
    source: str

    @property
    def configured(self) -> bool:
        return self.api_key_configured and self.base_url_configured

    @property
    def masked_api_key(self) -> str | None:
        if not self.api_key:
            return None
        if len(self.api_key) <= 8:
            return "••••"
        return f"{self.api_key[:4]}••••{self.api_key[-4:]}"


async def get_school_ai_setting(db: AsyncSession, school_id: str | None) -> AIProviderSetting | None:
    if school_id is None:
        return None
    result = await db.execute(
        select(AIProviderSetting).where(AIProviderSetting.school_id == school_id)
    )
    return result.scalar_one_or_none()


async def resolve_ai_settings(db: AsyncSession, school_id: str | None) -> ResolvedAISettings:
    env = get_settings()
    row = await get_school_ai_setting(db, school_id)
    if row is not None:
        preset = get_provider_preset(row.provider)
        model = row.model or preset.default_model
        base_url = row.base_url or preset.base_url
        return ResolvedAISettings(
            provider=preset.id,
            provider_display_name=preset.display_name,
            model=model,
            base_url=base_url,
            api_key=row.api_key_secret,
            api_key_configured=bool(row.api_key_secret),
            base_url_configured=bool(base_url),
            timeout_seconds=float(row.timeout_seconds),
            source="database",
        )

    preset = get_provider_preset(env.llm_provider)
    model = env.llm_model or preset.default_model
    base_url = env.llm_base_url or preset.base_url
    return ResolvedAISettings(
        provider=preset.id,
        provider_display_name=preset.display_name,
        model=model,
        base_url=base_url,
        api_key=env.llm_api_key,
        api_key_configured=bool(env.llm_api_key),
        base_url_configured=bool(base_url),
        timeout_seconds=env.llm_timeout_seconds,
        source="environment",
    )


async def get_school_llm_adapter(db: AsyncSession, school_id: str | None) -> LLMAdapter:
    resolved = await resolve_ai_settings(db, school_id)
    return build_llm_adapter(
        provider=resolved.provider,
        model=resolved.model,
        base_url=resolved.base_url,
        api_key=resolved.api_key,
        timeout_seconds=resolved.timeout_seconds,
    )
