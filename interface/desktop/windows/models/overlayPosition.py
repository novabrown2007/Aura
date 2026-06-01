"""Overlay position model for the Windows desktop layer."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class OverlayPosition:
    """Persisted floating-window geometry."""

    x: int = 0
    y: int = 0
    width: int = 360
    height: int = 120
    screenWidth: int = 0
    screenHeight: int = 0
    monitorName: str = ""

    def asDict(self) -> dict[str, Any]:
        return {
            "x": int(self.x),
            "y": int(self.y),
            "width": int(self.width),
            "height": int(self.height),
            "screenWidth": int(self.screenWidth),
            "screenHeight": int(self.screenHeight),
            "monitorName": self.monitorName,
        }

