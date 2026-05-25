"""Text-based debug console for assistant ecosystem simulations."""

from __future__ import annotations

from typing import Any


class AssistantConsole:
    """Render human-readable simulation events for debugging."""

    def __init__(self, context=None, tracer=None):
        self.context = context
        self.tracer = tracer
        self.logger = context.logger.getChild("Testing.Console") if context and getattr(context, "logger", None) else None
        self.lines: list[str] = []

    def displayVoice(self, text: str):
        return self._append("VOICE", text)

    def displayIntent(self, intent: str):
        return self._append("INTENT", intent)

    def displayBridge(self, text: str):
        return self._append("BRIDGE", text)

    def displayResponse(self, text: str):
        return self._append("RESPONSE", text)

    def displayNotification(self, text: str):
        return self._append("NOTIFICATION", text)

    def displaySubscription(self, text: str):
        return self._append("SUBSCRIPTION", text)

    def displaySession(self, text: str):
        return self._append("SESSION", text)

    def displayStream(self, text: str):
        return self._append("STREAM", text)

    def displayAnalysis(self, text: str):
        return self._append("ANALYSIS", text)

    def render(self, kind: str, text: str):
        """Render one tagged console line."""

        return self._append(kind, text)

    def renderBlock(self, title: str, lines: list[str]):
        """Render a multi-line debug block."""

        self._append(title, "")
        for line in lines:
            self._append(title, line)
        return self.lines[-len(lines) - 1 :] if lines else self.lines[-1:]

    def clear(self):
        """Reset the console log."""

        self.lines.clear()

    def getLines(self) -> list[str]:
        """Return a copy of the rendered output."""

        return list(self.lines)

    def _append(self, kind: str, text: str):
        line = f"[{kind.upper()}] {text}"
        self.lines.append(line)
        if self.logger:
            self.logger.info(line)
        return line
