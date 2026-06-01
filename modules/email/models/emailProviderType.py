"""Supported email provider types."""

from __future__ import annotations


class EmailProviderType:
    """Normalize provider names used by Aura email accounts."""

    GMAIL = "GMAIL"
    OUTLOOK = "OUTLOOK"
    IMAP_SMTP = "IMAP_SMTP"
    UNKNOWN = "UNKNOWN"

    @classmethod
    def normalize(cls, value) -> str:
        text = str(value or "").strip().upper().replace("-", "_").replace(" ", "_")
        if text in {"GMAIL", "GOOGLE"}:
            return cls.GMAIL
        if text in {"OUTLOOK", "HOTMAIL", "MICROSOFT"}:
            return cls.OUTLOOK
        if text in {"IMAP_SMTP", "IMAPSMTP", "IMAP"}:
            return cls.IMAP_SMTP
        return cls.UNKNOWN
