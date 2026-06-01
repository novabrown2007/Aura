"""Graceful shutdown orchestration for Aura's Windows desktop shell."""

from __future__ import annotations

from typing import Any


class ShutdownManager:
    """Coordinate UI shutdown without trapping Aura in the background."""

    def __init__(self, context=None, app=None, overlayManager=None):
        self.context = context
        self.app = app
        self.overlayManager = overlayManager
        logger = getattr(context, "logger", None)
        self.logger = logger.getChild("Desktop.Shutdown") if logger else None
        self.requested = False
        self.completed = False

    def requestShutdown(self, reason: str = "user") -> bool:
        self.requested = True
        if getattr(self.context, "eventManager", None) is not None:
            try:
                self.context.eventManager.emit("assistant.shutdown.requested", {"reason": reason})
            except Exception:
                pass
        if self.overlayManager is not None and hasattr(self.overlayManager, "shutdownUi"):
            try:
                self.overlayManager.shutdownUi()
            except Exception as error:
                if self.logger:
                    self.logger.warning(f"Overlay UI shutdown failed: {error}")
        if getattr(self.context, "should_exit", None) is not None:
            self.context.should_exit = True
        if self.app is not None and hasattr(self.app, "requestExit"):
            try:
                self.app.requestExit()
            except Exception as error:
                if self.logger:
                    self.logger.warning(f"App shutdown request failed: {error}")
        self.completed = True
        return True

    def snapshot(self) -> dict[str, Any]:
        return {"requested": self.requested, "completed": self.completed}

