"""Email attachment model."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class EmailAttachment:
    """Represent one attachment associated with an email."""

    attachmentId: str = ""
    filename: str = ""
    mimeType: str = ""
    sizeBytes: int = 0
    url: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def asDict(self) -> dict[str, Any]:
        return {
            "attachmentId": self.attachmentId,
            "filename": self.filename,
            "mimeType": self.mimeType,
            "sizeBytes": int(self.sizeBytes or 0),
            "url": self.url,
            "metadata": dict(self.metadata or {}),
        }

    @classmethod
    def fromDict(cls, values: dict[str, Any] | None):
        values = dict(values or {})
        return cls(
            attachmentId=str(values.get("attachmentId") or values.get("id") or ""),
            filename=str(values.get("filename") or ""),
            mimeType=str(values.get("mimeType") or values.get("contentType") or ""),
            sizeBytes=int(values.get("sizeBytes") or 0),
            url=str(values.get("url") or ""),
            metadata=dict(values.get("metadata") or {}),
        )
