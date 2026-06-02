"""Content area wrapper for the Aura application shell."""

from __future__ import annotations

from .page_manager import PageManager
from .pages.home_page import HomePage


class ContentArea:
    """Expose the switchable middle page area."""

    def __init__(self, page_manager: PageManager | None = None):
        self.page_manager = page_manager or PageManager({"home": HomePage()}, initial_page="home")
        if "home" not in getattr(self.page_manager, "_pages", {}):
            self.page_manager.registerPage("home", HomePage())
        self.page_manager.setPage("home")

    def render(self, canvas, width: int, height: int, theme, sidebar_visible: bool):
        self.page_manager.render(canvas, width, height, theme, sidebar_visible)

    def handle_press(self, x: int, y: int, width: int, height: int, sidebar_visible: bool) -> bool:
        return self.page_manager.handle_press(x, y, width, height, sidebar_visible)

    def handle_drag(self, x: int, y: int, width: int, height: int, sidebar_visible: bool) -> bool:
        return self.page_manager.handle_drag(x, y, width, height, sidebar_visible)

    def handle_release(self, x: int, y: int, width: int, height: int, sidebar_visible: bool) -> bool:
        return self.page_manager.handle_release(x, y, width, height, sidebar_visible)

    def content_bounds(self, width: int, height: int, sidebar_visible: bool) -> dict[str, int]:
        return self.page_manager.content_bounds(width, height, sidebar_visible)

    def setPage(self, pageName):
        return self.page_manager.setPage(pageName)
