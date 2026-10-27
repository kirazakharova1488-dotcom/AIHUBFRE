"""Integration-style tests for providers and storage."""

from __future__ import annotations

import pytest

from ai_hub.config import Settings
from ai_hub.providers.base import ChatRequest, ChatResponse
from ai_hub.providers.groq import GroqProvider
from ai_hub.providers.openai_compatible import OpenAICompatibleProvider
from ai_hub.providers.openrouter import OpenRouterProvider
from ai_hub.providers.registry import ProviderRegistry
from ai_hub.storage.database import migrate
from ai_hub.storage.database import get_connection as _gc
from ai_hub.storage.repositories import AgentRepository, ConversationRepository, UsageRepository


def _settings(tmp_path) -> Settings:
    return Settings(_env_file=None, _env_file_encoding=None, data_dir=tmp_path, db_path=tmp_path / "ai_hub.db")  # type: ignore[arg-type]


def test_registry_builds_providers(tmp_path) -> None:
    reg = ProviderRegistry(_settings(tmp_path))
    assert set(reg.all()) >= {"ollama", "openai", "gemini", "groq", "openrouter"}


def test_agent_repository_roundtrip(tmp_path) -> None:
    conn = _gc(tmp_path / "ai_hub.db")
    migrate(conn)
    ar = AgentRepository(conn)
    ar.create(agent_id="agent_1", name="CODER", description="", system_prompt="code",
              model="llama3", permissions="", token_limit=2000, max_steps=5)
    assert ar.get("agent_1") is not None
    conn.close()


def test_conversation_repository_history(tmp_path) -> None:
    conn = _gc(tmp_path / "ai_hub.db")
    migrate(conn)
    cr = ConversationRepository(conn)
    cid = cr.create("test")
    cr.add_message(cid, "user", "hello", model="m")
    cr.add_message(cid, "assistant", "hi", model="m")
    history = cr.history(cid)
    assert len(history) == 2
    conn.close()


def test_openai_compatible_provider_health_offline(tmp_path) -> None:
    import asyncio
    provider = OpenAICompatibleProvider(_settings(tmp_path))
    resp = asyncio.run(provider.health())
    assert resp.error is not None  # no API key -> offline


def test_groq_provider_present(tmp_path) -> None:
    provider = GroqProvider(_settings(tmp_path))
    assert provider.name == "groq"
    assert provider.base_url == "https://api.groq.com/openai/v1"


def test_openrouter_provider_present(tmp_path) -> None:
    provider = OpenRouterProvider(_settings(tmp_path))
    assert provider.name == "openrouter"


def test_chat_response_shape() -> None:
    r = ChatResponse(text="answer", input_tokens=3, output_tokens=4, model="m")
    assert r.text == "answer"
    req = ChatRequest(model="m", messages=[{"role": "user", "content": "hi"}], max_tokens=10)
    assert req.max_tokens == 10
