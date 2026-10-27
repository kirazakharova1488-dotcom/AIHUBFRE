
"""Central orchestrator: wires providers, storage, agents, extensions, chat loop."""

from __future__ import annotations

from dataclasses import dataclass

from ai_hub.config import Settings
from ai_hub.core.permissions import Permissions
from ai_hub.core.router import Router
from ai_hub.core.token_manager import TokenManager, TokenBudget
from ai_hub.providers.base import ChatRequest


@dataclass
class ChatResult:
    text: str
    model: str
    provider: str
    tokens_in: int = 0
    tokens_out: int = 0


class Orchestrator:
    def __init__(self, settings: Settings, registry=None) -> None:
        self.settings = settings
        self.registry = registry
        self.token_manager = TokenManager.from_settings(settings)
        self.router = Router(settings, self.token_manager)
        self.permissions = Permissions()

    async def process(
        self,
        message: str,
        agent_name: str | None = None,
        model_override: str | None = None,
    ) -> ChatResult:
        registry = self.registry
        if registry is None:
            from ai_hub.providers.registry import build_registry

            registry = build_registry(self.settings)
            self.registry = registry

        healths = await registry.health_all()
        providers = []

        for name, info in healths.items():
            provider = registry.get(name)
            if provider is None:
                continue

            # Cache model lists for the router.
            provider._last_models = list(info.models or [])

            if info.online:
                providers.append((name, provider))

        if not providers:
            details = "; ".join(
                f"{name}: {info.error or 'offline'}"
                for name, info in healths.items()
            )
            return ChatResult(
                text=f"[error]No providers available. {details}[/error]",
                model="-",
                provider="-",
            )

        provider_name, model = self.router.choose(
            providers,
            task_hint=message,
            model_override=model_override,
        )

        if provider_name is None:
            return ChatResult(
                text="[error]Requested provider is unavailable.[/error]",
                model=model or "-",
                provider="-",
            )

        # Build a finite candidate list. Never retry the same model.
        candidates: list[tuple[str, str]] = []
        if model:
            candidates.append((provider_name, model))

        # Explicit user selection must not silently change to another model.
        if model_override:
            fallback_enabled = False
        else:
            fallback_enabled = bool(
                getattr(self.settings, "ollama_auto_fallback", True)
            )

        if fallback_enabled:
            ollama = registry.get("ollama")
            if ollama is not None and any(
                name == "ollama" for name, _ in providers
            ):
                preferred = getattr(
                    self.settings,
                    "ollama_preferred_models",
                    "qwen2.5:7b,gemma3:latest",
                )
                installed = set(getattr(ollama, "_last_models", []) or [])

                for candidate_model in (
                    item.strip() for item in preferred.split(",")
                ):
                    candidate = ("ollama", candidate_model)
                    if (
                        candidate_model
                        and candidate_model in installed
                        and candidate not in candidates
                    ):
                        candidates.append(candidate)

        if not candidates:
            return ChatResult(
                text="[error]No usable model found. Check installed models and provider settings.[/error]",
                model="-",
                provider=provider_name,
            )

        budget: TokenBudget = self.token_manager.apply_to_request()
        errors: list[str] = []

        for candidate_provider_name, candidate_model in candidates:
            provider = registry.get(candidate_provider_name)
            if provider is None:
                continue

            request = ChatRequest(
                model=candidate_model,
                messages=[{"role": "user", "content": message}],
                max_tokens=budget.output_tokens,
            )

            try:
                response = await provider.chat(request)
            except Exception as exc:
                errors.append(
                    f"{candidate_provider_name}/{candidate_model}: {exc}"
                )
                continue

            self.token_manager.record(
                input_tokens=response.input_tokens,
                output_tokens=response.output_tokens,
                context_limit=budget.context_tokens,
                model=response.model or candidate_model,
            )

            return ChatResult(
                text=response.text,
                model=response.model or candidate_model,
                provider=candidate_provider_name,
                tokens_in=response.input_tokens,
                tokens_out=response.output_tokens,
            )

        error_details = " | ".join(errors) or "No candidate could be used."
        return ChatResult(
            text=f"[error]All model attempts failed: {error_details}[/error]",
            model="-",
            provider=provider_name,
        )
