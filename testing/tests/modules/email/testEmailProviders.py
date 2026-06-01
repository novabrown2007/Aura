"""Provider behavior tests for Aura email."""

from __future__ import annotations

import unittest

from modules.email.models import EmailAccount, EmailProviderType
from modules.email.providers import GmailProvider, ImapSmtpProvider, OutlookProvider
from testing.tests.modules.email.helpers import build_email_context


class EmailProviderTests(unittest.TestCase):
    """Validate the provider abstraction across supported backends."""

    def test_provider_connection_search_and_send(self):
        context = build_email_context()
        account = EmailAccount(accountId="gmail-nova", emailAddress="nova@gmail.com", displayName="Nova", providerType=EmailProviderType.GMAIL)
        provider = GmailProvider(context).initialize(context)
        provider.connectAccount(account)

        inbox = provider.listInbox(account.accountId)
        search = provider.searchEmails(account.accountId, "welcome")
        draft = provider.createDraft(account.accountId, {"to": ["john@example.com"], "subject": "Hi", "body": "Hello"})
        sent = provider.sendEmail(account.accountId, draft)

        self.assertGreaterEqual(len(inbox), 1)
        self.assertGreaterEqual(len(search), 1)
        self.assertTrue(sent["messageId"])

    def test_outlook_and_imap_providers_are_available(self):
        context = build_email_context()
        outlook = OutlookProvider(context).initialize(context)
        imap = ImapSmtpProvider(context).initialize(context)

        self.assertTrue(outlook.isAvailable())
        self.assertTrue(imap.isAvailable())

    def test_provider_failure_does_not_crash_module(self):
        context = build_email_context()
        provider = GmailProvider(context).initialize(context)
        provider.available = False

        self.assertFalse(provider.isAvailable())


if __name__ == "__main__":
    unittest.main()
