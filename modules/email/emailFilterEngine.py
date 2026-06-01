"""Email filtering engine."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from modules.email.models import EmailFilter


class EmailFilterEngine:
    """Apply deterministic filters to email collections."""

    def apply(self, messages, criteria: dict[str, Any] | EmailFilter | None = None):
        criteria = criteria.asDict() if isinstance(criteria, EmailFilter) else dict(criteria or {})
        items = [self._asDict(message) for message in messages or []]
        filtered = []
        for message in items:
            if not self._matches(message, criteria):
                continue
            filtered.append(message)
        return filtered

    def _matches(self, message: dict[str, Any], criteria: dict[str, Any]):
        sender = str(criteria.get("sender") or "").lower()
        recipient = str(criteria.get("recipient") or "").lower()
        accountId = str(criteria.get("accountId") or "")
        labels = {str(value).lower() for value in criteria.get("labels") or []}
        tags = {str(value).lower() for value in criteria.get("tags") or []}
        keywords = [str(value).lower() for value in criteria.get("keywords") or []]
        if sender and sender not in str(message.get("sender") or "").lower():
            return False
        if recipient and recipient not in " ".join(message.get("recipients") or []).lower():
            return False
        if accountId and accountId != str(message.get("accountId") or ""):
            return False
        if criteria.get("unreadOnly") and not bool(message.get("isUnread", False)):
            return False
        if criteria.get("hasAttachments") and not (message.get("attachments") or []):
            return False
        if labels and not labels.intersection({str(item).lower() for item in message.get("labels") or []}):
            return False
        if tags and not tags.intersection({str(item).lower() for item in message.get("tags") or []}):
            return False
        if criteria.get("importance"):
            if str(criteria.get("importance")).lower() != str(message.get("importance") or message.get("priority") or "").lower():
                return False
        dateFrom = str(criteria.get("dateFrom") or "")
        dateTo = str(criteria.get("dateTo") or "")
        stamp = str(message.get("receivedAt") or message.get("sentAt") or "")
        if dateFrom and stamp and stamp < dateFrom:
            return False
        if dateTo and stamp and stamp > dateTo:
            return False
        haystack = " ".join(
            [
                str(message.get("subject") or ""),
                str(message.get("snippet") or ""),
                str(message.get("body") or ""),
                str(message.get("sender") or ""),
            ]
        ).lower()
        for keyword in keywords:
            if keyword not in haystack:
                return False
        return True

    @staticmethod
    def _asDict(message):
        return message.asDict() if hasattr(message, "asDict") else dict(message or {})
