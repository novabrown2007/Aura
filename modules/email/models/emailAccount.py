"""Email account model."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from modules.email.models.emailConnectionState import EmailConnectionState
from modules.email.models.emailProviderType import EmailProviderType


@dataclass
class EmailAccount:
    """Represent one connected email account."""

    accountId: str = ""
    emailAddress: str = ""
    displayName: str = ""
    providerType: str = EmailProviderType.UNKNOWN
    connectionState: str = EmailConnectionState.DISCONNECTED
    isDefault: bool = False
    syncEnabled: bool = True
    lastSyncTime: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def asDict(self) -> dict[str, Any]:
        return {
            "accountId": self.accountId,
            "emailAddress": self.emailAddress,
            "displayName": self.displayName,
            "providerType": self.providerType,
            "connectionState": self.connectionState,
            "isDefault": bool(self.isDefault),
            "syncEnabled": bool(self.syncEnabled),
            "lastSyncTime": self.lastSyncTime,
            "metadata": dict(self.metadata or {}),
        }

    @classmethod
    def fromDict(cls, values: dict[str, Any] | None):
        values = dict(values or {})
        return cls(
            accountId=str(values.get("accountId") or values.get("id") or ""),
            emailAddress=str(values.get("emailAddress") or values.get("address") or ""),
            displayName=str(values.get("displayName") or ""),
            providerType=EmailProviderType.normalize(values.get("providerType")),
            connectionState=EmailConnectionState.normalize(values.get("connectionState")),
            isDefault=bool(values.get("isDefault", False)),
            syncEnabled=bool(values.get("syncEnabled", True)),
            lastSyncTime=str(values.get("lastSyncTime") or ""),
            metadata=dict(values.get("metadata") or {}),
        )
