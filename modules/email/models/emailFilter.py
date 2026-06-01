"""Email filter model."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class EmailFilter:
    """Describe one inbox filter rule."""

    filterId: str = ""
    sender: str = ""
    recipient: str = ""
    accountId: str = ""
    labels: list[str] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)
    unreadOnly: bool = False
    hasAttachments: bool = False
    keywords: list[str] = field(default_factory=list)
    importance: str = ""
    dateFrom: str = ""
    dateTo: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def asDict(self) -> dict[str, Any]:
        return {
            "filterId": self.filterId,
            "sender": self.sender,
            "recipient": self.recipient,
            "accountId": self.accountId,
            "labels": list(self.labels or []),
            "tags": list(self.tags or []),
            "unreadOnly": bool(self.unreadOnly),
            "hasAttachments": bool(self.hasAttachments),
            "keywords": list(self.keywords or []),
            "importance": self.importance,
            "dateFrom": self.dateFrom,
            "dateTo": self.dateTo,
            "metadata": dict(self.metadata or {}),
        }

    @classmethod
    def fromDict(cls, values: dict[str, Any] | None):
        values = dict(values or {})
        return cls(
            filterId=str(values.get("filterId") or values.get("id") or ""),
            sender=str(values.get("sender") or ""),
            recipient=str(values.get("recipient") or ""),
            accountId=str(values.get("accountId") or ""),
            labels=list(values.get("labels") or []),
            tags=list(values.get("tags") or []),
            unreadOnly=bool(values.get("unreadOnly", False)),
            hasAttachments=bool(values.get("hasAttachments", False)),
            keywords=list(values.get("keywords") or []),
            importance=str(values.get("importance") or ""),
            dateFrom=str(values.get("dateFrom") or ""),
            dateTo=str(values.get("dateTo") or ""),
            metadata=dict(values.get("metadata") or {}),
        )
