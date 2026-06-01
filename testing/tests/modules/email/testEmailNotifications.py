"""Email notification tests for Aura."""

from __future__ import annotations

import unittest

from modules.email import EmailModule
from modules.email.models import EmailProviderType
from testing.tests.modules.email.helpers import build_email_context


class EmailNotificationTests(unittest.TestCase):
    """Validate notification generation and deduplication."""

    def test_new_mail_triggers_notifications_once(self):
        context = build_email_context()
        module = EmailModule(context)
        module.connectAccount(emailAddress="nova@gmail.com", displayName="Nova Gmail", providerType=EmailProviderType.GMAIL, isDefault=True)

        first = module.pollNewMail()
        second = module.pollNewMail()

        self.assertGreaterEqual(len(first), 1)
        self.assertEqual(len(second), 0)
        self.assertGreaterEqual(len(context.notificationManager.created), 1)

    def test_notification_snapshot_exposes_activity(self):
        context = build_email_context()
        module = EmailModule(context)
        module.connectAccount(emailAddress="nova@gmail.com", displayName="Nova Gmail", providerType=EmailProviderType.GMAIL, isDefault=True)
        module.pollNewMail()

        snapshot = module.snapshot()

        self.assertIn("notifications", snapshot)
        self.assertGreaterEqual(snapshot["notifications"]["seenCount"], 1)


if __name__ == "__main__":
    unittest.main()
