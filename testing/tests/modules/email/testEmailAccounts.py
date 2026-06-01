"""Email account and module contract tests."""

from __future__ import annotations

import unittest

from modules.email import EmailModule
from modules.email.models import EmailProviderType
from testing.tests.modules.email.helpers import build_email_context


EXPECTED_TOOL_NAMES = [
    "email.listAccounts",
    "email.connectAccount",
    "email.setDefaultAccount",
    "email.listInbox",
    "email.readEmail",
    "email.searchEmails",
    "email.listDrafts",
    "email.createDraft",
    "email.updateDraft",
    "email.sendEmail",
    "email.scheduleEmail",
    "email.listLabels",
    "email.applyLabel",
    "email.filterEmails",
    "email.sortEmails",
    "email.deleteEmail",
    "email.archiveEmail",
]


class EmailAccountTests(unittest.TestCase):
    """Validate account management and the module contract."""

    def tearDown(self):
        pass

    def test_module_exposes_expected_tools_and_permissions(self):
        module = EmailModule()
        toolNames = {tool.name for tool in module.getTools()}

        self.assertEqual(module.metadata.name, "email")
        self.assertIn("email.read", module.metadata.capabilities)
        self.assertIn("email.send", module.metadata.capabilities)
        self.assertTrue(toolNames.issuperset(EXPECTED_TOOL_NAMES))

    def test_multiple_accounts_connect_and_default_account_is_tracked(self):
        context = build_email_context()
        module = EmailModule(context)

        gmail = module.connectAccount(
            emailAddress="nova@gmail.com",
            displayName="Nova Gmail",
            providerType=EmailProviderType.GMAIL,
            isDefault=True,
        )
        outlook = module.connectAccount(
            emailAddress="nova@outlook.com",
            displayName="Nova Outlook",
            providerType=EmailProviderType.OUTLOOK,
        )
        accounts = module.listAccounts()

        self.assertEqual(gmail["providerType"], EmailProviderType.GMAIL)
        self.assertEqual(outlook["providerType"], EmailProviderType.OUTLOOK)
        self.assertEqual(len(accounts), 2)
        self.assertTrue(any(account["isDefault"] for account in accounts))
        self.assertTrue(module.snapshot()["accounts"])
        self.assertGreaterEqual(len(context.eventManager.events), 2)

    def test_account_views_render_compact_payloads(self):
        context = build_email_context()
        module = EmailModule(context)
        module.connectAccount(emailAddress="nova@gmail.com", displayName="Nova Gmail", providerType=EmailProviderType.GMAIL, isDefault=True)

        accountView = module.getAccountView()
        inboxView = module.getInboxView(limit=5)

        self.assertIn("accounts", accountView)
        self.assertIn("messages", inboxView)
        self.assertGreaterEqual(inboxView["count"], 1)


if __name__ == "__main__":
    unittest.main()
