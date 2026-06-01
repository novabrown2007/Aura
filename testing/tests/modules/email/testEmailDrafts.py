"""Draft creation and editing tests for Aura email."""

from __future__ import annotations

import unittest

from modules.email import EmailModule
from modules.email.models import EmailProviderType
from testing.tests.modules.email.helpers import build_email_context


class EmailDraftTests(unittest.TestCase):
    """Validate draft lifecycle and response shaping."""

    def test_create_and_update_draft(self):
        context = build_email_context()
        module = EmailModule(context)
        account = module.connectAccount(emailAddress="nova@gmail.com", displayName="Nova Gmail", providerType=EmailProviderType.GMAIL, isDefault=True)

        draft = module.createDraft(
            accountId=account["accountId"],
            to=["john@example.com"],
            subject="Check in",
            body="I will be there at 5.",
        )
        updated = module.updateDraft(draft["draftId"], body="I will be there at 5:30.")
        draftView = module.getDraftView(account["accountId"])
        response = module.manager.buildResponse("email.createDraft", {"draft": draft})

        self.assertEqual(draft["subject"], "Check in")
        self.assertIn("5:30", updated["body"])
        self.assertGreaterEqual(draftView["count"], 1)
        self.assertIn("spokenText", response)
        self.assertIn("followups", response)

    def test_blank_draft_prompts_for_followup(self):
        context = build_email_context()
        module = EmailModule(context)
        module.connectAccount(emailAddress="nova@gmail.com", displayName="Nova Gmail", providerType=EmailProviderType.GMAIL, isDefault=True)

        response = module.handleIntent("email.createDraft")

        self.assertIn("followups", response)
        self.assertGreaterEqual(len(response["followups"]), 1)


if __name__ == "__main__":
    unittest.main()
