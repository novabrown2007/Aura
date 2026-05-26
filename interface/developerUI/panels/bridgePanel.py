"""Bridge panel for the Aura Developer UI."""

from __future__ import annotations

from interface.developerUI.panels.basePanel import TextPanel


class BridgePanel(TextPanel):
    """Display bridge connection state and recent protocol traffic."""

    title = "Bridge"

    def refresh(self, snapshot):
        bridge = snapshot.bridge
        lines = ["[BRIDGE]", f"Connected: {bridge.get('connected', False)}"]
        if bridge.get("bridgeName"):
            lines.append(f"Bridge: {bridge.get('bridgeName')}")
        lines.append("")
        lines.append("Subscriptions:")
        lines.append(str(bridge.get("subscriptions", [])))
        lines.append("")
        lines.append("Recent Messages:")
        for message in (bridge.get("messages") or [])[-60:]:
            lines.append(f"- {message.get('timestamp')} {message.get('name')}: {message.get('summary')}")
        self.setText("\n".join(str(line) for line in lines))
