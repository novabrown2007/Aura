"""Layout manager for the Aura Developer UI."""

from __future__ import annotations

from tkinter import ttk

from interface.developerUI.panels import (
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

    def __init__(self, context=None, parent=None):
        self.context = context
        self.parent = parent
        logger = getattr(context, "logger", None)
        self.logger = logger.getChild("DeveloperUI.Layout") if logger else None

    def build(self):
        """Build the tab widget and panel instances."""

        tabs = ttk.Notebook(self.parent)
        panels = []
        for panelClass in self.panelClasses:
            panel = panelClass(tabs)
            panels.append(panel)
            tabs.add(panel, text=getattr(panel, "title", panelClass.__name__))
        return tabs, panels
