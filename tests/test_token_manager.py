"""Usage tests."""

from __future__ import annotations

from ai_hub.core.token_manager import TokenManager, TokenUsage


def test_token_manager_usage_for_model() -> None:
    tm = TokenManager.__new__(TokenManager)
    tm.settings = None
    tm.usage_log = []
    tm.usage_log.append(TokenUsage(input_tokens=1, output_tokens=2, context_limit=10, model="m1"))
    tm.usage_log.append(TokenUsage(input_tokens=3, output_tokens=4, context_limit=10, model="m2"))
    assert len(tm.usage_for(model="m1")) == 1
    assert len(tm.usage_for()) == 2