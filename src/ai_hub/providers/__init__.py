"""Base provider interface for all LLM backends."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass
class ProviderInfo:
    name: str
    display_name: str
    kind: str  # ollama | openai | gemini | groq | openrouter | hf
    online: bool = False
    models: list[str] = field(default_factory=list)
    error: str | None = None


@dataclass
class ChatRequest:
    model: str
    messages: list[dict[str, str]]
    max_tokens: int = 2000
    temperature: float = 0.7
    stream: bool = False
    extra: dict[str, Any] = field(default_factory=dict)


@dataclass
class ChatResponse:
    text: str
    input_tokens: int = 0
    output_tokens: int = 0
    model: str = ""
    raw: Any = None


class BaseProvider(ABC):
    """Every provider implements this contract so the kernel never depends on specifics."""

    def __init__(self, name: str, display_name: str, kind: str, settings: Any) -> None:
        self.name = name
        self.display_name = display_name
        self.kind = kind
        self.settings = settings

    @abstractmethod
    async def health(self) -> ProviderInfo:
        ...

    @abstractmethod
    async def list_models(self) -> list[str]:
        ...

    @abstractmethod
    async def chat(self, request: ChatRequest) -> ChatResponse:
        ...

    async def chat_stream(self, request: ChatRequest):
        """Default: yield a single chunk."""
        response = await self.chat(request)
        yield response

    def supports_max_tokens(self) -> bool:
        return True