"""Content area wrapper for the Aura application shell."""

from __future__ import annotations

from .page_manager import PageManager
from .pages.chat_page import ChatPage
from .pages.home_page import HomePage
from .pages.media_manager_page import MediaManagerPage
from .pages.weather_page import WeatherPage


class ContentArea:
    """Expose the switchable middle page area."""

    def __init__(self, page_manager: PageManager | None = None, context=None, post_ui_event=None, thread_factory=None):
        self.page_manager = page_manager or PageManager(
            {
                "home": HomePage(),
                "chat": ChatPage(context=context, post_ui_event=post_ui_event, thread_factory=thread_factory),
                "media": MediaManagerPage(context=context),
                "weather": WeatherPage(context=context),
            },
            initial_page="home",
        )
        if "home" not in getattr(self.page_manager, "_pages", {}):
            self.page_manager.registerPage("home", HomePage())
        if "chat" not in getattr(self.page_manager, "_pages", {}):
            self.page_manager.registerPage("chat", ChatPage(context=context, post_ui_event=post_ui_event, thread_factory=thread_factory))
        if "media" not in getattr(self.page_manager, "_pages", {}):
            self.page_manager.registerPage("media", MediaManagerPage(context=context))
        if "weather" not in getattr(self.page_manager, "_pages", {}):
            self.page_manager.registerPage("weather", WeatherPage(context=context))
        self.page_manager.setPage("home")

    def render(self, canvas, width: int, height: int, theme, sidebar_visible: bool):
        self.page_manager.render(canvas, width, height, theme, sidebar_visible)

    def handle_press(self, x: int, y: int, width: int, height: int, sidebar_visible: bool) -> bool:
        return self.page_manager.handle_press(x, y, width, height, sidebar_visible)

    def handle_drag(self, x: int, y: int, width: int, height: int, sidebar_visible: bool) -> bool:
        return self.page_manager.handle_drag(x, y, width, height, sidebar_visible)

    def handle_release(self, x: int, y: int, width: int, height: int, sidebar_visible: bool) -> bool:
        return self.page_manager.handle_release(x, y, width, height, sidebar_visible)

    def handle_scroll(self, delta: int, x: int, y: int, width: int, height: int, sidebar_visible: bool) -> bool:
        return self.page_manager.handle_scroll(delta, x, y, width, height, sidebar_visible)

    def handle_keypress(self, event) -> bool:
        return self.page_manager.handle_keypress(event)

    def submitPrompt(self, prompt: str) -> bool:
        return self.page_manager.submit_prompt(prompt)

    def content_bounds(self, width: int, height: int, sidebar_visible: bool) -> dict[str, int]:
        return self.page_manager.content_bounds(width, height, sidebar_visible)

    def setPage(self, pageName):
        return self.page_manager.setPage(pageName)

    def currentPageName(self):
        return self.page_manager.current_page_name()
