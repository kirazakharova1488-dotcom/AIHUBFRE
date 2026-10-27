"""Validator: checks extension manifest, code, permissions and compatibility."""

from __future__ import annotations

from dataclasses import dataclass

from ai_hub.extensions.manifest import ExtensionManifest


@dataclass
class ValidationResult:
    ok: bool
    errors: list[str]
    warnings: list[str]


class ExtensionValidator:
    def __init__(self, settings=None) -> None:
        self.settings = settings

    def validate_manifest(self, manifest: ExtensionManifest) -> ValidationResult:
        errors: list[str] = []
        warnings: list[str] = []
        if not manifest.id:
            errors.append("manifest.id is required")
        if not manifest.name:
            errors.append("manifest.name is required")
        if manifest.max_runtime_seconds > 120:
            warnings.append("max_runtime_seconds is high; prefer <= 60")
        if manifest.network and not self._network_allowed():
            warnings.append("network access requested but disabled in settings")
        if manifest.filesystem:
            warnings.append("filesystem access requested; requires explicit approval")
        return ValidationResult(ok=not errors, errors=errors, warnings=warnings)

    def validate_code(self, code: str) -> ValidationResult:
        errors: list[str] = []
        warnings: list[str] = []
        forbidden = (
            "os.system", "subprocess", "shutil.rmtree", "rm -rf", "eval(", "exec(", "import socket",
            "requests.get", "urllib.request",
        )
        for token in forbidden:
            if token in code:
                errors.append(f"forbidden token in generated code: {token}")
        return ValidationResult(ok=not errors, errors=errors, warnings=warnings)

    def validate_compatibility(self, manifest: ExtensionManifest, providers: list[str]) -> ValidationResult:
        warnings: list[str] = []
        if manifest.type == "provider" and not providers:
            warnings.append("no providers registered; extension may not function")
        return ValidationResult(ok=True, errors=[], warnings=warnings)

    def _network_allowed(self) -> bool:
        return bool(self.settings.network_access_allowed) if self.settings else False