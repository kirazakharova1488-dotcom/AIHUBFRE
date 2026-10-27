"""Groq API provider adapter (OpenAI-compatible endpoint)."""

from __future__ import annotations

from ai_hub.config import Settings
from ai_hub.providers.base import ProviderInfo
from ai_hub.providers.openai_compatible import OpenAICompatibleProvider


class GroqProvider(OpenAICompatibleProvider):
    def __init__(self, settings: Settings) -> None:
        super().__init__(
            settings=settings,
            name="groq",
            display_name="Groq",
            kind="groq",
            base_url="https://api.groq.com/openai/v1",
            api_key=settings.groq_api_key,
        )

    async def health(self) -> ProviderInfo:
        info = await super().health()
        info.name = self.name
        info.display_name = self.display_name
        info.kind = self.kind
        return info