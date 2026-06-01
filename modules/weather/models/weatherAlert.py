"""Weather alert model for Aura."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class WeatherAlert:
    """A normalized weather warning or emergency alert."""

    alertId: str = ""
    title: str = ""
    message: str = ""
    severity: str = "LOW"
    alertType: str = ""
    source: str = ""
    issuedAt: str = ""
    expiresAt: str = ""
    location: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def asDict(self) -> dict[str, Any]:
        return {
            "alertId": self.alertId,
            "title": self.title,
            "message": self.message,
            "severity": self.severity,
            "alertType": self.alertType,
            "source": self.source,
            "issuedAt": self.issuedAt,
            "expiresAt": self.expiresAt,
            "location": self.location,
            "metadata": dict(self.metadata),
        }

    @classmethod
    def fromDict(cls, values: dict[str, Any] | None):
        values = dict(values or {})
        return cls(
            alertId=str(values.get("alertId") or values.get("id") or ""),
            title=str(values.get("title") or ""),
            message=str(values.get("message") or values.get("content") or ""),
            severity=str(values.get("severity") or "LOW").upper(),
            alertType=str(values.get("alertType") or values.get("type") or ""),
            source=str(values.get("source") or ""),
            issuedAt=str(values.get("issuedAt") or values.get("timestamp") or ""),
            expiresAt=str(values.get("expiresAt") or ""),
            location=str(values.get("location") or ""),
            metadata=dict(values.get("metadata") or {}),
        )
