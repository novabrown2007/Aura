"""Retry policy for background tasks."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class RetryPolicy:
    """Describe task retry behavior."""

    maxRetries: int = 3
    retryDelaySeconds: float = 30.0
    backoffMultiplier: float = 2.0
    retryOnFailure: bool = True

    def asDict(self) -> dict:
        return {
            "maxRetries": int(self.maxRetries),
            "retryDelaySeconds": float(self.retryDelaySeconds),
            "backoffMultiplier": float(self.backoffMultiplier),
            "retryOnFailure": bool(self.retryOnFailure),
        }

    @classmethod
    def fromDict(cls, data: dict | None):
        data = dict(data or {})
        return cls(
            maxRetries=int(data.get("maxRetries", 3)),
            retryDelaySeconds=float(data.get("retryDelaySeconds", 30.0)),
            backoffMultiplier=float(data.get("backoffMultiplier", 2.0)),
            retryOnFailure=bool(data.get("retryOnFailure", True)),
        )
