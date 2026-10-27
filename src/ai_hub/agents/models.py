"""Agent data models."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class AgentStatus(str, Enum):
    IDLE = "idle"
    RUNNING = "running"
    DONE = "done"
    ERROR = "error"


@dataclass
class AgentConfig:
    agent_id: str
    name: str
    description: str = ""
    system_prompt: str = "You are a helpful assistant."
    model: str | None = None
    tools: list[str] = field(default_factory=list)
    permissions: list[str] = field(default_factory=list)
    token_limit: int | None = None
    max_steps: int = 5
    version: int = 1
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class ActionRecord:
    step: int
    action: str
    tool: str | None
    result: str
    status: str = "ok"


@dataclass
class AgentRunResult:
    agent_id: str
    status: AgentStatus
    final_text: str = ""
    steps: list[ActionRecord] = field(default_factory=list)
    error: str | None = None
    tokens_used: int = 0
