"""UI formatting for structured assistant responses."""

from __future__ import annotations


class UIFormatter:
    """Prepare display-friendly response text."""

    @staticmethod
    def format(text: str, fallback: str = "") -> str:
        cleaned = str(text or "").strip()
        if cleaned:
            return cleaned
        return str(fallback or "").strip()
