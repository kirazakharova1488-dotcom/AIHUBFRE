"""Google Gemini API provider adapter."""

from __future__ import annotations

import httpx

from ai_hub.config import Settings
from ai_hub.providers.base import BaseProvider, ChatRequest, ChatResponse, ProviderInfo


class GeminiProvider(BaseProvider):
    def __init__(self, settings: Settings) -> None:
        super().__init__(name="gemini", display_name="Google Gemini", kind="gemini", settings=settings)
        self.api_key = settings.gemini_api_key
        self.base_url = "https://generativelanguage.googleapis.com/v1beta"

    async def health(self) -> ProviderInfo:
        if not self.api_key:
            return ProviderInfo(name=self.name, display_name=self.display_name, kind=self.kind,
                                error="API key not configured")
        try:
            async with httpx.AsyncClient(timeout=15) as client:
                response = await client.get(
                    f"{self.base_url}/models?key={self.api_key}",
                )
                if response.status_code == 200:
                    data = response.json()
                    models = [m.get("name", "").replace("models/", "") for m in data.get("models", [])]
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
        contents = [
            {"role": "user" if m["role"] == "user" else "model", "parts": [{"text": m["content"]}]}
            for m in request.messages
        ]
        payload = {
            "contents": contents,
            "generationConfig": {"maxOutputTokens": request.max_tokens, "temperature": request.temperature},
        }
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(
                f"{self.base_url}/models/{request.model}:generateContent?key={self.api_key}",
                json=payload,
            )
            response.raise_for_status()
            data = response.json()
        candidates = data.get("candidates", [{}])
        text = candidates[0].get("content", {}).get("parts", [{}])[0].get("text", "")
        usage = data.get("usageMetadata", {})
        return ChatResponse(
            text=text,
            input_tokens=usage.get("promptTokenCount", 0),
            output_tokens=usage.get("candidatesTokenCount", 0),
            model=data.get("model", request.model),
            raw=data,
        )

    @property
    def timeout(self) -> int:
        return self.settings.ollama_timeout