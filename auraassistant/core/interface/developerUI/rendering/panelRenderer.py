"""Panel renderer for the Aura Developer UI."""

from __future__ import annotations


class PanelRenderer:
    """Refresh all developer UI panels from a shared state snapshot."""

    def __init__(self, panels=None, context=None):
        self.panels = list(panels or [])
        self.context = context
        logger = getattr(context, "logger", None)
        self.logger = logger.getChild("DeveloperUI.Renderer") if logger else None

    def setPanels(self, panels):
        """Set the active panel collection."""

        self.panels = list(panels or [])

    def refresh(self, snapshot):
        """Refresh each panel safely."""

        for panel in self.panels:
            try:
                if hasattr(panel, "refresh"):
                    panel.refresh(snapshot)
            except Exception as error:
                if self.logger:
                    self.logger.warning(f"Developer UI panel refresh failed: {panel.__class__.__name__}: {error}")

