"""Scheduled email model."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from modules.email.models.emailDraft import EmailDraft


@dataclass
class ScheduledEmail:
    """Represent one scheduled send operation."""

    scheduledEmailId: str = ""
    draft: EmailDraft = field(default_factory=EmailDraft)
    sendAt: str = ""
    state: str = "PENDING"
    createdAt: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def asDict(self) -> dict[str, Any]:
        return {
            "scheduledEmailId": self.scheduledEmailId,
            "draft": self.draft.asDict() if hasattr(self.draft, "asDict") else dict(self.draft or {}),
            "sendAt": self.sendAt,
            "state": self.state,
            "createdAt": self.createdAt,
            "metadata": dict(self.metadata or {}),
        }

    @classmethod
    def fromDict(cls, values: dict[str, Any] | None):
        values = dict(values or {})
        draft = values.get("draft") or {}
        if not isinstance(draft, EmailDraft):
            draft = EmailDraft.fromDict(draft)
        return cls(
            scheduledEmailId=str(values.get("scheduledEmailId") or values.get("id") or ""),
            draft=draft,
            sendAt=str(values.get("sendAt") or ""),
            state=str(values.get("state") or "PENDING"),
            createdAt=str(values.get("createdAt") or ""),
            metadata=dict(values.get("metadata") or {}),
        )
