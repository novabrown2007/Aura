"""Apply output formatting rules to structured assistant responses."""

from __future__ import annotations

from assistant.responses.formatting import NotificationFormatter, UIFormatter, VoiceFormatter


class ResponseFormatter:
    """Normalize response text for the available delivery surfaces."""

    def __init__(self, context=None):
        self.context = context
        logger = getattr(context, "logger", None)
        self.logger = logger.getChild("Responses.Formatter") if logger else None

    def formatSpokenText(self, response):
        """Return a concise TTS-friendly string."""

        return VoiceFormatter.format(getattr(response, "spokenText", ""), getattr(response, "uiText", ""))

    def formatUiText(self, response):
        """Return a display-friendly string."""

        return UIFormatter.format(getattr(response, "uiText", ""), getattr(response, "spokenText", ""))

    def formatNotification(self, notification):
        """Return a normalized notification mapping."""

        return NotificationFormatter.format(getattr(notification, "title", ""), getattr(notification, "message", ""))
