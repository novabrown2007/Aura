"""Base page contract for the Aura content area."""

from __future__ import annotations


class Page:
    """Interface for middle-section pages."""

    name = "page"

    def render(self, canvas, width: int, height: int, theme, sidebar_visible: bool):
        raise NotImplementedError

    def handle_press(self, x: int, y: int, width: int, height: int, sidebar_visible: bool) -> bool:
        return False

    def handle_drag(self, x: int, y: int, width: int, height: int, sidebar_visible: bool) -> bool:
        return False

    def handle_release(self, x: int, y: int, width: int, height: int, sidebar_visible: bool) -> bool:
        return False
