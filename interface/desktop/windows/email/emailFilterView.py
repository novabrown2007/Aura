"""Filter controls payload for the Windows interface."""

from __future__ import annotations


class EmailFilterView:
    """Render email filter controls."""

    def render(self):
        return {
            "title": "Filters",
            "controls": [
                "sender",
                "recipient",
                "labels",
                "tags",
                "unreadOnly",
                "hasAttachments",
                "keywords",
                "dateRange",
                "importance",
            ],
        }
