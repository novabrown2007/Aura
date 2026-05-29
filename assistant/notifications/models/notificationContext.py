"""Notification routing context model."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class NotificationContext:
    """Runtime context used to route notifications."""

    interfaceType: str = "desktop"
    conversationActive: bool = False
    activeTopic: str = ""
    activeEntity: str = ""
    voiceSpeaking: bool = False
    speechQueueBusy: bool = False
    quietHoursEnabled: bool = False
    quietHoursActive: bool = False
    allowVoiceInterruptions: bool = True
    criticalAlwaysInterrupt: bool = True
    userActivityState: str = "idle"
    timestamp: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def asDict(self) -> dict[str, Any]:
        """Return a serializable context snapshot."""

        return {
            "interfaceType": self.interfaceType,
            "conversationActive": bool(self.conversationActive),
            "activeTopic": self.activeTopic,
            "activeEntity": self.activeEntity,
            "voiceSpeaking": bool(self.voiceSpeaking),
            "speechQueueBusy": bool(self.speechQueueBusy),
            "quietHoursEnabled": bool(self.quietHoursEnabled),
            "quietHoursActive": bool(self.quietHoursActive),
            "allowVoiceInterruptions": bool(self.allowVoiceInterruptions),
            "criticalAlwaysInterrupt": bool(self.criticalAlwaysInterrupt),
            "userActivityState": self.userActivityState,
            "timestamp": self.timestamp,
            "metadata": dict(self.metadata),
        }
