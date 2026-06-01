"""Voice formatting for structured assistant responses."""

from __future__ import annotations


class VoiceFormatter:
    """Prepare concise text for TTS delivery."""

    @staticmethod
    def format(text: str, fallback: str = "") -> str:
        cleaned = str(text or "").strip()
        if cleaned:
            return cleaned
        return str(fallback or "").strip()
