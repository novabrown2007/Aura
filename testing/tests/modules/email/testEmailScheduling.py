"""Scheduled email tests for Aura email."""

from __future__ import annotations

import unittest

from modules.email import EmailModule
from modules.email.models import EmailProviderType
from testing.tests.modules.email.helpers import build_email_context


class EmailSchedulingTests(unittest.TestCase):
    """Validate future-send workflows and schedule integration."""

    def test_schedule_email_creates_schedule_item_and_completes_due_send(self):
        context = build_email_context()
        module = EmailModule(context)
        account = module.connectAccount(emailAddress="nova@gmail.com", displayName="Nova Gmail", providerType=EmailProviderType.GMAIL, isDefault=True)
        draft = module.createDraft(
            accountId=account["accountId"],
            to=["john@example.com"],
            subject="Tomorrow",
            body="See you tomorrow morning.",
        )

        scheduled = module.scheduleEmail(accountId=account["accountId"], draftId=draft["draftId"], sendAt="2000-01-01T00:00:00+00:00")
        sent = module.processScheduledEmails()
        scheduleView = module.getScheduleView()

        self.assertEqual(scheduled["state"], "PENDING")
        self.assertGreaterEqual(len(context.personalSchedule.created), 1)
        self.assertGreaterEqual(len(sent), 1)
        self.assertGreaterEqual(scheduleView["count"], 1)

    def test_handle_intent_schedules_email(self):
        context = build_email_context()
        module = EmailModule(context)
        account = module.connectAccount(emailAddress="nova@gmail.com", displayName="Nova Gmail", providerType=EmailProviderType.GMAIL, isDefault=True)
        draft = module.createDraft(accountId=account["accountId"], to=["john@example.com"], subject="Later", body="Send later.")

        response = module.handleIntent(
            type("Intent", (), {"name": "email.scheduleEmail", "arguments": {"accountId": account["accountId"], "draftId": draft["draftId"], "sendAt": "2000-01-01T00:00:00+00:00"}})()
        )

        self.assertIn("spokenText", response)
        self.assertIn("Email scheduled", response["spokenText"])


if __name__ == "__main__":
    unittest.main()
