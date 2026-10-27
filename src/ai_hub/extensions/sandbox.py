
"""Fail-closed execution wrapper for generated extensions.

On Windows, arbitrary extension execution is disabled because this module
does not provide a real operating-system security boundary.

On Unix, execution is limited by subprocess timeouts and resource limits,
but this is NOT a complete security sandbox.
"""

from __future__ import annotations

import ast
import os
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path

try:
    import resource
except ImportError:  # Windows
    resource = None

from ai_hub.config import settings


@dataclass
class SandboxResult:
    stdout: str = ""
    stderr: str = ""
    exit_code: int = 0
    timed_out: bool = False
    memory_exceeded: bool = False
    duration_ms: int = 0


def _decode_output(value: str | bytes | None) -> str:
    """Decode subprocess output without failing on invalid bytes."""
    if value is None:
        return ""
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    return value


def _validate_code(code: str) -> str | None:
    """Reject obviously dangerous constructs before executing any code.

    This is defense in depth, not a replacement for OS-level isolation.
    """
    try:
        tree = ast.parse(code, filename="<extension>")
    except SyntaxError as exc:
        return f"Invalid Python syntax: {exc}"

    forbidden_modules = {
        "os",
        "subprocess",
        "socket",
        "ctypes",
        "multiprocessing",
        "winreg",
        "importlib",
        "pty",
        "shutil",
    }

    forbidden_calls = {
        "exec",
        "eval",
        "compile",
        "__import__",
        "breakpoint",
    }

    for node in ast.walk(tree):
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            if isinstance(node, ast.Import):
                names = [alias.name.split(".")[0] for alias in node.names]
            else:
                module = node.module or ""
                names = [module.split(".")[0]]

            blocked = forbidden_modules.intersection(names)
            if blocked:
                return (
                    "Forbidden import: "
                    + ", ".join(sorted(blocked))
                )

        if isinstance(node, ast.Call):
            func = node.func
            if isinstance(func, ast.Name) and func.id in forbidden_calls:
                return f"Forbidden function call: {func.id}"

            if isinstance(func, ast.Attribute) and func.attr in {
                "system",
                "popen",
                "spawn",
                "fork",
                "execv",
                "execve",
            }:
                return f"Forbidden operation: {func.attr}"

        if isinstance(node, ast.Name) and node.id in {
            "__builtins__",
            "__loader__",
        }:
            return f"Forbidden name: {node.id}"

    return None


def _timeout_result(
    exc: subprocess.TimeoutExpired,
    start: float,
) -> SandboxResult:
    return SandboxResult(
        stdout=_decode_output(exc.stdout),
        stderr=_decode_output(exc.stderr),
        exit_code=-1,
        timed_out=True,
        duration_ms=int((time.monotonic() - start) * 1000),
    )


def _blocked_result(message: str) -> SandboxResult:
    return SandboxResult(
        stdout="",
        stderr=message,
        exit_code=1,
    )


def run_in_sandbox(
    code: str,
    *,
    timeout: int | None = None,
    max_memory_mb: int | None = None,
    network: bool = False,
    env: dict[str, str] | None = None,
) -> SandboxResult:
    """Run extension code only where this wrapper permits it.

    Windows execution is disabled until a genuine OS-level sandbox is
    configured. Unix resource limits are best-effort and not sufficient
    for executing hostile code safely.
    """
    timeout = (
        settings.sandbox_timeout if timeout is None else max(1, timeout)
    )
    max_memory_mb = (
        settings.sandbox_max_memory_mb
        if max_memory_mb is None
        else max(1, max_memory_mb)
    )

    start = time.monotonic()

    if not isinstance(code, str):
        return _blocked_result("Extension code must be a string.")

    validation_error = _validate_code(code)
    if validation_error:
        return _blocked_result(validation_error)

    if os.name == "nt":
        return _blocked_result(
            "Extension execution is disabled on Windows: "
            "a genuine OS-level sandbox is not configured. "
            "Use a properly isolated environment before running "
            "generated extension code."
        )

    # Resource limits below are best-effort, not a complete sandbox.
    if resource is None:
        return _blocked_result(
            "Resource limits are unavailable; execution is disabled."
        )

    runner = r'''
import resource
import sys
import traceback

memory_bytes = int(sys.argv[1])
cpu_seconds = int(sys.argv[2])

try:
    resource.setrlimit(
        resource.RLIMIT_AS, (memory_bytes, memory_bytes)
    )
    resource.setrlimit(
        resource.RLIMIT_CPU, (cpu_seconds, cpu_seconds + 1)
    )
except (ValueError, OSError) as exc:
    print(f"Could not apply resource limits: {exc}", file=sys.stderr)
    sys.exit(125)

source = sys.stdin.read()

try:
    exec(compile(source, "<extension>", "exec"), {"__name__": "__main__"})
except SystemExit as exc:
    sys.exit(exc.code if isinstance(exc.code, int) else 1)
except BaseException:
    traceback.print_exc()
    sys.exit(1)
'''

    child_env = {
        "PATH": os.environ.get("PATH", ""),
        "PYTHONIOENCODING": "utf-8",
        "PYTHONUTF8": "1",
    }
    if env:
        child_env.update(env)

    # This flag is intentionally not treated as proof of network isolation.
    # Real network restrictions require OS-level sandboxing.
    if network:
        return _blocked_result(
            "Network-enabled execution is not supported by this wrapper."
        )

    try:
        proc = subprocess.run(
            [
                sys.executable,
                "-I",
                "-c",
                runner,
                str(max_memory_mb * 1024 * 1024),
                str(timeout),
            ],
            input=code,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
            env=child_env,
            check=False,
        )

        return SandboxResult(
            stdout=proc.stdout,
            stderr=proc.stderr,
            exit_code=proc.returncode,
            duration_ms=int((time.monotonic() - start) * 1000),
        )

    except subprocess.TimeoutExpired as exc:
        return _timeout_result(exc, start)

    except OSError as exc:
        return SandboxResult(
            stderr=f"Could not start sandbox process: {exc}",
            exit_code=1,
            duration_ms=int((time.monotonic() - start) * 1000),
        )


def run_tests(
    extension_dir: Path,
    timeout: int = 60,
) -> SandboxResult:
    """Run extension tests only on systems where this wrapper permits it.

    On Windows, running extension tests is disabled because pytest would
    execute potentially untrusted code without a genuine sandbox.
    """
    start = time.monotonic()

    if os.name == "nt":
        return _blocked_result(
            "Extension test execution is disabled on Windows until "
            "a genuine OS-level sandbox is configured."
        )

    if not resource:
        return _blocked_result(
            "Resource limits are unavailable; extension tests are disabled."
        )

    try:
        proc = subprocess.run(
            [
                sys.executable,
                "-I",
                "-m",
                "pytest",
                "-q",
                "--no-header",
                str(extension_dir.resolve()),
            ],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=max(1, timeout),
            check=False,
        )

        return SandboxResult(
            stdout=proc.stdout,
            stderr=proc.stderr,
            exit_code=proc.returncode,
            duration_ms=int((time.monotonic() - start) * 1000),
        )

    except subprocess.TimeoutExpired as exc:
        return _timeout_result(exc, start)

    except OSError as exc:
        return SandboxResult(
            stderr=f"Could not run extension tests: {exc}",
            exit_code=1,
            duration_ms=int((time.monotonic() - start) * 1000),
        )
