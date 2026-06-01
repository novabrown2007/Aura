"""Overlay state model for the Windows desktop layer."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from interface.desktop.windows.models.assistantStatus import AssistantStatus
from interface.desktop.windows.models.overlayPosition import OverlayPosition


def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


@dataclass
class OverlayState:
    """Full desktop overlay state used for debugging and UI coordination."""

    available: bool = False
    enabled: bool = False
    visible: bool = False
    minimizedToTray: bool = False
    trayActive: bool = False
    bubbleVisible: bool = False
    quickInteractionVisible: bool = False
    assistantStatus: AssistantStatus = field(default_factory=AssistantStatus)
    overlayPosition: OverlayPosition = field(default_factory=OverlayPosition)
    notificationCount: int = 0
    lastEvent: str = ""
    lastUpdated: str = field(default_factory=_now)
    error: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def asDict(self) -> dict[str, Any]:
        return {
            "available": self.available,
            "enabled": self.enabled,
            "visible": self.visible,
            "minimizedToTray": self.minimizedToTray,
            "trayActive": self.trayActive,
            "bubbleVisible": self.bubbleVisible,
            "quickInteractionVisible": self.quickInteractionVisible,
            "assistantStatus": self.assistantStatus.asDict(),
            "overlayPosition": self.overlayPosition.asDict(),
            "notificationCount": int(self.notificationCount),
            "lastEvent": self.lastEvent,
            "lastUpdated": self.lastUpdated,
            "error": self.error,
            "metadata": dict(self.metadata),
        }

