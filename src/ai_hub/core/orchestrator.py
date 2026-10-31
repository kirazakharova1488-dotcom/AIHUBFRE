"""Central orchestrator with sequential workspace tool execution."""

from __future__ import annotations

import json
from dataclasses import dataclass
from json import JSONDecoder
from typing import Any

from ai_hub.config import Settings
from ai_hub.core.permissions import Permissions
from ai_hub.core.router import Router
from ai_hub.core.token_manager import TokenManager, TokenBudget
from ai_hub.providers.base import ChatRequest
from ai_hub.tools.developer import DeveloperTools


@dataclass
class ChatResult:
    text: str
    model: str
    provider: str
    tokens_in: int = 0
    tokens_out: int = 0


TOOL_INSTRUCTIONS = """
You are AI HUB, an autonomous development assistant.

You can create, read, edit and run files inside the workspace.

Available tools:

list_files:
{"tool":"list_files","arguments":{"path":"."}}

read_file:
{"tool":"read_file","arguments":{"path":"relative/path"}}

write_file:
{"tool":"write_file","arguments":{"path":"relative/path","content":"complete file content"}}

edit_file:
{"tool":"edit_file","arguments":{"path":"relative/path","old_text":"old text","new_text":"new text"}}

create_directory:
{"tool":"create_directory","arguments":{"path":"relative/path"}}

run_python:
{"tool":"run_python","arguments":{"path":"relative/script.py"}}

run_tests:
{"tool":"run_tests","arguments":{"path":"."}}

install_dependencies:
{"tool":"install_dependencies","arguments":{"path":"requirements.txt"}}

IMPORTANT:
- When a task requires tools, return JSON tool calls, not descriptions.
- You may return several JSON tool objects in one response.
- Each tool call must be a separate JSON object.
- Do not claim that an operation succeeded until you receive its actual result.
- After receiving tool results, continue the task.
- Finish with a normal text summary.
- All paths must be relative to workspace.
"""


AVAILABLE_TOOLS = {
    "list_files",
    "read_file",
    "write_file",
    "edit_file",
    "create_directory",
    "run_python",
    "run_tests",
    "install_dependencies",
}


def parse_tool_calls(text: str) -> list[dict[str, Any]]:
    """Extract one or more JSON tool calls from a model response."""

    if not text:
        return []

    decoder = JSONDecoder()
    found: list[dict[str, Any]] = []
    index = 0

    while index < len(text):
        start = text.find("{", index)

        if start == -1:
            break

        try:
            data, end = decoder.raw_decode(text, start)
        except json.JSONDecodeError:
            index = start + 1
            continue

        index = end

        if not isinstance(data, dict):
            continue

        tool_name = data.get("tool")
        arguments = data.get("arguments", {})

        if tool_name not in AVAILABLE_TOOLS:
            continue

        if not isinstance(arguments, dict):
            continue

        found.append({
            "tool": tool_name,
            "arguments": arguments,
        })

    return found


def parse_tool_call(text: str) -> dict[str, Any] | None:
    """Backward-compatible parser returning the first tool call."""

    calls = parse_tool_calls(text)
    return calls[0] if calls else None


OLLAMA_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "list_files",
            "description": "List files in workspace.",
            "parameters": {
                "type": "object",
                "properties": {"path": {"type": "string"}},
                "required": ["path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "Read a workspace file.",
            "parameters": {
                "type": "object",
                "properties": {"path": {"type": "string"}},
                "required": ["path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "write_file",
            "description": "Write a file in workspace.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string"},
                    "content": {"type": "string"},
                },
                "required": ["path", "content"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "edit_file",
            "description": "Edit a workspace file.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string"},
                    "old_text": {"type": "string"},
                    "new_text": {"type": "string"},
                },
                "required": ["path", "old_text", "new_text"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "create_directory",
            "description": "Create a workspace directory.",
            "parameters": {
                "type": "object",
                "properties": {"path": {"type": "string"}},
                "required": ["path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "run_python",
            "description": "Run a Python file in workspace.",
            "parameters": {
                "type": "object",
                "properties": {"path": {"type": "string"}},
                "required": ["path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "run_tests",
            "description": "Run workspace tests.",
            "parameters": {
                "type": "object",
                "properties": {"path": {"type": "string"}},
                "required": ["path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "install_dependencies",
            "description": "Install dependencies from a requirements file.",
            "parameters": {
                "type": "object",
                "properties": {"path": {"type": "string"}},
                "required": ["path"],
            },
        },
    },
]


class Orchestrator:
    def __init__(self, settings: Settings, registry=None) -> None:
        self.settings = settings
        self.registry = registry
        self.token_manager = TokenManager.from_settings(settings)
        self.router = Router(settings, self.token_manager)
        self.permissions = Permissions()
        self.developer_tools = DeveloperTools()
        self.max_tool_calls = 8

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

        candidates: list[tuple[str, str]] = []

        if model:
            candidates.append((provider_name, model))

        fallback_enabled = (
            not model_override
            and bool(getattr(self.settings, "ollama_auto_fallback", True))
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
                installed = set(
                    getattr(ollama, "_last_models", []) or []
                )

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
                text="[error]No usable model found.[/error]",
                model="-",
                provider=provider_name,
            )

        budget: TokenBudget = self.token_manager.apply_to_request()
        errors: list[str] = []

        for candidate_provider_name, candidate_model in candidates:
            provider = registry.get(candidate_provider_name)

            if provider is None:
                continue

            system_prompt = TOOL_INSTRUCTIONS

            if agent_name:
                system_prompt += f"\nCurrent agent: {agent_name}"

            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": message},
            ]

            total_input_tokens = 0
            total_output_tokens = 0
            tool_calls_executed = 0

            try:
                response = await provider.chat(
                    ChatRequest(
                        model=candidate_model,
                        messages=messages,
                        max_tokens=budget.output_tokens,
                        extra=(
                            {"tools": OLLAMA_TOOLS}
                            if candidate_provider_name == "ollama"
                            else {}
                        ),
                    )
                )

                total_input_tokens += response.input_tokens
                total_output_tokens += response.output_tokens

                while True:
                    calls = parse_tool_calls(response.text)

                    if not calls:
                        break

                    remaining = self.max_tool_calls - tool_calls_executed

                    if remaining <= 0:
                        response.text = (
                            "Остановлено: достигнут лимит инструментов. "
                            "Последний ответ модели:\n" + response.text
                        )
                        break

                    calls = calls[:remaining]

                    messages.append({
                        "role": "assistant",
                        "content": response.text,
                    })

                    results = []

                    for call in calls:
                        tool_calls_executed += 1

                        tool_name = call["tool"]
                        arguments = call["arguments"]

                        result = self.developer_tools.execute(
                            tool_name,
                            arguments,
                        )

                        results.append(
                            f"Tool: {tool_name}\n"
                            f"Arguments: {json.dumps(arguments, ensure_ascii=False)}\n"
                            f"Actual result:\n{result}"
                        )

                    messages.append({
                        "role": "user",
                        "content": (
                            "The following tools were executed. "
                            "These are their actual results:\n\n"
                            + "\n\n---\n\n".join(results)
                            + "\n\nContinue the task. If more actions are "
                            "needed, return JSON tool calls. Otherwise give "
                            "a final answer based only on actual results."
                        ),
                    })

                    response = await provider.chat(
                        ChatRequest(
                            model=candidate_model,
                            messages=messages,
                            max_tokens=budget.output_tokens,
                            extra=(
                                {"tools": OLLAMA_TOOLS}
                                if candidate_provider_name == "ollama"
                                else {}
                            ),
                        )
                    )

                    total_input_tokens += response.input_tokens
                    total_output_tokens += response.output_tokens

                self.token_manager.record(
                    input_tokens=total_input_tokens,
                    output_tokens=total_output_tokens,
                    context_limit=budget.context_tokens,
                    model=response.model or candidate_model,
                )

                return ChatResult(
                    text=response.text,
                    model=response.model or candidate_model,
                    provider=candidate_provider_name,
                    tokens_in=total_input_tokens,
                    tokens_out=total_output_tokens,
                )

            except Exception as exc:
                errors.append(
                    f"{candidate_provider_name}/{candidate_model}: {exc}"
                )

        details = " | ".join(errors) or "No candidate could be used."

        return ChatResult(
            text=f"[error]All model attempts failed: {details}[/error]",
            model="-",
            provider=provider_name,
        )
