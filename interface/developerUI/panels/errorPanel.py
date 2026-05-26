"""Error panel for the Aura Developer UI."""

from __future__ import annotations

from interface.developerUI.panels.basePanel import TextPanel


class ErrorPanel(TextPanel):
    """Display recent exceptions and operational failures."""

    title = "Errors"

    def refresh(self, snapshot):
        lines = ["[ERRORS]"]
        if not snapshot.errors:
            lines.append("No errors observed.")
        for error in snapshot.errors[-100:]:
            lines.append("")
            lines.append(f"[{error.get('timestamp')}] {error.get('name')}")
            lines.append(f"Error: {error.get('error')}")
            lines.append(f"Payload: {error.get('payload')}")
        self.setText("\n".join(str(line) for line in lines))
