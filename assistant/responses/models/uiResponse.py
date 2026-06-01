"""UI response payload for Aura."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class UIResponse:
    """Display-ready response payload for desktop and developer UIs."""

    text: str = ""
    title: str = ""
    markdown: bool = True
    details: dict[str, object] | None = None

    def asDict(self) -> dict[str, object]:
        return {
            "text": self.text,
            "title": self.title,
            "markdown": bool(self.markdown),
            "details": dict(self.details or {}),
        }
