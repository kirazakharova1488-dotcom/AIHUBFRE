"""Token manager: output/context/dynamic budgets, usage statistics."""

from __future__ import annotations

from dataclasses import dataclass, field

from ai_hub.config import Settings


@dataclass
class TokenUsage:
    input_tokens: int = 0
    output_tokens: int = 0
    context_limit: int = 0
    model: str = ""


@dataclass
class TokenBudget:
    output_tokens: int
    context_tokens: int
    dialog_budget: int | None
    agent_budget: int | None = None

    def to_model_params(self) -> dict[str, int]:
        """Map to provider-supported generation params."""
        params: dict[str, int] = {"max_tokens": self.output_tokens, "max_output_tokens": self.output_tokens}
        return params


class TokenManager:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.usage_log: list[TokenUsage] = []

    @classmethod
    def from_settings(cls, settings: Settings) -> "TokenManager":
        return cls(settings)

    def get_budget(self, agent_budget: int | None = None) -> TokenBudget:
        return TokenBudget(
            output_tokens=agent_budget or self.settings.default_output_token_limit,
            context_tokens=self.settings.default_context_token_limit,
            dialog_budget=self.settings.default_dialog_budget,
            agent_budget=agent_budget,
        )

    def apply_to_request(self, agent_budget: int | None = None) -> TokenBudget:
        return self.get_budget(agent_budget)

    def record(self, input_tokens: int, output_tokens: int, context_limit: int, model: str) -> TokenUsage:
        usage = TokenUsage(
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            context_limit=context_limit,
            model=model,
        )
        self.usage_log.append(usage)
        return usage

    def total_tokens(self) -> int:
        return sum(u.input_tokens + u.output_tokens for u in self.usage_log)

    def usage_for(self, today: bool = False, model: str | None = None) -> list[TokenUsage]:
        filtered = self.usage_log
        if today:
            from datetime import datetime, date

            today_date = date.today()
            filtered = [u for u in filtered if u.context_limit > 0]  # placeholder, refined in storage layer
        if model:
            filtered = [u for u in filtered if u.model == model]
        return filtered


class DialogBudget:
    def __init__(self, total_tokens: int) -> None:
        self.total = total_tokens

    def remaining(self) -> int:
        used = sum(u.output_tokens for u in _dialog_cache)
        return self.total - used

    def consume(self, tokens: int) -> None:
        pass


_dialog_cache: list[TokenUsage] = []
