"""Local Ollama model management."""

from __future__ import annotations

import json
import os
import shutil
from pathlib import Path
from collections.abc import Iterator

import httpx
from rich.progress import BarColumn, Progress, SpinnerColumn, TaskProgressColumn, TextColumn

from ai_hub.config import settings
from ai_hub.utils.console import console


def _base_url() -> str:
    return settings.ollama_host.rstrip("/")


def _read_json_lines(lines: Iterator[str]) -> Iterator[dict]:
    for line in lines:
        if not line.strip():
            continue
        try:
            data = json.loads(line)
        except json.JSONDecodeError as exc:
            raise RuntimeError(f"Invalid response from Ollama: {line[:200]}") from exc
        if isinstance(data, dict):
            if data.get("error"):
                raise RuntimeError(str(data["error"]))
            yield data


def format_bytes(size: int | float | None) -> str:
    value = float(size or 0)
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if value < 1024 or unit == "TB":
            return f"{value:.1f} {unit}" if unit != "B" else f"{int(value)} B"
        value /= 1024
    return f"{value:.1f} TB"


def list_models() -> list[dict]:
    """Return installed Ollama models."""
    try:
        response = httpx.get(
            f"{_base_url()}/api/tags",
            timeout=settings.ollama_timeout,
        )
        response.raise_for_status()
        payload = response.json()
    except (httpx.HTTPError, ValueError) as exc:
        raise RuntimeError(f"Cannot retrieve local models: {exc}") from exc

    models = payload.get("models", [])
    return sorted(models, key=lambda item: str(item.get("name", "")).lower())



# Approximate download sizes in GiB for common Ollama tags.
# Unknown tags use a conservative estimate; this is not exact metadata.
_MODEL_SIZE_ESTIMATES = {
    "qwen2.5:3b": 2.0,
    "gemma3:4b": 3.3,
    "qwen2.5:7b": 4.7,
    "llama3.1:8b": 4.9,
    "qwen2.5:14b": 9.0,
}

_UNKNOWN_MODEL_SIZE_GIB = 8.0
_DISK_SAFETY_MARGIN_GIB = 2.0
_DOWNLOAD_OVERHEAD_FACTOR = 1.3


def check_model_space(name: str) -> None:
    """Check available disk space before starting a model download."""
    configured = os.getenv("OLLAMA_MODELS")
    model_dir = (
        Path(configured).expanduser()
        if configured
        else Path.home() / ".ollama" / "models"
    )

    probe = model_dir
    while not probe.exists() and probe != probe.parent:
        probe = probe.parent

    try:
        usage = shutil.disk_usage(probe)
    except OSError as exc:
        raise RuntimeError(
            f"Cannot check free disk space for model directory {model_dir}: {exc}"
        ) from exc

    free_gib = usage.free / (1024 ** 3)
    known_size = name.lower() in _MODEL_SIZE_ESTIMATES
    estimate_gib = _MODEL_SIZE_ESTIMATES.get(
        name.lower(), _UNKNOWN_MODEL_SIZE_GIB
    )
    required_gib = (
        estimate_gib * _DOWNLOAD_OVERHEAD_FACTOR
        + _DISK_SAFETY_MARGIN_GIB
    )

    console.print("\n[bold cyan]Storage preflight[/bold cyan]")
    console.print(f"Model directory: {model_dir}")
    console.print(f"Available disk space: {free_gib:.1f} GiB")
    console.print(
        f"Estimated model download: about {estimate_gib:.1f} GiB"
        + ("" if known_size else " (conservative estimate for an unknown tag)")
    )
    console.print(
        f"Recommended free space including safety margin: {required_gib:.1f} GiB"
    )

    if not known_size:
        console.print(
            "[yellow]Exact model size is not known before download; "
            "the estimate may differ significantly.[/yellow]"
        )

    if free_gib < required_gib:
        raise RuntimeError(
            f"Not enough disk space to install {name}. "
            f"Available: {free_gib:.1f} GiB; "
            f"recommended: at least {required_gib:.1f} GiB. "
            "Free disk space or change Ollama's model storage location, "
            "then try again."
        )

    console.print("[green]Disk space check passed.[/green]")


def pull_model(name: str) -> None:
    """Download a model while displaying Ollama's reported progress."""
    name = name.strip()
    if not name:
        raise ValueError("Model name cannot be empty.")

    check_model_space(name)

    console.print(f"\n[bold cyan]Downloading model:[/bold cyan] {name}")
    try:
        with httpx.stream(
            "POST",
            f"{_base_url()}/api/pull",
            json={"name": name, "stream": True},
            timeout=None,
        ) as response:
            response.raise_for_status()
            with Progress(
                SpinnerColumn(style="cyan"),
                TextColumn("[bold]{task.description}"),
                BarColumn(),
                TaskProgressColumn(),
                console=console,
            ) as progress:
                task_id = progress.add_task("Connecting to Ollama...", total=None)
                for item in _read_json_lines(response.iter_lines()):
                    status = str(item.get("status", "Working..."))
                    total = item.get("total")
                    completed = item.get("completed")
                    if isinstance(total, (int, float)) and total > 0:
                        progress.update(
                            task_id,
                            description=status,
                            total=total,
                            completed=min(completed or 0, total),
                        )
                    else:
                        progress.update(task_id, description=status)
    except httpx.HTTPError as exc:
        raise RuntimeError(f"Model download failed: {exc}") from exc

    console.print(f"[bold green]Model ready:[/bold green] {name}")


def delete_model(name: str) -> None:
    """Delete an installed Ollama model."""
    name = name.strip()
    if not name:
        raise ValueError("Model name cannot be empty.")

    try:
        response = httpx.post(
            f"{_base_url()}/api/delete",
            json={"name": name},
            timeout=settings.ollama_timeout,
        )
        response.raise_for_status()
    except httpx.HTTPError as exc:
        detail = ""
        if isinstance(exc, httpx.HTTPStatusError):
            detail = f" ? {exc.response.text[:300]}"
        raise RuntimeError(f"Could not delete {name}: {exc}{detail}") from exc
