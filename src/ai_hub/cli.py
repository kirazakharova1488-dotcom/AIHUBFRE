
"""AI HUB CLI — terminal interface."""

from __future__ import annotations

import asyncio
import shlex
import time
from pathlib import Path
import sqlite3

import typer
from rich.align import Align
from rich.markdown import Markdown
from rich.panel import Panel
from rich.text import Text

from ai_hub import __version__
from ai_hub.agents.manager import AgentManager
from ai_hub.agents.runtime import AgentRuntime
from ai_hub.config import get_db_path, get_data_dir, settings
from ai_hub.core.orchestrator import ChatResult, Orchestrator
from ai_hub.extensions.manager import ExtensionManager
from ai_hub.providers.registry import build_registry
from ai_hub.model_manager import (
    delete_model as _delete_local_model,
    format_bytes as _format_model_bytes,
    list_models as _list_local_models,
    pull_model as _pull_local_model,
)
from ai_hub.storage.database import get_connection, migrate
from ai_hub.storage.repositories import (
    ConversationRepository,
    ExtensionRepository,
    UsageRepository,
)
from ai_hub.utils.console import (
    console,
    error,
    header,
    info,
    ok,
    prompt,
    status_bar,
    table,
    warn,
)

app = typer.Typer(
    name="aihub",
    help="AI HUB — local AI and agent platform.",
    no_args_is_help=True,
)


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

def _get_orchestrator() -> Orchestrator:
    return Orchestrator(settings)


def _get_registry():
    return build_registry(settings)


def _get_extensions() -> ExtensionManager:
    return ExtensionManager()


def _init_db() -> None:
    migrate()


def _get_db():
    migrate()
    return get_connection()


def _get_agents() -> AgentManager:
    return AgentManager(_get_db())


# ---------------------------------------------------------------------------
# Branding and startup
# ---------------------------------------------------------------------------

def _show_logo() -> None:
    logo = r"""
     █████╗ ██╗    ██╗    ██╗  ██╗██╗   ██╗██████╗
    ██╔══██╗██║    ██║    ██║  ██║██║   ██║██╔══██╗
    ███████║██║ █╗ ██║    ███████║██║   ██║██████╔╝
    ██╔══██║██║███╗██║    ██╔══██║██║   ██║██╔══██╗
    ██║  ██║╚███╔███╔╝    ██║  ██║╚██████╔╝██████╔╝
    ╚═╝  ╚═╝ ╚══╝╚══╝     ╚═╝  ╚═╝ ╚═════╝ ╚═════╝
    """
    brand = Text(logo, style="bold bright_cyan")
    brand.append("\nUNIVERSAL AI & AGENT PLATFORM", style="bold white")
    brand.append("\nLOCAL INTELLIGENCE  •  MULTI-MODEL", style="dim cyan")

    console.print()
    console.print(
        Panel(
            Align.center(brand),
            title="[bold bright_cyan]AI HUB[/bold bright_cyan]",
            subtitle=f"[dim]TERMINAL EDITION v{__version__}[/dim]",
            border_style="white",
            padding=(1, 2),
            expand=False,
        ),
        justify="center",
    )


def _startup_screen():
    """Initialize services and show a real animated startup indicator."""
    registry = _get_registry()
    orchestrator = _get_orchestrator()
    extensions = _get_extensions()
    agents = _get_agents()

    with console.status(
        "[bold bright_cyan]➤ LOADING AI HUB[/bold bright_cyan]\n"
        "[dim]Checking providers, models and local resources...[/dim]",
        spinner="dots",
        spinner_style="bright_cyan",
    ):
        healths = asyncio.run(registry.health_all())
        agent_count = len(agents.list())
        extension_repo = ExtensionRepository(get_connection())
        extension_count = len(extension_repo.list())

    online_count = sum(1 for health in healths.values() if health.online)
    model_count = sum(len(health.models or []) for health in healths.values())

    console.print(
        Panel(
            "[bold green]✔ SYSTEM READY[/bold green]\n"
            "[dim]Startup checks completed.[/dim]",
            border_style="green",
            padding=(0, 2),
            expand=False,
        )
    )
    status_bar(
        model_count,
        online_count,
        agent_count,
        extension_count,
        mode="LOCAL / FREE",
    )
    return registry, orchestrator, extensions, agents


# ---------------------------------------------------------------------------
# Interactive chat
# ---------------------------------------------------------------------------

def _run_interactive(
    model: str | None = None,
    agent: str | None = None,
) -> None:
    """Launch the AI HUB terminal chat."""
    _init_db()
    console.clear()
    _show_logo()

    try:
        _, orchestrator, extensions, agents = _startup_screen()
    except Exception as exc:
        error(f"AI HUB startup failed: {exc}")
        raise typer.Exit(code=1) from exc

    conn = get_connection()
    conv_repo = ConversationRepository(conn)
    usage_repo = UsageRepository(conn)
    conv_id = conv_repo.create(title=f"chat-{int(time.time())}")

    console.print(
        "\n[dim]Commands:[/dim] "
        "[bright_cyan]/help[/bright_cyan]  "
        "[bright_cyan]/models[/bright_cyan]  "
        "[bright_cyan]/clear[/bright_cyan]  "
        "[bright_cyan]/exit[/bright_cyan]\n"
    )

    active_model = model
    active_agent = agent

    while True:
        try:
            user_input = prompt()
        except (EOFError, KeyboardInterrupt):
            console.print("\n[bold green]AI HUB stopped. Goodbye![/bold green]")
            break

        user_input = user_input.strip()
        if not user_input:
            continue

        # Slash commands
        if user_input.startswith("/"):
            try:
                parts = shlex.split(user_input)
            except ValueError as exc:
                warn(f"Invalid command syntax: {exc}")
                continue

            if not parts:
                continue

            cmd, args = parts[0].lower(), parts[1:]

            if cmd in ("/exit", "/quit"):
                console.print("[bold green]AI HUB stopped. Goodbye![/bold green]")
                break
            elif cmd == "/help":
                _print_help()
            elif cmd == "/models":
                _cmd_models_list()
            elif cmd == "/providers":
                _cmd_providers_list()
            elif cmd == "/agents":
                _cmd_agents_list()
            elif cmd == "/extensions":
                _cmd_extensions_list()
            elif cmd == "/settings":
                _cmd_settings()
            elif cmd == "/limits":
                _cmd_limits_show()
            elif cmd == "/usage":
                _cmd_usage()
            elif cmd == "/history":
                history = conv_repo.history(conv_id)
                rows = [
                    [
                        item["role"],
                        item["content"][:70],
                        item["model"] or "-",
                    ]
                    for item in history
                ]
                table(
                    rows,
                    ["role", "content", "model"],
                    title="Conversation History",
                )
            elif cmd == "/clear":
                console.clear()
                _show_logo()
                console.print(
                    "[dim]Type /help for commands or /exit to quit.[/dim]\n"
                )
            elif cmd == "/reset":
                conv_id = conv_repo.create(
                    title=f"chat-{int(time.time())}"
                )
                ok("Started a new conversation.")
            elif cmd == "/use" and args:
                active_model = args[0]
                ok(f"Model override set to {active_model}")
            elif cmd == "/agent" and args:
                active_agent = args[0]
                ok(f"Agent set to {active_agent}")
            else:
                warn(f"Unknown command: {cmd}. Type /help.")
            continue

        # Save user message
        conv_repo.add_message(
            conv_id,
            "user",
            user_input,
            model=active_model,
        )

        # Handle supported natural-language actions
        intent = _detect_intent(user_input)
        if intent:
            response_text = _handle_intent(
                intent,
                user_input,
                extensions,
                agents,
            )
            console.print(
                Panel(
                    response_text,
                    title="[bold yellow]AI HUB SYSTEM[/bold yellow]",
                    border_style="yellow",
                    expand=False,
                )
            )
            conv_repo.add_message(
                conv_id,
                "assistant",
                response_text,
                model="system",
            )
            continue

        # Run the model with a spinner
        with console.status(
            "[bold bright_cyan]➤ AI HUB THINKING[/bold bright_cyan]\n"
            "[dim]Generating response...[/dim]",
            spinner="dots",
            spinner_style="bright_cyan",
        ):
            try:
                if active_agent:
                    agent_config = None
                    for cfg in agents.list():
                        if cfg.name == active_agent:
                            agent_config = cfg
                            break
                    # ?????? ?? ?????? ??????? ? ?????????? ????? (????) ? Windows
                    if not agent_config and agents.list():
                        agent_config = agents.list()[0]
                    if agent_config:
                        runtime = AgentRuntime(manager=agents, orchestrator=orchestrator)
                        run_result = asyncio.run(runtime.run(agent_config, user_input))
                        result = ChatResult(
                            text=run_result.final_text,
                            model=agent_config.model,
                            provider="AgentRuntime",
                        )
                    else:
                        raise ValueError(f"Agent '{active_agent}' not found configuration.")
                else:
                    result = asyncio.run(
                        orchestrator.process(
                            user_input,
                            agent_name=None,
                            model_override=active_model,
                        )
                    )
            except Exception as exc:  # noqa: BLE001
                result = ChatResult(
                    text=f"Request failed: {exc}",
                    model=active_model or "-",
                    provider="-",
                )

        console.print(
            f"[dim]Provider:[/dim] [cyan]{result.provider}[/cyan]  "
            f"[dim]Model:[/dim] [bright_cyan]{result.model}[/bright_cyan]"
        )
        console.print(
            Panel(
                Markdown(result.text),
                title="[bold bright_cyan]AI HUB RESPONSE[/bold bright_cyan]",
                border_style="bright_cyan",
                padding=(1, 2),
                expand=False,
            )
        )

        conv_repo.add_message(
            conv_id,
            "assistant",
            result.text,
            model=result.model,
        )

        try:
            usage_repo.record(
                active_model or result.model or "unknown",
                0,
                0,
            )
        except Exception:  # noqa: BLE001
            pass


# ---------------------------------------------------------------------------
# Help and listing functions
# ---------------------------------------------------------------------------

def _print_help() -> None:
    header("Commands", "AI HUB CLI")
    table(
        [
            ["/help", "show this help"],
            ["/models", "list available providers and models"],
            ["/providers", "list providers"],
            ["/agents", "list agents"],
            ["/extensions", "list extensions"],
            ["/use MODEL", "select a model override"],
            ["/agent NAME", "select an agent"],
            ["/limits", "show token limits"],
            ["/usage", "show token usage"],
            ["/history", "show current conversation history"],
            ["/reset", "start a new conversation"],
            ["/clear", "clear the screen"],
            ["/exit", "quit AI HUB"],
        ],
        ["COMMAND", "DESCRIPTION"],
        title="AI HUB COMMAND CENTER",
    )


def _cmd_models_list() -> None:
    registry = _get_registry()

    async def run_health():
        return await registry.health_all()

    healths = asyncio.run(run_health())
    rows = [
        [
            name,
            health.display_name,
            "ONLINE" if health.online else "OFFLINE",
            str(len(health.models or [])),
            health.error or "-",
        ]
        for name, health in healths.items()
    ]
    table(
        rows,
        ["provider", "display name", "status", "models", "details"],
        title="Models / Providers",
    )


def _cmd_providers_list() -> None:
    _cmd_models_list()


def _cmd_agents_list() -> None:
    manager = _get_agents()
    rows = [
        [
            item.name,
            item.model or "default",
            str(item.token_limit or "-"),
            str(item.max_steps),
        ]
        for item in manager.list()
    ]
    table(
        rows,
        ["name", "model", "token limit", "max steps"],
        title="AI Agents",
    )


def _cmd_extensions_list() -> None:
    manager = _get_extensions()
    rows = [
        [
            item["id"],
            item["name"],
            item["type"],
            str(item["version"]),
            "ON" if item["enabled"] else "OFF",
        ]
        for item in manager.list()
    ]
    table(
        rows,
        ["id", "name", "type", "version", "enabled"],
        title="Extensions",
    )


def _cmd_settings() -> None:
    settings_cmd()


def _cmd_limits_show() -> None:
    console.print(
        f"[dim]Output token limit:[/dim] "
        f"[bright_cyan]{settings.default_output_token_limit}[/bright_cyan]"
    )
    console.print(
        f"[dim]Context token limit:[/dim] "
        f"[bright_cyan]{settings.default_context_token_limit}[/bright_cyan]"
    )


def _cmd_usage() -> None:
    conn = _get_db()
    repo = UsageRepository(conn)
    totals = repo.totals()
    table(
        [[
            str(totals["in"]),
            str(totals["out"]),
            str(totals["in"] + totals["out"]),
        ]],
        ["input tokens", "output tokens", "total tokens"],
        title="Token Usage",
    )


# ---------------------------------------------------------------------------
# Typer CLI commands
# ---------------------------------------------------------------------------

@app.command(name="models-local")
def models_local() -> None:
    """List locally installed Ollama models and their sizes."""
    try:
        items = _list_local_models()
    except RuntimeError as exc:
        error(str(exc))
        raise typer.Exit(code=1) from exc

    if not items:
        info("No local models installed. Install one with: aihub models-install qwen2.5:7b")
        return

    rows = [
        [
            item.get("name", "-"),
            _format_model_bytes(item.get("size", 0)),
            item.get("modified_at", "-"),
        ]
        for item in items
    ]
    table(rows, ["MODEL", "SIZE", "LAST MODIFIED"], title="LOCAL MODEL LIBRARY")


@app.command(name="models-install")
def models_install(
    model: str = typer.Argument(..., help="Ollama model name, e.g. qwen2.5:7b"),
) -> None:
    """Download a model from the Ollama library."""
    try:
        _pull_local_model(model)
    except (RuntimeError, ValueError) as exc:
        error(str(exc))
        raise typer.Exit(code=1) from exc


@app.command(name="models-remove")
def models_remove(
    model: str = typer.Argument(..., help="Name of the installed model"),
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip the confirmation prompt"),
) -> None:
    """Remove an installed local model."""
    try:
        installed = _list_local_models()
    except RuntimeError as exc:
        error(str(exc))
        raise typer.Exit(code=1) from exc

    match = next(
        (item for item in installed if item.get("name") == model),
        None,
    )
    if match is None:
        error(f"Model not found: {model}")
        raise typer.Exit(code=1)

    if not yes and not typer.confirm(
        f"Delete {model} ({_format_model_bytes(match.get('size', 0))})?",
        default=False,
    ):
        info("Deletion cancelled.")
        raise typer.Exit()

    try:
        _delete_local_model(model)
        ok(f"Removed local model: {model}")
    except (RuntimeError, ValueError) as exc:
        error(str(exc))
        raise typer.Exit(code=1) from exc


@app.command(name="models")
def models() -> None:
    """List available models and providers."""
    _cmd_models_list()


@app.command(name="providers")
def providers() -> None:
    """List configured providers."""
    _cmd_providers_list()


@app.command(name="agents")
def agents() -> None:
    """List configured agents."""
    _cmd_agents_list()


@app.command(name="extensions")
def extensions() -> None:
    """List configured extensions."""
    _cmd_extensions_list()


@app.command(name="limits")
def limits() -> None:
    """Show token limits."""
    _cmd_limits_show()


@app.command(name="usage")
def usage() -> None:
    """Show token usage statistics."""
    _cmd_usage()


@app.command(name="settings")
def settings_cmd() -> None:
    """Show current settings."""
    rows = [
        ["ollama_host", settings.ollama_host],
        ["ollama_timeout", str(settings.ollama_timeout)],
        ["openai_base_url", settings.openai_base_url or "-"],
        ["gemini_api_key", "***" if settings.gemini_api_key else "-"],
        ["groq_api_key", "***" if settings.groq_api_key else "-"],
        ["openrouter_api_key", "***" if settings.openrouter_api_key else "-"],
        [
            "default_output_token_limit",
            str(settings.default_output_token_limit),
        ],
        [
            "default_context_token_limit",
            str(settings.default_context_token_limit),
        ],
        ["sandbox_enabled", str(settings.sandbox_enabled)],
        ["network_access_allowed", str(settings.network_access_allowed)],
    ]
    table(rows, ["setting", "value"], title="AI HUB Settings")


@app.command(name="history")
def history_cmd() -> None:
    """List saved conversations."""
    conn = _get_db()
    repo = ConversationRepository(conn)
    conversations = repo.list_conversations()
    rows = [
        [
            str(item["id"]),
            item["title"] or "-",
            str(item["updated_at"]),
        ]
        for item in conversations
    ]
    table(
        rows,
        ["id", "title", "updated"],
        title="Conversation History",
    )


@app.command(name="memory")
def memory_cmd() -> None:
    """Show settings and memory-related configuration."""
    settings_cmd()


@app.command(name="backup")
def backup_cmd() -> None:
    """Create a database backup."""
    db_path = get_db_path()
    backup_path = get_data_dir() / f"ai_hub_backup_{int(time.time())}.db"

    source = sqlite3.connect(str(db_path))
    destination = sqlite3.connect(str(backup_path))
    try:
        source.backup(destination)
    finally:
        destination.close()
        source.close()

    ok(f"Backup saved to {backup_path}")


@app.command(name="restore")
def restore_cmd(
    path: Path = typer.Argument(..., help="Path to a backup .db file"),
) -> None:
    """Restore the database from a backup file."""
    if not path.is_file():
        error(f"Backup file not found: {path}")
        raise typer.Exit(code=1)

    db_path = get_db_path()
    destination = sqlite3.connect(str(db_path))
    source = sqlite3.connect(str(path))
    try:
        source.backup(destination)
    finally:
        destination.close()
        source.close()

    ok(f"Database restored from {path}")


@app.command(name="chat")
def chat(
    model: str | None = typer.Option(
        None,
        "--model",
        "-m",
        help="Model override to use",
    ),
    agent: str | None = typer.Option(
        None,
        "--agent",
        "-a",
        help="Agent to use",
    ),
) -> None:
    """Start the interactive AI HUB chat."""
    _run_interactive(model=model, agent=agent)


# ---------------------------------------------------------------------------
# Natural-language intent helpers
# ---------------------------------------------------------------------------

def _detect_intent(user_input: str) -> dict | None:
    text = user_input.lower()

    if any(
        phrase in text
        for phrase in ("создай агента", "создать агента", "create agent")
    ):
        return {"type": "create_agent", "text": user_input}

    if any(
        phrase in text
        for phrase in (
            "покажи расширения",
            "покажи агентов",
            "list extensions",
            "list agents",
        )
    ):
        return {"type": "list_resources", "text": user_input}

    if any(
        phrase in text
        for phrase in (
            "добавь расширение",
            "создай расширение",
            "create extension",
            "add extension",
        )
    ):
        return {"type": "create_extension", "text": user_input}

    if (
        any(word in text for word in ("лимит", "limit", "токен", "token"))
        and any(word in text for word in ("установи", "set", "задай"))
    ):
        return {"type": "set_limit", "text": user_input}

    return None


def _handle_intent(
    intent: dict,
    text: str,
    extensions: ExtensionManager,
    agents: AgentManager,
) -> str:
    kind = intent["type"]

    if kind == "create_agent":
        name = _guess_name(text) or "new-agent"
        try:
            config = agents.create(
                name=name,
                description="Created via chat",
                model=None,
            )
            return f"Created agent {config.name} ({config.agent_id})."
        except Exception as exc:  # noqa: BLE001
            return f"Could not create agent: {exc}"

    if kind == "create_extension":
        return (
            "Extension generation is not implemented yet. "
            "Use /extensions to inspect installed extensions."
        )

    if kind == "set_limit":
        return (
            "Changing token limits from chat is not implemented yet. "
            "Use the settings/configuration workflow."
        )

    if kind == "list_resources":
        return (
            f"Agents: {len(agents.list())}, "
            f"Extensions: {len(extensions.list())}"
        )

    return "This action is recognized but not implemented yet."


def _guess_name(text: str) -> str | None:
    lowered = text.lower()
    for marker in ("создай агента", "создать агента", "агента", "агент", "agent"):
        index = lowered.find(marker)
        if index >= 0:
            remainder = text[index + len(marker):].strip(" ,.:-")
            words = remainder.split()
            if words:
                return words[0]
    return None


from ai_hub.models_recommend import show_recommendations as _show_model_recommendations


@app.command("models-recommend")
def models_recommend() -> None:
    """Analyze hardware and recommend local AI models."""
    _show_model_recommendations()
