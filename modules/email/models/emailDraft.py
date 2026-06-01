"""Email draft model."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class EmailDraft:
    """Represent one draft email."""

    draftId: str = ""
    accountId: str = ""
    to: list[str] = field(default_factory=list)
    cc: list[str] = field(default_factory=list)
    bcc: list[str] = field(default_factory=list)
    subject: str = ""
    body: str = ""
    attachments: list[dict[str, Any]] = field(default_factory=list)
    createdAt: str = ""
    updatedAt: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def asDict(self) -> dict[str, Any]:
        return {
            "draftId": self.draftId,
            "accountId": self.accountId,
            "to": list(self.to or []),
            "cc": list(self.cc or []),
            "bcc": list(self.bcc or []),
            "subject": self.subject,
            "body": self.body,
            "attachments": [dict(item) for item in self.attachments or []],
            "createdAt": self.createdAt,
            "updatedAt": self.updatedAt,
            "metadata": dict(self.metadata or {}),
        }

    @classmethod
    def fromDict(cls, values: dict[str, Any] | None):
        values = dict(values or {})
        return cls(
            draftId=str(values.get("draftId") or values.get("id") or ""),
            accountId=str(values.get("accountId") or ""),
            to=list(values.get("to") or []),
            cc=list(values.get("cc") or []),
            bcc=list(values.get("bcc") or []),
            subject=str(values.get("subject") or ""),
            body=str(values.get("body") or ""),
            attachments=[dict(item) for item in (values.get("attachments") or [])],
            createdAt=str(values.get("createdAt") or ""),
            updatedAt=str(values.get("updatedAt") or ""),
            metadata=dict(values.get("metadata") or {}),
        )
