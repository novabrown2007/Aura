"""Inbox reading and search tests for Aura email."""

from __future__ import annotations

import unittest

from modules.email import EmailModule
from modules.email.models import EmailProviderType
from testing.tests.modules.email.helpers import build_email_context


class InboxReadingTests(unittest.TestCase):
    """Validate inbox listing, reading, and search behavior."""

    def test_inbox_listing_reading_and_search(self):
        context = build_email_context()
        module = EmailModule(context)
        account = module.connectAccount(
            emailAddress="nova@gmail.com",
            displayName="Nova Gmail",
            providerType=EmailProviderType.GMAIL,
            isDefault=True,
        )

        inbox = module.listInbox(accountId=account["accountId"], limit=10)
        latest = inbox[0]
        message = module.readEmail(account["accountId"], latest["messageId"])
        search = module.searchEmails("welcome", accountId=account["accountId"], limit=10)
        unread = module.listUnread(accountId=account["accountId"], limit=10)

        self.assertGreaterEqual(len(inbox), 1)
        self.assertFalse(message["isUnread"])
        self.assertGreaterEqual(len(search), 1)
        self.assertLessEqual(len(unread), len(inbox))
        self.assertIn("body", module.getMessageView(account["accountId"], latest["messageId"]))

    def test_filter_and_sort_controls_work(self):
        context = build_email_context()
        module = EmailModule(context)
        account = module.connectAccount(
            emailAddress="nova@outlook.com",
            displayName="Nova Outlook",
            providerType=EmailProviderType.OUTLOOK,
            isDefault=True,
        )

        filtered = module.filterEmails(accountId=account["accountId"], unreadOnly=True)
        sorted_items = module.sortEmails(accountId=account["accountId"], sortMode="UNREAD_FIRST")

        self.assertGreaterEqual(len(filtered), 1)
        self.assertGreaterEqual(len(sorted_items), 1)
        self.assertIn("controls", module.getFilterView())


if __name__ == "__main__":
    unittest.main()
