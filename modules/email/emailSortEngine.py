"""Email sort engine."""

from __future__ import annotations

from typing import Any

from modules.email.models import EmailSortMode


class EmailSortEngine:
    """Sort email collections in a deterministic way."""

    def sort(self, messages, mode: str | None = None):
        mode = EmailSortMode.normalize(mode)
        items = [message.asDict() if hasattr(message, "asDict") else dict(message or {}) for message in messages or []]
        if mode == EmailSortMode.OLDEST_FIRST:
            return sorted(items, key=lambda item: item.get("receivedAt") or item.get("sentAt") or "")
        if mode == EmailSortMode.UNREAD_FIRST:
            return sorted(items, key=lambda item: (not bool(item.get("isUnread", False)), item.get("receivedAt") or ""), reverse=False)
        if mode == EmailSortMode.SENDER:
            return sorted(items, key=lambda item: str(item.get("sender") or "").lower())
        if mode == EmailSortMode.IMPORTANCE:
            return sorted(items, key=lambda item: (not bool(item.get("isImportant", False)), item.get("receivedAt") or ""), reverse=False)
        if mode == EmailSortMode.ACCOUNT:
            return sorted(items, key=lambda item: (str(item.get("accountId") or ""), item.get("receivedAt") or ""), reverse=False)
        return sorted(items, key=lambda item: item.get("receivedAt") or item.get("sentAt") or "", reverse=True)
