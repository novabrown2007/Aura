"""Layout manager for the Aura Developer UI."""

from __future__ import annotations

from PyQt6.QtWidgets import QTabWidget

from auraassistant.core.interface.developerUI.panels import (
    BridgePanel,
    ErrorPanel,
    EventPanel,
    IntentPanel,
    MemoryPanel,
    NotificationPanel,
    ProviderPanel,
    SessionPanel,
    SystemPanel,
    VoicePanel,
)


class LayoutManager:
    """Create the first simple tabbed developer-console layout."""

    panelClasses = (
        EventPanel,
        SessionPanel,
        IntentPanel,
        MemoryPanel,
        VoicePanel,
        ProviderPanel,
        BridgePanel,
        NotificationPanel,
        ErrorPanel,
        SystemPanel,
    )

    def __init__(self, context=None):
        self.context = context
        logger = getattr(context, "logger", None)
        self.logger = logger.getChild("DeveloperUI.Layout") if logger else None

    def build(self) -> tuple[QTabWidget, list]:
        """Build the tab widget and panel instances."""

        tabs = QTabWidget()
        panels = []
        for panelClass in self.panelClasses:
            panel = panelClass()
            panels.append(panel)
            tabs.addTab(panel, getattr(panel, "title", panelClass.__name__))
        return tabs, panels

