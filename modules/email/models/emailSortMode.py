"""Email sort modes."""

from __future__ import annotations


class EmailSortMode:
    """Supported email sorting modes."""

    NEWEST_FIRST = "NEWEST_FIRST"
    OLDEST_FIRST = "OLDEST_FIRST"
    UNREAD_FIRST = "UNREAD_FIRST"
    SENDER = "SENDER"
    IMPORTANCE = "IMPORTANCE"
    ACCOUNT = "ACCOUNT"

    @classmethod
    def normalize(cls, value) -> str:
        text = str(value or "").strip().upper().replace(" ", "_")
        if text in {cls.NEWEST_FIRST, cls.OLDEST_FIRST, cls.UNREAD_FIRST, cls.SENDER, cls.IMPORTANCE, cls.ACCOUNT}:
            return text
        return cls.NEWEST_FIRST
