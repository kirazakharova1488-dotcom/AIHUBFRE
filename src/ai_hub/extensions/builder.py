"""Extension builder: AI-generated tools, commands, providers and handlers."""

from __future__ import annotations

import re
import uuid
from pathlib import Path

from ai_hub.config import get_data_dir
from ai_hub.extensions.manifest import ExtensionManifest, ExtensionType
from ai_hub.extensions.sandbox import run_in_sandbox, run_tests
from ai_hub.extensions.validator import ExtensionValidator


class ExtensionBuilder:
    def __init__(self, data_dir: Path | None = None) -> None:
        self.data_dir = data_dir or get_data_dir()
        self.extensions_dir = self.data_dir / "extensions"
        self.extensions_dir.mkdir(parents=True, exist_ok=True)
        self.validator = ExtensionValidator()

    def _slug(self, name: str) -> str:
        return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")

    def build(self, name: str, description: str, ext_type: ExtensionType, code: str,
              tests: str | None = None, network: bool = False) -> tuple[ExtensionManifest, str]:
        slug = self._slug(name)
        ext_id = f"ext_{slug}"
        ext_dir = self.extensions_dir / slug
        ext_dir.mkdir(parents=True, exist_ok=True)
        manifest = ExtensionManifest(
            id=ext_id, name=name, type=ext_type, description=description,
            entrypoint="extension.py", network=network,
        )
        (ext_dir / "extension.py").write_text(code, encoding="utf-8")
        if tests:
            (ext_dir / "test_extension.py").write_text(tests, encoding="utf-8")
        manifest_path = ext_dir / "manifest.json"
        manifest_path.write_text(manifest.model_dump_json(indent=2), encoding="utf-8")
        return manifest, str(manifest_path)

    def test(self, ext_dir: Path) -> bool:
        result = run_tests(ext_dir)
        return result.exit_code == 0 and not result.timed_out

    def smoke(self, code: str) -> bool:
        result = run_in_sandbox(code)
        return result.exit_code == 0 and not result.timed_out and not result.memory_exceeded

    def generate_stub(self, name: str, ext_type: ExtensionType) -> str:
        if ext_type == ExtensionType.TOOL:
            return f"def {self._slug(name)}(*args, **kwargs):\n    return 'stub result'\n"
        if ext_type == ExtensionType.CLI_COMMAND:
            return f"def {self._slug(name)}(args):\n    return 0\n"
        if ext_type == ExtensionType.PROVIDER:
            return "from ai_hub.providers.base import BaseProvider\n\n\nclass StubProvider(BaseProvider):\n    pass\n"
        return f"# {self._slug(name)} extension\n"