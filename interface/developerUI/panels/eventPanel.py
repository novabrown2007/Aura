"""Event panel for the Aura Developer UI."""

from __future__ import annotations

from interface.developerUI.panels.basePanel import TextPanel


class EventPanel(TextPanel):
    """Display recent Aura events."""

    title = "Events"

    def refresh(self, snapshot):
        lines = ["Time | Category | Event | Source | Payload", "-" * 96]
        for event in snapshot.events[-200:]:
            lines.append(
                f"{event.get('timestamp', '')} | {event.get('category', '')} | "
                f"{event.get('name', '')} | {event.get('source', '')} | {event.get('summary', '')}"
            )
        self.setText("\n".join(lines))
