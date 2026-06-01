"""Single email message view payload."""

from __future__ import annotations


class EmailMessageView:
    """Render one email message for the desktop layer."""

    def __init__(self, message=None):
        self.message = dict(message or {})

    def render(self):
        message = self.message
        return {
            "title": message.get("subject") or "Email",
            "sender": message.get("sender") or "",
            "recipients": list(message.get("recipients") or []),
            "cc": list(message.get("cc") or []),
            "bcc": list(message.get("bcc") or []),
            "body": message.get("body") or message.get("snippet") or "",
            "labels": list(message.get("labels") or []),
            "attachments": list(message.get("attachments") or []),
            "accountId": message.get("accountId") or "",
            "messageId": message.get("messageId") or "",
        }
