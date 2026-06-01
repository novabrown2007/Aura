"""Tray menu model for Aura's Windows desktop shell."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Any


@dataclass
class TrayMenuItem:
    """One tray menu item."""

    itemId: int
    label: str
    actionName: str
    separator: bool = False
    enabled: bool = True


@dataclass
class TrayMenu:
    """Collection of tray items and their actions."""

    items: list[TrayMenuItem] = field(default_factory=list)

    def asDict(self) -> dict[str, Any]:
        return {"items": [item.__dict__ for item in self.items]}

