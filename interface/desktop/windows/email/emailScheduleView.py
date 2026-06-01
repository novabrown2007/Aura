"""Scheduled email payload for the Windows interface."""

from __future__ import annotations


class EmailScheduleView:
    """Render scheduled email items."""

    def __init__(self, scheduledEmails=None):
        self.scheduledEmails = list(scheduledEmails or [])

    def render(self):
        return {
            "title": "Scheduled Emails",
            "count": len(self.scheduledEmails),
            "scheduledEmails": [
                {
                    "scheduledEmailId": item.get("scheduledEmailId"),
                    "sendAt": item.get("sendAt"),
                    "state": item.get("state"),
                    "subject": (item.get("draft") or {}).get("subject") if isinstance(item.get("draft"), dict) else "",
                    "accountId": (item.get("draft") or {}).get("accountId") if isinstance(item.get("draft"), dict) else "",
                }
                for item in self.scheduledEmails
            ],
        }
