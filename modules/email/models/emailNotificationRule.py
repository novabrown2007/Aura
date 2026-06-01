"""Email notification rule model."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class EmailNotificationRule:
    """Describe how Aura should surface email alerts."""

    ruleId: str = ""
    titleTemplate: str = ""
    priority: str = "NORMAL"
    keywords: list[str] = field(default_factory=list)
    senderPatterns: list[str] = field(default_factory=list)
    cooldownSeconds: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)

    def asDict(self) -> dict[str, Any]:
        return {
            "ruleId": self.ruleId,
            "titleTemplate": self.titleTemplate,
            "priority": self.priority,
            "keywords": list(self.keywords or []),
            "senderPatterns": list(self.senderPatterns or []),
            "cooldownSeconds": int(self.cooldownSeconds or 0),
            "metadata": dict(self.metadata or {}),
        }
