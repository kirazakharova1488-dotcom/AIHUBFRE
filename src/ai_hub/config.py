"""Application configuration (Pydantic settings)."""

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "AI HUB CLI"
    app_version: str = "0.1.0"
    data_dir: Path = Path.home() / ".ai_hub"
    db_path: Path | None = None
    log_level: str = "INFO"

    workspace_dir: Path = Path("workspace")

    ollama_host: str = "http://localhost:11434"
    ollama_timeout: int = 60
    ollama_preferred_models: str = "qwen2.5:7b,gemma3:latest"
    ollama_auto_fallback: bool = True
    openai_base_url: str | None = None
    openai_api_key: str | None = None
    gemini_api_key: str | None = None
    groq_api_key: str | None = None
    openrouter_api_key: str | None = None

    default_output_token_limit: int = 2000
    default_context_token_limit: int = 8000
    default_dialog_budget: int | None = None

    sandbox_enabled: bool = True
    sandbox_timeout: int = 30
    sandbox_max_memory_mb: int = 256
    network_access_allowed: bool = False

    max_extensions: int = 50
    max_agents: int = 20
    agent_recursion_limit: int = 3


settings = Settings()


def get_data_dir() -> Path:
    data_dir = settings.data_dir
    data_dir.mkdir(parents=True, exist_ok=True)
    return data_dir


def get_db_path() -> Path:
    if settings.db_path is not None:
        return settings.db_path
    return get_data_dir() / "ai_hub.db"


def get_workspace_dir() -> Path:
    workspace = settings.workspace_dir.expanduser()

    if not workspace.is_absolute():
        workspace = Path.cwd() / workspace

    workspace.mkdir(parents=True, exist_ok=True)
    return workspace.resolve()
