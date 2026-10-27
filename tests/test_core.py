"""Unit tests for the core pieces: token manager, permissions, manifest, sandbox."""

from __future__ import annotations

import pytest

from ai_hub.agents.models import AgentStatus
from ai_hub.config import Settings
from ai_hub.core.permissions import Permissions
from ai_hub.core.token_manager import TokenManager
from ai_hub.extensions.manifest import ExtensionManifest, ExtensionType
from ai_hub.extensions.validator import ExtensionValidator


def _settings() -> Settings:
    return Settings(_env_file=None, _env_file_encoding=None)  # type: ignore[arg-type]


def test_token_manager_budget() -> None:
    tm = TokenManager(_settings())
    budget = tm.apply_to_request()
    assert budget.output_tokens == 2000
    assert budget.context_tokens == 8000


def test_token_manager_usage_totals() -> None:
    tm = TokenManager(_settings())
    tm.record(input_tokens=10, output_tokens=5, context_limit=8000, model="m")
    assert tm.total_tokens() == 15


def test_permissions_approve_and_deny() -> None:
    perms = Permissions()
    assert perms.can_execute("delete_all_data") is False
    perms.approve("delete_all_data")
    assert perms.can_execute("delete_all_data") is True


def test_agent_status_values() -> None:
    assert AgentStatus.IDLE.value == "idle"
    assert AgentStatus.RUNNING.value == "running"


def test_manifest_defaults() -> None:
    m = ExtensionManifest(id="ext_x", name="X", type=ExtensionType.TOOL, description="d")
    assert m.type == ExtensionType.TOOL
    assert m.version == "1.0.0"
    assert m.network is False
    assert m.filesystem is False


def test_validator_forbidden_code() -> None:
    v = ExtensionValidator()
    result = v.validate_code("import os; os.system('rm -rf /')")
    assert result.ok is False
    assert any("forbidden" in e.lower() for e in result.errors)


def test_sandbox_blocks_forbidden_code() -> None:
    from ai_hub.extensions.sandbox import run_in_sandbox
    result = run_in_sandbox("import os; os.system('rm -rf /')")
    assert result.exit_code != 0
    assert result.timed_out is False


def test_config_defaults() -> None:
    s = _settings()
    assert s.app_name == "AI HUB CLI"
    assert s.ollama_host == "http://localhost:11434"
    assert s.default_output_token_limit == 2000
