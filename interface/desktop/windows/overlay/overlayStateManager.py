"""State coordination for Aura's Windows desktop overlay."""

from __future__ import annotations

from dataclasses import asdict
from typing import Any

from interface.desktop.windows.models import AssistantStatus, OverlayPosition, OverlayState


class OverlayStateManager:
    """Maintain the current desktop presence state."""

    def __init__(self, context=None):
        self.context = context
        self.state = OverlayState()
        logger = getattr(context, "logger", None)
        self.logger = logger.getChild("Desktop.OverlayState") if logger else None

    def setEnabled(self, enabled: bool):
        self.state.enabled = bool(enabled)
        self._touch("enabled")

    def setVisible(self, visible: bool):
        self.state.visible = bool(visible)
        self._touch("visible")

    def setTrayActive(self, active: bool):
        self.state.trayActive = bool(active)
        self._touch("tray")

    def setBubbleVisible(self, visible: bool):
        self.state.bubbleVisible = bool(visible)
        self._touch("bubble")

    def setQuickInteractionVisible(self, visible: bool):
        self.state.quickInteractionVisible = bool(visible)
        self._touch("quickInteraction")

    def setMinimizedToTray(self, minimized: bool):
        self.state.minimizedToTray = bool(minimized)
        self._touch("tray")

    def setNotificationCount(self, count: int):
        self.state.notificationCount = max(0, int(count))
        self._touch("notification")

    def setOverlayPosition(self, position: OverlayPosition | dict[str, Any]):
        if isinstance(position, dict):
            position = OverlayPosition(**position)
        self.state.overlayPosition = position
        self._touch("position")

    def setAssistantStatus(self, status: AssistantStatus | dict[str, Any]):
        if isinstance(status, dict):
            status = AssistantStatus(**status)
        self.state.assistantStatus = status
        self._touch("assistant")

    def updateAssistant(self, **changes):
        status = self.state.assistantStatus
        for key, value in changes.items():
            if hasattr(status, key):
                setattr(status, key, value)
        if "state" in changes and not changes.get("message"):
            status.message = str(status.message or "")
        self._touch("assistant")
        return status

    def setError(self, error: str):
        self.state.error = str(error or "")
        self._touch("error")

    def markEvent(self, eventName: str):
        self.state.lastEvent = str(eventName or "")
        self._touch(eventName)

    def snapshot(self) -> dict[str, Any]:
        state = self.state.asDict()
        state["available"] = True
        return state

    def _touch(self, label: str):
        self.state.available = True
        self.state.lastUpdated = self._now()
        self.state.metadata["lastLabel"] = label
        if self.logger:
            self.logger.debug(f"Overlay state updated: {label}")

    @staticmethod
    def _now() -> str:
        from datetime import datetime, timezone

        return datetime.now(timezone.utc).replace(microsecond=0).isoformat()

