"""Small utilities."""

from __future__ import annotations

import json
import re
from pathlib import Path


def count_tokens(text: str) -> int:
    """Approximate token count. Explicitly marked as approximate; not provider-exact."""
    return max(1, len(text.split()) * 4 // 3)


def sanitize_name(name: str) -> str:
    return re.sub(r"[^a-z0-9_]", "_", name.lower()).strip("_") or "unnamed"


def write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
