"""Page registry and routing for the Aura middle content area."""

from __future__ import annotations


class PageManager:
    """Store and switch the active middle-page implementation."""

    def __init__(self, pages: dict[str, object] | None = None, initial_page: str | None = "home"):
        self._pages: dict[str, object] = {}
        self.currentPageName: str | None = None
        self.currentPage = None
        for name, page in (pages or {}).items():
            self.registerPage(name, page)
        if initial_page is not None and initial_page in self._pages:
            self.setPage(initial_page)

    def registerPage(self, pageName: str, page):
        self._pages[str(pageName)] = page
        if self.currentPage is None:
            self.setPage(pageName)

    def setPage(self, pageName):
        page = self._pages.get(str(pageName))
        if page is None:
            return None
        self.currentPageName = str(pageName)
        self.currentPage = page
        return page

    def render(self, canvas, width: int, height: int, theme, sidebar_visible: bool):
        if self.currentPage is None:
            return
        self.currentPage.render(canvas, width, height, theme, sidebar_visible)

    def handle_press(self, x: int, y: int, width: int, height: int, sidebar_visible: bool) -> bool:
        if self.currentPage is None:
            return False
        return bool(self.currentPage.handle_press(x, y, width, height, sidebar_visible))

    def handle_drag(self, x: int, y: int, width: int, height: int, sidebar_visible: bool) -> bool:
        if self.currentPage is None:
            return False
        return bool(self.currentPage.handle_drag(x, y, width, height, sidebar_visible))

    def handle_release(self, x: int, y: int, width: int, height: int, sidebar_visible: bool) -> bool:
        if self.currentPage is None:
            return False
        return bool(self.currentPage.handle_release(x, y, width, height, sidebar_visible))

    def handle_scroll(self, delta: int, x: int, y: int, width: int, height: int, sidebar_visible: bool) -> bool:
        if self.currentPage is None:
            return False
        handler = getattr(self.currentPage, "handle_scroll", None)
        if handler is None:
            return False
        return bool(handler(delta, x, y, width, height, sidebar_visible))

    def handle_keypress(self, event) -> bool:
        if self.currentPage is None:
            return False
        handler = getattr(self.currentPage, "handle_keypress", None)
        if handler is None:
            return False
        return bool(handler(event))

    def submit_prompt(self, prompt: str) -> bool:
        if self.currentPage is None:
            return False
        handler = getattr(self.currentPage, "submit_prompt", None)
        if handler is None:
            return False
        return bool(handler(prompt))

    def content_bounds(self, width: int, height: int, sidebar_visible: bool) -> dict[str, int]:
        if self.currentPage is None:
            return {"left": 36, "right": width - 36, "top": 102, "bottom": height - 148}
        return self.currentPage.content_bounds(width, height, sidebar_visible)

    def current_page_name(self) -> str | None:
        return self.currentPageName
