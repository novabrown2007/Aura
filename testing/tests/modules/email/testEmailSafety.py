"""Safety enforcement tests for Aura email."""

from __future__ import annotations

import unittest

from assistant.safety import SafetyManager
from core.tools.tool import Tool
from core.tools.toolExecutor import ToolExecutor
from core.tools.toolRegistry import ToolRegistry
from modules.email import EmailModule
from modules.email.models import EmailProviderType
from testing.tests.modules.email.helpers import build_email_context


class EmailSafetyTests(unittest.TestCase):
    """Validate confirmation gating for sensitive email actions."""

    def setUp(self):
        self.context = build_email_context()
        self.context.toolRegistry = ToolRegistry(self.context)
        self.context.toolExecutor = ToolExecutor(self.context)
        self.context.safetyManager = SafetyManager(self.context)
        self.module = EmailModule(self.context)
        self.context.email = self.module
        self.account = self.module.connectAccount(emailAddress="nova@gmail.com", displayName="Nova Gmail", providerType=EmailProviderType.GMAIL, isDefault=True)
        self.draft = self.module.createDraft(accountId=self.account["accountId"], to=["john@example.com"], subject="Hello", body="Hi there.")
        for tool in self.module.getTools():
            self.context.toolRegistry.registerTool(tool)

    def test_send_requires_confirmation_and_then_executes(self):
        initial = self.context.toolExecutor.executeToolCall(
            "email.sendEmail",
            {"accountId": self.account["accountId"], "draftId": self.draft["draftId"]},
        )

        self.assertFalse(initial["success"])
        self.assertTrue(initial["requiresConfirmation"])
        requestId = next(iter(self.context.safetyManager.pendingConfirmations.keys()))
        confirmed = self.context.safetyManager.confirm(requestId, approved=True)

        self.assertTrue(confirmed["success"])
        self.assertTrue(any(event["name"] == "email.sent" for event in self.context.eventManager.events))

    def test_delete_requires_confirmation(self):
        message = self.module.listInbox(accountId=self.account["accountId"], limit=1)[0]
        initial = self.context.toolExecutor.executeToolCall(
            "email.deleteEmail",
            {"accountId": self.account["accountId"], "messageId": message["messageId"]},
        )

        self.assertFalse(initial["success"])
        self.assertTrue(initial["requiresConfirmation"])


if __name__ == "__main__":
    unittest.main()
