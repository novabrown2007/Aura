"""Persist and restore Aura's desktop overlay position."""

from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path
from typing import Any

from interface.desktop.windows.models import OverlayPosition


class OverlayPositionManager:
    """Store floating-window geometry in a local JSON file."""

    def __init__(self, context=None, storagePath: str | None = None):
        self.context = context
        logger = getattr(context, "logger", None)
        self.logger = logger.getChild("Desktop.OverlayPosition") if logger else None
        defaultPath = Path.home() / ".aura" / "desktop_overlay_position.json"
        self.storagePath = Path(storagePath or self._getConfigValue("desktopOverlay.positionFile", defaultPath))
        self.lastLoaded = ""
        self.lastSaved = ""

    def load(self) -> OverlayPosition:
        if not self.storagePath.exists():
            return OverlayPosition()
        try:
            data = json.loads(self.storagePath.read_text(encoding="utf-8"))
            position = OverlayPosition(**data)
            self.lastLoaded = self._now()
            return position
        except Exception as error:
            if self.logger:
                self.logger.warning(f"Overlay position load failed: {error}")
            return OverlayPosition()

    def save(self, position: OverlayPosition | dict[str, Any]):
        if isinstance(position, dict):
            position = OverlayPosition(**position)
        try:
            self.storagePath.parent.mkdir(parents=True, exist_ok=True)
            self.storagePath.write_text(json.dumps(position.asDict(), indent=2, sort_keys=True), encoding="utf-8")
            self.lastSaved = self._now()
        except Exception as error:
            if self.logger:
                self.logger.warning(f"Overlay position save failed: {error}")

    def clamp(self, position: OverlayPosition, screenWidth: int, screenHeight: int) -> OverlayPosition:
        width = max(160, min(int(position.width or 360), max(int(screenWidth or 0), 160)))
        height = max(100, min(int(position.height or 120), max(int(screenHeight or 0), 100)))
        maxX = max(0, int(screenWidth or width) - width)
        maxY = max(0, int(screenHeight or height) - height)
        x = min(max(int(position.x or 0), 0), maxX)
        y = min(max(int(position.y or 0), 0), maxY)
        return OverlayPosition(
            x=x,
            y=y,
            width=width,
            height=height,
            screenWidth=int(screenWidth or 0),
            screenHeight=int(screenHeight or 0),
            monitorName=str(getattr(position, "monitorName", "") or ""),
        )

    def restoreWindowPosition(self, window) -> OverlayPosition:
        position = self.load()
        try:
            if hasattr(window, "winfo_screenwidth") and hasattr(window, "winfo_screenheight"):
                position = self.clamp(position, int(window.winfo_screenwidth()), int(window.winfo_screenheight()))
            if hasattr(window, "geometry"):
                window.geometry(f"{position.width}x{position.height}+{position.x}+{position.y}")
        except Exception as error:
            if self.logger:
                self.logger.warning(f"Overlay position restore failed: {error}")
        return position

    def captureWindowPosition(self, window) -> OverlayPosition:
        try:
            geometry = str(window.geometry())
            size, _, offset = geometry.partition("+")
            width, _, height = size.partition("x")
            x, _, y = offset.partition("+")
            position = OverlayPosition(
                x=int(x or 0),
                y=int(y or 0),
                width=int(width or 360),
                height=int(height or 120),
                screenWidth=int(window.winfo_screenwidth()) if hasattr(window, "winfo_screenwidth") else 0,
                screenHeight=int(window.winfo_screenheight()) if hasattr(window, "winfo_screenheight") else 0,
            )
            self.save(position)
            return position
        except Exception as error:
            if self.logger:
                self.logger.warning(f"Overlay position capture failed: {error}")
            return OverlayPosition()

    def snapshot(self) -> dict[str, Any]:
        position = self.load()
        return {
            "storagePath": str(self.storagePath),
            "lastLoaded": self.lastLoaded,
            "lastSaved": self.lastSaved,
            "position": position.asDict(),
        }

    def _getConfigValue(self, key: str, default=None):
        config = getattr(self.context, "config", None)
        if config is None or not hasattr(config, "get"):
            return default
        return config.get(key, default)

    @staticmethod
    def _now() -> str:
        from datetime import datetime, timezone

        return datetime.now(timezone.utc).replace(microsecond=0).isoformat()

