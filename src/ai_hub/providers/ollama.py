"""Ollama provider adapter."""

from __future__ import annotations

import httpx

from ai_hub.config import Settings
from ai_hub.providers.base import BaseProvider, ChatRequest, ChatResponse, ProviderInfo


class OllamaProvider(BaseProvider):
    def __init__(self, settings: Settings) -> None:
        super().__init__(name="ollama", display_name="Ollama (local)", kind="ollama", settings=settings)
        self.base_url = settings.ollama_host.rstrip("/")
        self.timeout = settings.ollama_timeout

    async def health(self) -> ProviderInfo:
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(f"{self.base_url}/api/tags")
                if response.status_code == 200:
                    data = response.json()
                    models = [m.get("name", "") for m in data.get("models", [])]
                    return ProviderInfo(
                        name=self.name, display_name=self.display_name, kind=self.kind,
                        online=True, models=models,
                    )
                return ProviderInfo(name=self.name, display_name=self.display_name, kind=self.kind,
                                    error=f"HTTP {response.status_code}")
        except Exception as exc:
            return ProviderInfo(name=self.name, display_name=self.display_name, kind=self.kind,
                                error=str(exc))

    async def list_models(self) -> list[str]:
        info = await self.health()
        return info.models

    async def chat(self, request: ChatRequest) -> ChatResponse:
        payload = {
            "model": request.model,
            "messages": request.messages,
            "stream": False,
            "options": {"num_predict": request.max_tokens, "temperature": request.temperature},
        }
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(f"{self.base_url}/api/chat", json=payload)
            response.raise_for_status()
            data = response.json()
        return ChatResponse(
            text=data.get("message", {}).get("content", ""),
            input_tokens=data.get("prompt_eval_count", 0),
            output_tokens=data.get("eval_count", 0),
            model=data.get("model", request.model),
            raw=data,
        )

    def supports_max_tokens(self) -> bool:
        return True