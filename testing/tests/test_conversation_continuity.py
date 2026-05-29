"""Tests for Aura conversational continuity."""

from __future__ import annotations

from types import SimpleNamespace
import unittest

from assistant.conversation import ConversationManager
from core.runtime.observability import ObservabilityManager
from core.threading.events.eventManager import EventManager
from modules.llm.llmHandler import LLMHandler
from modules.llm.models.llmResponse import LLMResponse
from testing.tests.support.fakes import DictConfig, make_context


class ConversationContinuityTests(unittest.TestCase):
    """Validate short-term follow-up and reference resolution."""

    def makeContext(self):
        context = make_context()
        context.eventManager = EventManager(context)
        context.config._data["conversation"] = {"conversationTimeoutSeconds": 300}
        return context

    def test_pronoun_followup_resolves_to_active_light_entity(self):
        context = self.makeContext()
        manager = ConversationManager(context)

        first = manager.preprocessInput("Turn off the bedroom lights.")
        manager.recordAction("lights.turnOff", {"room": "bedroom"}, {"success": True})
        second = manager.preprocessInput("Actually make them blue.")

        self.assertEqual(first, "Turn off the bedroom lights.")
        self.assertIn("bedroom lights", second.lower())
        self.assertIn("blue", second.lower())
        self.assertEqual(manager.snapshot()["activeTopic"]["name"], "lighting")
        self.assertEqual(manager.snapshot()["activeEntity"]["name"], "bedroom lights")

    def test_incremental_lighting_modification_uses_previous_entity(self):
        context = self.makeContext()
        manager = ConversationManager(context)

        manager.preprocessInput("Set the bedroom lights to 50%.")
        manager.recordAction("lights.setBrightness", {"room": "bedroom", "brightness": 50}, {"success": True})
        resolved = manager.preprocessInput("And dim them more.")

        self.assertIn("dim bedroom lights", resolved.lower())
        self.assertEqual(manager.snapshot()["followupChainLength"], 1)

    def test_music_pronoun_resolves_to_current_playback(self):
        context = self.makeContext()
        manager = ConversationManager(context)

        manager.preprocessInput("Play jazz.")
        manager.recordAction("music.play", {"genre": "jazz"}, {"success": True})
        resolved = manager.preprocessInput("Turn it down.")

        self.assertIn("music playback", resolved.lower())
        self.assertEqual(manager.snapshot()["activeTopic"]["name"], "music")

    def test_context_expiration_resets_stale_entities(self):
        context = self.makeContext()
        context.config = DictConfig({"conversation": {"conversationTimeoutSeconds": 1}})
        manager = ConversationManager(context)
        manager.preprocessInput("Turn off the bedroom lights.")
        manager.recordAction("lights.turnOff", {"room": "bedroom"}, {"success": True})

        manager.context.state.expiresAt = 0
        resolved = manager.preprocessInput("Make them blue.")

        self.assertEqual(resolved, "Make them blue.")
        self.assertEqual(manager.snapshot()["followupChainLength"], 0)

    def test_clarification_state_is_exposed_and_completed(self):
        context = self.makeContext()
        manager = ConversationManager(context)

        manager.startClarification("Which room?", {"intent": "lights.turnOn"}, "room")
        self.assertTrue(manager.snapshot()["pendingClarification"]["active"])

        manager.completeClarification()
        self.assertFalse(manager.snapshot()["pendingClarification"]["active"])

    def test_llm_handler_sends_resolved_text_to_provider(self):
        context = self.makeContext()
        context.conversationManager = ConversationManager(context)
        captured = []
        context.llmManager = SimpleNamespace(
            offlineMode=False,
            generateResponse=lambda _prompt, userInput, _history=None: captured.append(userInput)
            or LLMResponse(provider="test", success=True, text="Done."),
        )
        handler = LLMHandler(context)

        handler.generateResponse("Turn off the bedroom lights.")
        context.conversationManager.recordAction("lights.turnOff", {"room": "bedroom"}, {"success": True})
        handler.generateResponse("Actually make them blue.")

        self.assertIn("bedroom lights", captured[-1].lower())
        self.assertIn("blue", captured[-1].lower())

    def test_observability_exposes_conversation_context(self):
        context = self.makeContext()
        manager = ConversationManager(context)
        manager.preprocessInput("Turn off the bedroom lights.")
        context.observability = ObservabilityManager(context)

        snapshot = context.observability.snapshot()

        self.assertTrue(snapshot["conversation"]["available"])
        self.assertEqual(snapshot["conversation"]["activeTopic"]["name"], "lighting")


if __name__ == "__main__":
    unittest.main()
