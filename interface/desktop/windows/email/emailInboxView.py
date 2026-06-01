"""Compact inbox view payload for the Windows interface."""

from __future__ import annotations


class EmailInboxView:
    """Render a concise inbox payload for the desktop layer."""

    def __init__(self, messages=None, accounts=None):
        self.messages = list(messages or [])
        self.accounts = list(accounts or [])

    def render(self):
        return {
            "title": "Inbox",
            "count": len(self.messages),
            "accounts": len(self.accounts),
            "messages": [
                {
                    "messageId": message.get("messageId"),
                    "accountId": message.get("accountId"),
                    "sender": message.get("sender"),
                    "subject": message.get("subject"),
                    "snippet": message.get("snippet"),
                    "isUnread": bool(message.get("isUnread", False)),
                    "labels": list(message.get("labels") or []),
                }
                for message in self.messages[:50]
            ],
        }
