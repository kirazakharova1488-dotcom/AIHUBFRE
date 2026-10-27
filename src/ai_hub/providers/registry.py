"""Provider registry: loads providers, tracks health, exposes model catalog."""

from __future__ import annotations

from dataclasses import dataclass, field

from ai_hub.config import Settings
from ai_hub.providers.base import BaseProvider, ProviderInfo
from ai_hub.providers.gemini import GeminiProvider
from ai_hub.providers.groq import GroqProvider
from ai_hub.providers.openai_compatible import OpenAICompatibleProvider
from ai_hub.providers.ollama import OllamaProvider
from ai_hub.providers.openrouter import OpenRouterProvider


@dataclass
class RegisteredProvider:
    name: str
    provider: BaseProvider


class ProviderRegistry:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self._providers: dict[str, BaseProvider] = {}
        self._register_defaults()

    def _register_defaults(self) -> None:
        self._providers["ollama"] = OllamaProvider(self.settings)
        self._providers["openai"] = OpenAICompatibleProvider(self.settings)
        self._providers["gemini"] = GeminiProvider(self.settings)
        self._providers["groq"] = GroqProvider(self.settings)
        self._providers["openrouter"] = OpenRouterProvider(self.settings)

    def get(self, name: str) -> BaseProvider | None:
        return self._providers.get(name)

    def all(self) -> dict[str, BaseProvider]:
        return dict(self._providers)

    def register(self, name: str, provider: BaseProvider) -> None:
        self._providers[name] = provider

    def unregister(self, name: str) -> bool:
        return self._providers.pop(name, None) is not None

    async def health_all(self) -> dict[str, ProviderInfo]:
        results: dict[str, ProviderInfo] = {}
        for name, provider in self._providers.items():
            try:
                results[name] = await provider.health()
            except Exception as exc:
                results[name] = ProviderInfo(
                    name=name,
                    display_name=provider.display_name,
                    kind=provider.kind,
                    error=str(exc),
                )
        return results

    async def list_all_models(self) -> list[str]:
        models: list[str] = []
        for provider in self._providers.values():
            try:
                models.extend(await provider.list_models())
            except Exception:
                pass
        return models


def build_registry(settings: Settings) -> ProviderRegistry:
    return ProviderRegistry(settings)
