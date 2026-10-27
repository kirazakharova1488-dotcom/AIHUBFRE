
"""AI HUB — shared terminal UI and Rich console helpers."""

from __future__ import annotations

from rich.align import Align
from rich.box import ROUNDED
from rich.console import Console, Group
from rich.live import Live
from rich.panel import Panel
from rich.spinner import Spinner
from rich.table import Table
from rich.text import Text
from rich.theme import Theme


# ---------------------------------------------------------
# AI HUB theme
# ---------------------------------------------------------

_ai_hub_theme = Theme(
    {
        "primary": "bold bright_cyan",
        "secondary": "bright_magenta",
        "success": "bold bright_green",
        "warning": "bold yellow",
        "error": "bold bright_red",
        "muted": "grey62",
        "model": "bold bright_green",
        "provider": "bold bright_blue",
        "agent": "bold bright_magenta",
        "extension": "bold yellow",
        "status_online": "bold bright_green",
        "status_offline": "bold bright_red",
    }
)

console = Console(theme=_ai_hub_theme)


# ---------------------------------------------------------
# Logo
# ---------------------------------------------------------

_LOGO = r"""
     █████╗ ██╗    ██╗    ██╗  ██╗██╗   ██╗██████╗
    ██╔══██╗██║    ██║    ██║  ██║██║   ██║██╔══██╗
    ███████║██║ █╗ ██║    ███████║██║   ██║██████╔╝
    ██╔══██╗██║███╗██║    ██║  ██║██║   ██║██╔══██╗
    ██║  ██║╚███╔███╔╝    ██║  ██║╚██████╔╝██████╔╝
    ╚═╝  ╚═╝ ╚══╝╚══╝     ╚═╝  ╚═╝ ╚═════╝ ╚═════╝
"""


def header(
    title: str = "AI HUB",
    subtitle: str = "Universal AI & Agent Platform",
) -> None:
    """Display the main AI HUB banner."""
    content = Group(
        Align.center(Text(_LOGO.strip("\n"), style="bold bright_cyan")),
        Align.center(Text(subtitle, style="bold white")),
        Align.center(
            Text("LOCAL INTELLIGENCE  •  MULTI-MODEL", style="dim cyan")
        ),
    )

    console.print()
    console.print(
        Panel(
            content,
            title=f"[primary] {title} [/primary]",
            subtitle="[muted] SYSTEM READY [/muted]",
            border_style="bright_cyan",
            box=ROUNDED,
            padding=(1, 2),
        ),
        justify="center",
    )


# ---------------------------------------------------------
# System status
# ---------------------------------------------------------

def status_bar(
    models: int,
    online: int,
    agents: int,
    extensions: int,
    mode: str = "FREE",
) -> None:
    """Display a compact system status dashboard."""
    grid = Table.grid(padding=(0, 2))
    grid.add_column()
    grid.add_column(justify="right")

    grid.add_row("[muted]LOCAL MODELS[/muted]", f"[model]{models}[/model]")
    grid.add_row("[muted]ONLINE PROVIDERS[/muted]", f"[status_online]{online}[/status_online]")
    grid.add_row("[muted]AI AGENTS[/muted]", f"[agent]{agents}[/agent]")
    grid.add_row("[muted]EXTENSIONS[/muted]", f"[extension]{extensions}[/extension]")
    grid.add_row("[muted]EXECUTION MODE[/muted]", f"[success]{mode}[/success]")

    console.print(
        Panel(
            grid,
            title="[primary] AI HUB STATUS [/primary]",
            border_style="cyan",
            box=ROUNDED,
            padding=(0, 1),
        )
    )


# ---------------------------------------------------------
# Messages
# ---------------------------------------------------------

def info(text: str) -> None:
    console.print(
        "[primary]◆[/primary] [muted]AI HUB[/muted]  " + text
    )


def ok(text: str) -> None:
    console.print(f"[success]✔[/success] {text}")


def warn(text: str) -> None:
    console.print(f"[warning]⚠[/warning] {text}")


def error(text: str) -> None:
    console.print(f"[error]✖ ERROR[/error]  {text}")


# ---------------------------------------------------------
# Interactive input
# ---------------------------------------------------------

def prompt(text: str = "> ") -> str:
    """Read user input using the shared AI HUB theme."""
    return console.input(f"[primary]❯[/primary] [bold white]{text}[/bold white]")


# ---------------------------------------------------------
# Tables
# ---------------------------------------------------------

def table(
    rows: list[list[str]],
    columns: list[str],
    title: str | None = None,
) -> None:
    """Print a consistently styled table."""
    result = Table(
        title=title,
        title_style="bold bright_cyan",
        header_style="bold white",
        border_style="cyan",
        box=ROUNDED,
        show_lines=True,
        expand=False,
    )

    for column in columns:
        result.add_column(column, style="secondary", overflow="fold")

    for row in rows:
        result.add_row(*(str(cell) for cell in row))

    console.print(result)


# ---------------------------------------------------------
# Loading animation
# ---------------------------------------------------------

def loading(text: str = "LOADING AI HUB...") -> Live:
    """Create an animated loading indicator.

    Use with a context manager:

        with loading("Checking AI providers..."):
            perform_check()
    """
    spinner = Spinner(
        "dots",
        text=Text(f" {text}", style="bold bright_cyan"),
        style="bright_cyan",
    )

    return Live(
        spinner,
        console=console,
        refresh_per_second=12,
        transient=True,
    )
