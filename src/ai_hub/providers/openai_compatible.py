"""OpenAI-compatible API provider (OpenAI, Groq, OpenRouter, llama.cpp server, local APIs)."""

from __future__ import annotations

import httpx

from ai_hub.config import Settings
from ai_hub.providers.base import BaseProvider, ChatRequest, ChatResponse, ProviderInfo


class OpenAICompatibleProvider(BaseProvider):
    def __init__(self, settings: Settings, *, name: str = "openai", display_name: str = "OpenAI-compatible",
                 kind: str = "openai", base_url: str | None = None, api_key: str | None = None) -> None:
        super().__init__(name=name, display_name=display_name, kind=kind, settings=settings)
        self.base_url = (base_url or settings.openai_base_url or "https://api.openai.com").rstrip("/")
        self.api_key = api_key or settings.openai_api_key

    async def health(self) -> ProviderInfo:
        if not self.api_key:
            return ProviderInfo(name=self.name, display_name=self.display_name, kind=self.kind,
                                error="API key not configured")
        try:
            async with httpx.AsyncClient(timeout=15) as client:
                response = await client.get(
                    f"{self.base_url}/v1/models",
                    headers={"Authorization": f"Bearer {self.api_key}"},
                )
                if response.status_code == 200:
                    data = response.json()
                    models = [m.get("id", "") for m in data.get("data", [])]
                    return ProviderInfo(name=self.name, display_name=self.display_name, kind=self.kind,
                                        online=True, models=models)
                return ProviderInfo(name=self.name, display_name=self.display_name, kind=self.kind,
                                    error=f"HTTP {response.status_code}")
        except Exception as exc:
            return ProviderInfo(name=self.name, display_name=self.display_name, kind=self.kind, error=str(exc))

    async def list_models(self) -> list[str]:
        info = await self.health()
        return info.models

    async def chat(self, request: ChatRequest) -> ChatResponse:
        payload = {
            "model": request.model,
            "messages": request.messages,
            "max_tokens": request.max_tokens,
            "temperature": request.temperature,
        }
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(
                f"{self.base_url}/v1/chat/completions",
                json=payload,
                headers={"Authorization": f"Bearer {self.api_key}"},
            )
            response.raise_for_status()
            data = response.json()
        choice = data.get("choices", [{}])[0]
        usage = data.get("usage", {})
        return ChatResponse(
            text=choice.get("message", {}).get("content", ""),
            input_tokens=usage.get("prompt_tokens", 0),
            output_tokens=usage.get("completion_tokens", 0),
            model=data.get("model", request.model),
            raw=data,
        )

    @property
    def timeout(self) -> int:
        return self.settings.ollama_timeout