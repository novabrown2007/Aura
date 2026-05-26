"""Intent panel for the Aura Developer UI."""

from __future__ import annotations

from interface.developerUI.panels.basePanel import TextPanel


class IntentPanel(TextPanel):
    """Display generated intents, confidence, arguments, and status."""

    title = "Intents"

    def refresh(self, snapshot):
        lines = ["Intent Flow"]
        if not snapshot.intents:
            lines.append("No intent events observed.")
        for item in snapshot.intents[-80:]:
            payload = item.get("payload", {})
            lines.append("")
            lines.append(f"[{item.get('timestamp')}] {item.get('name')}")
            lines.append(f"Intent: {payload.get('intent') or payload.get('name') or payload.get('toolName') or ''}")
            lines.append(f"Confidence: {payload.get('confidence', '')}")
            lines.append(f"Arguments: {payload.get('arguments', {})}")
            lines.append(f"Status: {payload.get('status', payload.get('success', ''))}")
        self.setText("\n".join(lines))
