"""Access control / permissions for agents, tools and extensions."""

from __future__ import annotations

from dataclasses import dataclass, field


class PermissionLevel:
    DENY = "deny"
    PROMPT = "prompt"  # require user approval
    ALLOW = "allow"


@dataclass
class PermissionSet:
    allowed_tools: set[str] = field(default_factory=set)
    allowed_actions: set[str] = field(default_factory=set)
    denied_actions: set[str] = field(default_factory=set)

    def can(self, action: str, tool: str | None = None) -> bool:
        if action in self.denied_actions:
            return False
        if action in self.allowed_actions:
            return True
        if tool is not None and tool in self.allowed_tools:
            return True
        return False

    def require(self, action: str, tool: str | None = None) -> PermissionLevel:
        if self.can(action, tool):
            return PermissionLevel.ALLOW
        if self.denied_actions:
            return PermissionLevel.DENY
        return PermissionLevel.PROMPT


@dataclass
class ActionRecord:
    action: str
    actor: str
    status: str
    timestamp: str = ""


class Permissions:
    def __init__(self, user_approvals: set[str] | None = None) -> None:
        self.user_approvals = user_approvals or set()
        self.history: list[ActionRecord] = []

    def approve(self, action: str, actor: str = "user") -> None:
        self.user_approvals.add(f"{actor}:{action}")
        self.history.append(ActionRecord(action=action, actor=actor, status="approved"))

    def deny(self, action: str, actor: str = "user") -> None:
        self.user_approvals.add(f"{actor}:deny:{action}")
        self.history.append(ActionRecord(action=action, actor=actor, status="denied"))

    def is_approved(self, action: str, actor: str = "user") -> bool:
        return f"{actor}:{action}" in self.user_approvals

    def can_execute(self, action: str, actor: str = "user") -> bool:
        if not self.is_approved(action, actor):
            return False
        return True
