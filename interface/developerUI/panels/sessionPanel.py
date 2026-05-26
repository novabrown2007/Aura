"""Session panel for the Aura Developer UI."""

from __future__ import annotations

from interface.developerUI.panels.basePanel import TextPanel


class SessionPanel(TextPanel):
    """Display active sessions and conversation context."""

    title = "Sessions"

    def refresh(self, snapshot):
        lines = ["Active Sessions"]
        if not snapshot.sessions:
            lines.append("No active sessions.")
        for session in snapshot.sessions:
            lines.append("")
            lines.append(f"Session: {session.get('sessionId')}")
            lines.append(f"Interface: {session.get('interface', '')}")
            lines.append(f"Started: {session.get('startedAt', '')}")
            lines.append(f"Context: {session.get('context', {})}")
        self.setText("\n".join(lines))
