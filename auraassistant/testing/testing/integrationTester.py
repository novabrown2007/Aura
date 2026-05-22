"""Integration testing helpers for the assistant ecosystem."""

from __future__ import annotations

from typing import Any


class IntegrationTester:
    """Run deterministic end-to-end assistant integration checks."""

    def __init__(self, context=None, simulator=None, tracer=None, voiceTester=None, workflowTester=None):
        self.context = context
        self.simulator = simulator
        self.tracer = tracer
        self.voiceTester = voiceTester
        self.workflowTester = workflowTester
        self.logger = context.logger.getChild("Testing.Integration") if context and getattr(context, "logger", None) else None

    def testVoiceFlow(self, text: str, sessionId: str = "", speak: bool = False):
        """Test voice input -> assistant response flow."""

        if self.voiceTester is not None:
            return self.voiceTester.simulatePushToTalk(text)
        if self.simulator is None:
            return {"success": False, "error": "No simulator configured."}
        return self.simulator.simulateVoiceConversation(text, sessionId=sessionId, speak=speak)

    def testNotificationFlow(self, notification: dict[str, Any], sessionId: str = ""):
        """Test notification -> assistant awareness flow."""

        if self.simulator is None:
            return {"success": False, "error": "No simulator configured."}
        return self.simulator.simulateNotificationWorkflow(notification, sessionId=sessionId)

    def testWorkflowFlow(self, text: str, notification: dict[str, Any] | None = None, sessionId: str = ""):
        """Run a combined workflow pass."""

        if self.workflowTester is not None:
            results = {"conversation": self.workflowTester.runConversationWorkflow(text, sessionId=sessionId)}
            if notification is not None:
                results["notification"] = self.workflowTester.runNotificationWorkflow(notification, sessionId=sessionId)
            return results
        return self.runFullIntegration(text, notification=notification, sessionId=sessionId)

    def runFullIntegration(self, text: str, notification: dict[str, Any] | None = None, sessionId: str = ""):
        """Run a full assistant integration pass."""

        results = {
            "voice": self.testVoiceFlow(text, sessionId=sessionId),
        }
        if notification is not None:
            results["notification"] = self.testNotificationFlow(notification, sessionId=sessionId)
        return results
