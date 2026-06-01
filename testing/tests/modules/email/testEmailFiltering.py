"""Filtering and sorting tests for Aura email."""

from __future__ import annotations

import unittest

from modules.email import EmailModule
from modules.email.models import EmailProviderType
from testing.tests.modules.email.helpers import build_email_context


class EmailFilteringTests(unittest.TestCase):
    """Validate inbox filtering and sorting utilities."""

    def test_filter_by_sender_and_keywords(self):
        context = build_email_context()
        module = EmailModule(context)
        account = module.connectAccount(emailAddress="nova@gmail.com", displayName="Nova Gmail", providerType=EmailProviderType.GMAIL, isDefault=True)

        filtered = module.filterEmails(accountId=account["accountId"], sender="support@example.com", keywords=["welcome"])

        self.assertEqual(len(filtered), 1)
        self.assertIn("support@example.com", filtered[0]["sender"])

    def test_sorting_helpers_return_most_recent_first(self):
        context = build_email_context()
        module = EmailModule(context)
        account = module.connectAccount(emailAddress="nova@gmail.com", displayName="Nova Gmail", providerType=EmailProviderType.GMAIL, isDefault=True)

        newest = module.sortEmails(accountId=account["accountId"], sortMode="NEWEST_FIRST")
        oldest = module.sortEmails(accountId=account["accountId"], sortMode="OLDEST_FIRST")

        self.assertGreaterEqual(len(newest), 1)
        self.assertGreaterEqual(len(oldest), 1)
        self.assertNotEqual(newest[0]["messageId"], oldest[0]["messageId"])


if __name__ == "__main__":
    unittest.main()
