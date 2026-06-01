"""Executable action definition."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from assistant.execution.actions.executableAction import ExecutableAction


@dataclass
class ActionDefinition(ExecutableAction):
    """A registered action definition with validation metadata."""

    executionHandler: str = ""
    parameterSchema: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def fromTool(cls, tool) -> "ActionDefinition":
        payload = tool.asDict() if hasattr(tool, "asDict") else dict(tool or {})
        return cls(
            actionName=str(payload.get("name") or ""),
            module=str(payload.get("module") or ""),
            category=str(payload.get("category") or "UTILITY"),
            parameters=dict(payload.get("parameters") or {}),
            requiredPermissions=tuple(payload.get("requiredPermissions") or ()),
            riskLevel=str(payload.get("riskLevel") or "LOW"),
            isAsync=bool(payload.get("isAsync", False)),
            metadata={
                "method": payload.get("method", ""),
                "description": payload.get("description", ""),
                "safe": bool(payload.get("safe", True)),
                "offlineAllowed": bool(payload.get("offlineAllowed", False)),
                "confirmRequired": bool(payload.get("confirmRequired", False)),
            },
            executionHandler=str(payload.get("method") or ""),
            parameterSchema={
                "type": "object",
                "properties": dict(payload.get("parameters") or {}),
                "required": list(payload.get("requiredParameters") or []),
            },
        )
