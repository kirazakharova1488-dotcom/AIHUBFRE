"""Extension manifest schema (Pydantic)."""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field


class ExtensionType(str, Enum):
    TOOL = "tool"
    CLI_COMMAND = "cli_command"
    PROVIDER = "provider"
    FILE_HANDLER = "file_handler"
    MEMORY = "memory"
    WORKFLOW = "workflow"
    CODE_ANALYZER = "code_analyzer"
    API_INTEGRATION = "api_integration"


class ExtensionManifest(BaseModel):
    id: str
    name: str
    type: ExtensionType
    version: str = "1.0.0"
    description: str = ""
    author: str = "ai-hub"
    entrypoint: str | None = None
    permissions: list[str] = Field(default_factory=list)
    network: bool = False
    filesystem: bool = False
    env: list[str] = Field(default_factory=list)
    max_runtime_seconds: int = 30
    max_memory_mb: int = 256
    tests: list[str] = Field(default_factory=list)