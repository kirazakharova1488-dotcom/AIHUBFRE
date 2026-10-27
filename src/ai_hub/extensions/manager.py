"""Extension manager: load, enable, disable, uninstall, version history."""

from __future__ import annotations

import json
import uuid
from pathlib import Path

from ai_hub.config import get_data_dir
from ai_hub.extensions.manifest import ExtensionManifest
from ai_hub.extensions.validator import ExtensionValidator
from ai_hub.storage.database import get_connection
from ai_hub.storage.repositories import ExtensionRepository


class ExtensionManager:
    def __init__(self, data_dir: Path | None = None, connection=None) -> None:
        self.data_dir = data_dir or get_data_dir()
        self.extensions_dir = self.data_dir / "extensions"
        self.extensions_dir.mkdir(parents=True, exist_ok=True)
        self.conn = connection or get_connection()
        self.repo = ExtensionRepository(self.conn)
        self.validator = ExtensionValidator()

    def install(self, manifest: ExtensionManifest, manifest_path: str) -> ExtensionManifest:
        self.repo.create(
            ext_id=manifest.id, name=manifest.name, type_=manifest.type.value,
            manifest_path=manifest_path, version=manifest.version, enabled=1,
            source="ai-hub",
        )
        return manifest

    def list(self) -> list[dict]:
        return self.repo.list()

    def get(self, ext_id: str) -> dict | None:
        return self.repo.get(ext_id)

    def enable(self, ext_id: str) -> bool:
        return self.repo.set_enabled(ext_id, True)

    def disable(self, ext_id: str) -> bool:
        return self.repo.set_enabled(ext_id, False)

    def uninstall(self, ext_id: str) -> bool:
        row = self.repo.get(ext_id)
        if row and row.get("manifest_path"):
            try:
                Path(row["manifest_path"]).parent.rmdir()
            except OSError:
                pass
        return self.repo.delete(ext_id)

    def validate(self, manifest: ExtensionManifest) -> bool:
        return self.validator.validate_manifest(manifest).ok

    def load_manifest(self, path: Path) -> ExtensionManifest:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        return ExtensionManifest.model_validate(data)

    def new_id(self) -> str:
        return f"ext_{uuid.uuid4().hex[:8]}"