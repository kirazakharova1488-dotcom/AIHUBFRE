"""OpenRouter API provider adapter (OpenAI-compatible endpoint)."""

from __future__ import annotations

from ai_hub.config import Settings
from ai_hub.providers.base import ChatRequest, ChatResponse, ProviderInfo
from ai_hub.providers.openai_compatible import OpenAICompatibleProvider


class OpenRouterProvider(OpenAICompatibleProvider):
    def __init__(self, settings: Settings) -> None:
        super().__init__(
            settings=settings,
            name="openrouter",
            display_name="OpenRouter",
            kind="openrouter",
            base_url="https://openrouter.ai/api/v1",
            api_key=settings.openrouter_api_key,
        )

    async def health(self) -> ProviderInfo:
        info = await super().health()
        info.name = self.name
        info.display_name = self.display_name
        info.kind = self.kind
        return info