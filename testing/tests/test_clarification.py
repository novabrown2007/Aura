"""Tests for Aura clarification and ambiguity resolution."""

from __future__ import annotations

import unittest
from types import SimpleNamespace

from assistant.clarification import AmbiguityDetector, ClarificationManager, ClarificationOption, ClarificationResponseBuilder
from core.conversation import ConversationManager
from core.threading.events.eventManager import EventManager
from testing.tests.support.fakes import make_context


class ClarificationTests(unittest.TestCase):
    """Validate ambiguity detection, clarification sessions, and structured responses."""

    def makeContext(self):
        context = make_context()
        context.eventManager = EventManager(context)
        context.config._data["clarification"] = {
            "clarificationEnabled": True,
            "clarificationTimeoutSeconds": 60,
            "allowMultipleClarificationAttempts": True,
            "maxClarificationAttempts": 3,
            "clarificationUiEnabled": True,
            "clarificationVoiceEnabled": True,
        }
        context.conversationManager = ConversationManager(context)
        return context

    def test_ambiguity_detector_flags_missing_parameters(self):
        """Missing parameters should produce a natural clarification request."""

        context = self.makeContext()
        detector = AmbiguityDetector(context)

        result = detector.detect(
            {
                "intent": "lights.turnOn",
                "arguments": {},
                "confidence": 0.98,
                "metadata": {"requiredParameters": ["room"]},
            }
        )

        self.assertTrue(result.ambiguous)
        self.assertEqual(result.requiredParameter, "room")
        self.assertIn("room", result.question.lower())

    def test_clarification_manager_creates_structured_session_and_response(self):
        """Requested clarifications should update conversation state and build followup responses."""

        context = self.makeContext()
        manager = ClarificationManager(context, conversationContext=context.conversationManager.context)
        response = manager.start("Which room would you like me to turn the lights on in?", {"intent": "lights.turnOn"}, "room")

        self.assertIn("response", response)
        self.assertTrue(response["payload"]["spokenText"])
        self.assertTrue(context.conversationManager.snapshot()["pendingClarification"]["active"])
        self.assertGreaterEqual(manager.snapshot()["activeCount"], 1)
        self.assertEqual(response["payload"]["followups"][0]["kind"], "clarification")
        self.assertEqual(response["payload"]["followups"][0]["metadata"]["requiredParameter"], "room")

    def test_clarification_resolution_completes_pending_session(self):
        """A short follow-up reply should resolve the active clarification session."""

        context = self.makeContext()
        manager = context.clarificationManager
        started = manager.start("Which room would you like me to turn the lights on in?", {"intent": "lights.turnOn"}, "room")
        sessionId = started["session"].sessionId

        resolved = manager.resolveResponse("Bedroom", sessionId=sessionId)
        context.conversationManager.completeClarification()

        self.assertTrue(resolved["resolved"])
        self.assertEqual(resolved["result"]["value"], "bedroom")
        self.assertFalse(context.conversationManager.snapshot()["pendingClarification"]["active"])
        self.assertEqual(manager.snapshot()["activeCount"], 0)

    def test_clarification_response_builder_preserves_options_and_notes(self):
        """Structured clarification responses should carry selectable options and notes."""

        context = self.makeContext()
        builder = ClarificationResponseBuilder(context, context.conversationManager.clarifications.contextManager)
        request = SimpleNamespace(
            asDict=lambda: {
                "requestId": "req-1",
                "conversationId": "default",
                "question": "Which playlist would you like?",
                "options": [
                    ClarificationOption(label="Coding", value="coding").asDict(),
                    ClarificationOption(label="Focus", value="focus").asDict(),
                ],
                "clarificationType": "MULTIPLE_OPTIONS",
                "requiredParameter": "playlist",
                "metadata": {"source": "spotify"},
            }
        )

        response = builder.buildRequestResponse(request)

        self.assertEqual(response.spokenText, "Which playlist would you like?")
        self.assertEqual(response.followups[0].options[0]["label"], "Coding")
        self.assertIn("clarification", response.metadata.notes)
        self.assertEqual(response.metadata.notes["clarification"]["requiredParameter"], "playlist")

    def test_timeout_and_cancel_paths_leave_safe_state(self):
        """Timeout and cancel operations should clear active sessions without errors."""

        context = self.makeContext()
        manager = context.clarificationManager
        started = manager.start("Which room would you like me to turn the lights on in?", {"intent": "lights.turnOn"}, "room")
        sessionId = started["session"].sessionId

        timedOut = manager.timeout(sessionId)
        self.assertTrue(timedOut["timedOut"])
        self.assertEqual(manager.snapshot()["activeCount"], 0)

        restarted = manager.start("Which room would you like me to turn the lights on in?", {"intent": "lights.turnOn"}, "room")
        sessionId = restarted["session"].sessionId
        cancelled = manager.cancel(sessionId, reason="Cancelled by user")
        self.assertTrue(cancelled["cancelled"])
        self.assertEqual(manager.snapshot()["activeCount"], 0)


if __name__ == "__main__":
    unittest.main()
