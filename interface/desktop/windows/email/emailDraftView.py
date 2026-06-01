"""Draft list/editor payload for the Windows interface."""

from __future__ import annotations


class EmailDraftView:
    """Render draft state for the desktop layer."""

    def __init__(self, drafts=None):
        self.drafts = list(drafts or [])

    def render(self):
        return {
            "title": "Drafts",
            "count": len(self.drafts),
            "drafts": [
                {
                    "draftId": draft.get("draftId"),
                    "accountId": draft.get("accountId"),
                    "to": list(draft.get("to") or []),
                    "subject": draft.get("subject"),
                    "body": draft.get("body"),
                    "updatedAt": draft.get("updatedAt"),
                }
                for draft in self.drafts[:50]
            ],
        }
