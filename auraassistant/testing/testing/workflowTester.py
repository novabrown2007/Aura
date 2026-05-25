"""Workflow test helpers for assistant ecosystem simulations."""

from __future__ import annotations

from typing import Any


class WorkflowTester:
    """Test conversational continuity, notifications, and stream flows."""

    def __init__(self, context=None, simulator=None, tracer=None):
        self.context = context
        self.simulator = simulator
        self.tracer = tracer
        self.logger = context.logger.getChild("Testing.Workflow") if context and getattr(context, "logger", None) else None

    def runConversationWorkflow(self, text: str, sessionId: str = ""):
        """Run a text conversation workflow."""

        if self.simulator is not None:
            return self.simulator.simulateTextConversation(text, sessionId=sessionId)
        if self.logger:
            self.logger.debug("Workflow tester has no simulator; echoing text.")
        return {"input": text, "response": text}

    def runNotificationWorkflow(self, notification: dict[str, Any], sessionId: str = ""):
        """Run a notification-driven workflow."""

        if self.simulator is not None:
            return self.simulator.simulateNotificationWorkflow(notification, sessionId=sessionId)
        return {"notification": dict(notification), "response": ""}

    def runStreamWorkflow(self, stream: dict[str, Any], sessionId: str = ""):
        """Run a stream-request workflow."""

        if self.simulator is not None:
            return self.simulator.simulateStreamWorkflow(stream, sessionId=sessionId)
        return {"stream": dict(stream), "response": ""}

    def runSessionWorkflow(self, sessionId: str, interface: str = "desktop"):
        """Run a session synchronization workflow."""

        if self.simulator is not None:
            return self.simulator.syncSession(sessionId=sessionId, interface=interface)
        return {"sessionId": sessionId, "interface": interface}

    def runFullWorkflow(self, text: str, notification: dict[str, Any] | None = None, stream: dict[str, Any] | None = None, sessionId: str = "", interface: str = "desktop"):
        """Run a combined workflow to validate orchestration continuity."""

        results = {
            "conversation": self.runConversationWorkflow(text, sessionId=sessionId),
            "session": self.runSessionWorkflow(sessionId or "session001", interface=interface),
        }
        if notification is not None:
            results["notification"] = self.runNotificationWorkflow(notification, sessionId=sessionId)
        if stream is not None:
            results["stream"] = self.runStreamWorkflow(stream, sessionId=sessionId)
        return results
