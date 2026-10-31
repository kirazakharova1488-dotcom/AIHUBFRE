"""Workspace tools for AI HUB developer agents."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from typing import Any

from ai_hub.config import get_workspace_dir, settings


class WorkspaceError(Exception):
    """Raised when a workspace operation is not allowed or fails."""


class DeveloperTools:
    """File and execution tools restricted to the configured workspace."""

    def __init__(self) -> None:
        self.root = get_workspace_dir().resolve()

    def _safe_path(self, value: str) -> Path:
        if not isinstance(value, str) or not value.strip():
            raise WorkspaceError("Не указан путь.")

        candidate = Path(value).expanduser()

        if candidate.is_absolute():
            raise WorkspaceError(
                "Абсолютные пути запрещены. Используй путь относительно workspace."
            )

        resolved = (self.root / candidate).resolve()

        try:
            resolved.relative_to(self.root)
        except ValueError as exc:
            raise WorkspaceError(
                "Доступ за пределы workspace запрещён."
            ) from exc

        return resolved

    def list_files(self, path: str = ".") -> str:
        directory = self._safe_path(path)

        if not directory.exists():
            return f"Папка не найдена: {path}"

        if not directory.is_dir():
            return f"Это не папка: {path}"

        entries = []

        for item in sorted(directory.iterdir(), key=lambda p: p.name.lower()):
            kind = "DIR " if item.is_dir() else "FILE"
            entries.append(f"{kind}  {item.name}")

        return "\n".join(entries) if entries else "Папка пуста."

    def read_file(self, path: str) -> str:
        file_path = self._safe_path(path)

        if not file_path.exists():
            return f"Файл не найден: {path}"

        if not file_path.is_file():
            return f"Это не файл: {path}"

        try:
            return file_path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            return file_path.read_text(
                encoding="utf-8",
                errors="replace",
            )

    def write_file(self, path: str, content: str) -> str:
        file_path = self._safe_path(path)

        if not isinstance(content, str):
            raise WorkspaceError("Содержимое файла должно быть строкой.")

        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text(content, encoding="utf-8")

        return f"Файл записан: {file_path.relative_to(self.root)}"

    def edit_file(
        self,
        path: str,
        old_text: str,
        new_text: str,
    ) -> str:
        file_path = self._safe_path(path)

        if not file_path.is_file():
            return f"Файл не найден: {path}"

        content = file_path.read_text(encoding="utf-8")

        if old_text not in content:
            return "Ошибка: исходный текст для замены не найден."

        updated = content.replace(old_text, new_text, 1)
        file_path.write_text(updated, encoding="utf-8")

        return f"Файл изменён: {file_path.relative_to(self.root)}"

    def create_directory(self, path: str) -> str:
        directory = self._safe_path(path)
        directory.mkdir(parents=True, exist_ok=True)

        return f"Папка создана: {directory.relative_to(self.root)}"

    def _run_process(self, args: list[str]) -> str:
        if not settings.sandbox_enabled:
            return "Выполнение кода отключено: sandbox_enabled=False."

        timeout = max(1, min(int(settings.sandbox_timeout), 300))

        try:
            result = subprocess.run(
                args,
                cwd=str(self.root),
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=timeout,
                shell=False,
            )
        except subprocess.TimeoutExpired:
            return f"Ошибка: превышено время выполнения ({timeout} секунд)."
        except OSError as exc:
            return f"Ошибка запуска процесса: {exc}"

        output = (result.stdout or "").strip()
        errors = (result.stderr or "").strip()

        parts = [f"Код завершения: {result.returncode}"]

        if output:
            parts.append("STDOUT:\n" + output)

        if errors:
            parts.append("STDERR:\n" + errors)

        if not output and not errors:
            parts.append("Программа завершилась без вывода.")

        return "\n\n".join(parts)

    def run_python(self, path: str) -> str:
        file_path = self._safe_path(path)

        if not file_path.is_file():
            return f"Python-файл не найден: {path}"

        if file_path.suffix.lower() != ".py":
            return "Можно запускать только файлы с расширением .py."

        return self._run_process(
            [sys.executable, str(file_path)]
        )

    def run_tests(self, path: str = ".") -> str:
        directory = self._safe_path(path)

        if not directory.is_dir():
            return f"Папка тестов не найдена: {path}"

        return self._run_process(
            [sys.executable, "-m", "pytest", str(directory), "-q"]
        )

    def install_dependencies(
        self,
        path: str = "requirements.txt",
    ) -> str:
        if not settings.network_access_allowed:
            return (
                "Установка запрещена: network_access_allowed=False. "
                "Сетевой доступ сейчас отключён."
            )

        requirements = self._safe_path(path)

        if not requirements.is_file():
            return f"Файл зависимостей не найден: {path}"

        return self._run_process(
            [
                sys.executable,
                "-m",
                "pip",
                "install",
                "-r",
                str(requirements),
            ]
        )

    def execute(self, name: str, arguments: dict[str, Any]) -> str:
        """Dispatch a model-requested tool call."""

        if not isinstance(arguments, dict):
            return "Ошибка: arguments должны быть JSON-объектом."

        try:
            if name == "list_files":
                return self.list_files(
                    str(arguments.get("path", "."))
                )

            if name == "read_file":
                return self.read_file(
                    str(arguments.get("path", ""))
                )

            if name == "write_file":
                return self.write_file(
                    str(arguments.get("path", "")),
                    str(arguments.get("content", "")),
                )

            if name == "edit_file":
                return self.edit_file(
                    str(arguments.get("path", "")),
                    str(arguments.get("old_text", "")),
                    str(arguments.get("new_text", "")),
                )

            if name == "create_directory":
                return self.create_directory(
                    str(arguments.get("path", ""))
                )

            if name == "run_python":
                return self.run_python(
                    str(arguments.get("path", ""))
                )

            if name == "run_tests":
                return self.run_tests(
                    str(arguments.get("path", "."))
                )

            if name == "install_dependencies":
                return self.install_dependencies(
                    str(arguments.get("path", "requirements.txt"))
                )

            return f"Неизвестный инструмент: {name}"

        except Exception as exc:
            return f"Ошибка инструмента {name}: {exc}"


def edit_workspace_code(
    file_path: str,
    old_text: str,
    new_text: str,
) -> str:
    """Backward-compatible wrapper for the previous editing tool."""
    tools = DeveloperTools()
    return tools.edit_file(file_path, old_text, new_text)
