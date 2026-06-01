"""Email message model."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class EmailMessage:
    """Represent one message in an email inbox."""

    messageId: str = ""
    accountId: str = ""
    threadId: str = ""
    sender: str = ""
    recipients: list[str] = field(default_factory=list)
    cc: list[str] = field(default_factory=list)
    bcc: list[str] = field(default_factory=list)
    subject: str = ""
    snippet: str = ""
    body: str = ""
    receivedAt: str = ""
    sentAt: str = ""
    isUnread: bool = True
    isImportant: bool = False
    labels: list[str] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)
    attachments: list[dict[str, Any]] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def asDict(self) -> dict[str, Any]:
        return {
            "messageId": self.messageId,
            "accountId": self.accountId,
            "threadId": self.threadId,
            "sender": self.sender,
            "recipients": list(self.recipients or []),
            "cc": list(self.cc or []),
            "bcc": list(self.bcc or []),
            "subject": self.subject,
            "snippet": self.snippet,
            "body": self.body,
            "receivedAt": self.receivedAt,
            "sentAt": self.sentAt,
            "isUnread": bool(self.isUnread),
            "isImportant": bool(self.isImportant),
            "labels": list(self.labels or []),
            "tags": list(self.tags or []),
            "attachments": [dict(item) for item in self.attachments or []],
            "metadata": dict(self.metadata or {}),
        }

    @classmethod
    def fromDict(cls, values: dict[str, Any] | None):
        values = dict(values or {})
        return cls(
            messageId=str(values.get("messageId") or values.get("id") or ""),
            accountId=str(values.get("accountId") or ""),
            threadId=str(values.get("threadId") or ""),
            sender=str(values.get("sender") or ""),
            recipients=list(values.get("recipients") or []),
            cc=list(values.get("cc") or []),
            bcc=list(values.get("bcc") or []),
            subject=str(values.get("subject") or ""),
            snippet=str(values.get("snippet") or ""),
            body=str(values.get("body") or ""),
            receivedAt=str(values.get("receivedAt") or ""),
            sentAt=str(values.get("sentAt") or ""),
            isUnread=bool(values.get("isUnread", True)),
            isImportant=bool(values.get("isImportant", False)),
            labels=list(values.get("labels") or []),
            tags=list(values.get("tags") or []),
            attachments=[dict(item) for item in (values.get("attachments") or [])],
            metadata=dict(values.get("metadata") or {}),
        )
