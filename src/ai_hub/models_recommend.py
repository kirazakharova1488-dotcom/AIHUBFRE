import os
import shutil
import subprocess
from pathlib import Path

import httpx
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

console = Console()

CATALOG = [
    {
        "name": "qwen2.5:3b",
        "download_gb": 2.0,
        "vram_gb": 3.0,
        "ram_gb": 5.0,
        "use": "Быстрый помощник",
    },
    {
        "name": "gemma3:4b",
        "download_gb": 3.3,
        "vram_gb": 4.0,
        "ram_gb": 6.0,
        "use": "Универсальные задачи",
    },
    {
        "name": "qwen2.5:7b",
        "download_gb": 4.7,
        "vram_gb": 6.0,
        "ram_gb": 9.0,
        "use": "Код и анализ",
    },
    {
        "name": "llama3.1:8b",
        "download_gb": 4.9,
        "vram_gb": 7.0,
        "ram_gb": 10.0,
        "use": "Общение и универсальные задачи",
    },
    {
        "name": "qwen2.5:14b",
        "download_gb": 9.0,
        "vram_gb": 10.0,
        "ram_gb": 18.0,
        "use": "Более сложные задачи",
    },
]


def get_ram_gb():
    try:
        if os.name == "nt":
            import ctypes

            class MEMORYSTATUSEX(ctypes.Structure):
                _fields_ = [
                    ("dwLength", ctypes.c_ulong),
                    ("dwMemoryLoad", ctypes.c_ulong),
                    ("ullTotalPhys", ctypes.c_ulonglong),
                    ("ullAvailPhys", ctypes.c_ulonglong),
                    ("ullTotalPageFile", ctypes.c_ulonglong),
                    ("ullAvailPageFile", ctypes.c_ulonglong),
                    ("ullTotalVirtual", ctypes.c_ulonglong),
                    ("ullAvailVirtual", ctypes.c_ulonglong),
                    ("ullAvailExtendedVirtual", ctypes.c_ulonglong),
                ]

            status = MEMORYSTATUSEX()
            status.dwLength = ctypes.sizeof(status)
            if ctypes.windll.kernel32.GlobalMemoryStatusEx(
                ctypes.byref(status)
            ):
                return (
                    status.ullTotalPhys / (1024 ** 3),
                    status.ullAvailPhys / (1024 ** 3),
                )
        else:
            import psutil
            memory = psutil.virtual_memory()
            return (
                memory.total / (1024 ** 3),
                memory.available / (1024 ** 3),
            )
    except Exception:
        pass
    return None, None


def get_gpu():
    try:
        result = subprocess.run(
            [
                "nvidia-smi",
                "--query-gpu=name,memory.total,memory.used",
                "--format=csv,noheader,nounits",
            ],
            capture_output=True,
            text=True,
            timeout=5,
            check=True,
        )
        gpus = []
        for line in result.stdout.strip().splitlines():
            parts = [part.strip() for part in line.split(",")]
            if len(parts) >= 3:
                gpus.append({
                    "name": parts[0],
                    "total": float(parts[1]) / 1024,
                    "used": float(parts[2]) / 1024,
                })
        return gpus
    except (OSError, subprocess.SubprocessError, ValueError):
        return []


def get_ollama_host():
    host = os.getenv("OLLAMA_HOST", "http://localhost:11434").rstrip("/")
    if "://" not in host:
        host = "http://" + host
    return host


def get_model_directory():
    configured = os.getenv("OLLAMA_MODELS")
    if configured:
        return Path(configured).expanduser()

    if os.name == "nt":
        return Path.home() / ".ollama" / "models"

    return Path.home() / ".ollama" / "models"


def get_disk_info(path):
    probe = path
    while not probe.exists() and probe != probe.parent:
        probe = probe.parent

    try:
        usage = shutil.disk_usage(probe)
        return {
            "path": str(path),
            "probe": str(probe),
            "free_gb": usage.free / (1024 ** 3),
            "total_gb": usage.total / (1024 ** 3),
            "exists": path.exists(),
        }
    except OSError:
        return None


def get_ollama_models():
    try:
        response = httpx.get(
            f"{get_ollama_host()}/api/tags",
            timeout=8,
        )
        response.raise_for_status()
        return response.json().get("models", []), None
    except Exception as exc:
        return [], str(exc)


def show_recommendations():
    console.print()
    console.print(Panel(
        "[bold cyan]AI HUB[/bold cyan]  [white]SMART MODEL ADVISOR[/white]\n"
        "[dim]Оборудование, хранилище и совместимость моделей[/dim]",
        border_style="cyan",
    ))

    total_ram, available_ram = get_ram_gb()
    gpus = get_gpu()

    hardware = Table(title="ОБОРУДОВАНИЕ", border_style="cyan")
    hardware.add_column("Компонент", style="bold")
    hardware.add_column("Всего")
    hardware.add_column("Сейчас свободно")

    hardware.add_row(
        "System RAM",
        f"{total_ram:.1f} GiB" if total_ram is not None else "Не определена",
        f"{available_ram:.1f} GiB" if available_ram is not None else "—",
    )

    for gpu in gpus:
        free = max(0.0, gpu["total"] - gpu["used"])
        hardware.add_row(
            gpu["name"],
            f"{gpu['total']:.1f} GiB VRAM",
            f"{free:.1f} GiB VRAM",
        )

    if not gpus:
        hardware.add_row("NVIDIA GPU", "Не обнаружена", "—")

    console.print(hardware)

    model_dir = get_model_directory()
    disk = get_disk_info(model_dir)

    console.print()
    console.print(Panel(
        f"[bold]Папка моделей:[/bold] {model_dir}",
        title="OLLAMA STORAGE",
        border_style="blue",
    ))

    if disk:
        console.print(
            f"Диск: [bold]{disk['probe']}[/bold]  |  "
            f"Свободно: [bold green]{disk['free_gb']:.1f} GB[/bold green]  |  "
            f"Всего: {disk['total_gb']:.1f} GB"
        )
        if not disk["exists"]:
            console.print(
                "[yellow]Папка пока не создана; показано место "
                "на ближайшем существующем родительском пути.[/yellow]"
            )
    else:
        console.print("[yellow]Не удалось определить свободное место.[/yellow]")

    models, error = get_ollama_models()
    if error:
        console.print(
            f"\n[red]Ollama недоступна:[/red] {error}\n"
            "Проверь, запущена ли Ollama."
        )
        return

    installed = {model.get("name", "") for model in models}
    installed_sizes = {
        model.get("name", ""): model.get("size", 0)
        for model in models
    }

    console.print(f"\n[bold]Установлено моделей:[/bold] {len(installed)}")

    for name in sorted(installed):
        size = installed_sizes.get(name, 0)
        size_text = f"{size / (1024 ** 3):.2f} GB" if size else "размер неизвестен"
        console.print(f"  [green]✓[/green] {name} — {size_text}")

    free_vram = (
        max(0.0, gpus[0]["total"] - gpus[0]["used"])
        if gpus else None
    )

    table = Table(title="КАТАЛОГ РЕКОМЕНДАЦИЙ", border_style="cyan")
    table.add_column("Модель", style="bold")
    table.add_column("Загрузка ≈", justify="right")
    table.add_column("VRAM ≈", justify="right")
    table.add_column("Совместимость")
    table.add_column("Назначение")

    for item in CATALOG:
        if item["name"] in installed:
            status = "[green]Установлена[/green]"
        elif disk and disk["free_gb"] < item["download_gb"] * 1.3:
            status = "[red]Мало места[/red]"
        elif (
            available_ram is not None
            and available_ram >= item["ram_gb"]
            and free_vram is not None
            and free_vram >= item["vram_gb"]
        ):
            status = "[green]Хороший кандидат[/green]"
        elif available_ram is not None and available_ram >= item["ram_gb"]:
            status = "[yellow]Возможен запуск с RAM[/yellow]"
        else:
            status = "[yellow]Проверь память[/yellow]"

        table.add_row(
            item["name"],
            f"≈ {item['download_gb']:.1f} GB",
            f"≈ {item['vram_gb']:.0f} GiB",
            status,
            item["use"],
        )

    console.print()
    console.print(table)

    console.print(
        "\n[dim]Размеры загрузки и требования к VRAM — ориентировочные "
        "оценки для типичных квантованных вариантов, а не точные "
        "характеристики каждого тега. Дополнительно нужны место для "
        "временных файлов и память под контекст. Свободная VRAM "
        "может меняться во время работы.[/dim]"
    )

    console.print(
        "\n[bold cyan]Установка:[/bold cyan] "
        "aihub models-install ИМЯ_МОДЕЛИ"
    )


