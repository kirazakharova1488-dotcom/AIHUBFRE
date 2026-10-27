
"""Model router: automatic task-based routing across available providers."""

from __future__ import annotations

from ai_hub.config import Settings
from ai_hub.core.token_manager import TokenManager


class Router:
    def __init__(self, settings: Settings, token_manager: TokenManager) -> None:
        self.settings = settings
        self.token_manager = token_manager

    def choose(
        self,
        providers: list[tuple[str, object]],
        task_hint: str = "",
        model_override: str | None = None,
    ) -> tuple[str | None, str | None]:
        """Choose a provider and model, respecting local model preferences."""

        if not providers:
            return None, None

        if model_override and ":" in model_override:
            name, model = model_override.split(":", 1)
            for provider_name, _provider in providers:
                if provider_name == name:
                    return provider_name, model
            return None, None

        # Prefer configured Ollama models, in the order specified in Settings.
        ollama = next(
            ((name, provider) for name, provider in providers if name == "ollama"),
            None,
        )
        if ollama:
            configured = [
                item.strip()
                for item in self.settings.ollama_preferred_models.split(",")
                if item.strip()
            ]
            installed = getattr(ollama[1], "_last_models", []) or []

            for preferred_model in configured:
                if preferred_model in installed:
                    return "ollama", preferred_model

            if installed:
                return "ollama", installed[0]

        # Otherwise preserve the existing provider order.
        name, provider = providers[0]
        models = getattr(provider, "_last_models", []) or []
        return name, models[0] if models else None
