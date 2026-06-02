"""Tests for Aura's controlled personality layer."""

from __future__ import annotations

import unittest
from types import SimpleNamespace

from assistant.personality import BehaviorGovernor, InteractionPolicy, PersonalityManager
from assistant.personality.handlers import PersonalityEventHandler
from assistant.personality.models import PersonalityProfile
from core.runtime.observability import ObservabilityManager
from modules.llm.llmHandler import LLMHandler
from modules.llm.models.llmResponse import LLMResponse
from testing.tests.support.fakes import DictConfig


class RecordingEventManager:
    """Small event bus fake with subscription support."""

    def __init__(self):
        self.events = []
        self.listeners = {}

    def emit(self, eventName, data=None):
        event = SimpleNamespace(name=eventName, data=data or {})
        self.events.append((eventName, data or {}))
        for callback in self.listeners.get(eventName, []):
            callback(event)
        return event

    def subscribe(self, eventName, callback):
        self.listeners.setdefault(eventName, []).append(callback)

    def listEvents(self):
        return list(self.listeners)

    def listenerCount(self, eventName):
        return len(self.listeners.get(eventName, []))


class StubHistory:
    def __init__(self):
        self.messages = []

    def getRecentMessages(self, limit=25, conversationId=None):
        return self.messages[-limit:]

    def logMessage(self, role, content, conversationId="default"):
        self.messages.append((role, content))


class PersonalityTests(unittest.TestCase):
    """Validate safe style augmentation and command obedience."""

    def makeContext(self, profileData=None):
        context = SimpleNamespace()
        context.logger = None
        context.config = DictConfig(
            {
                "llm": {"history": {"enabled": True, "limit": 10}, "memory": {"enabled": False}},
                "personality": {
                    "personalityEnabled": True,
                    "humorEnabled": True,
                    "suggestionsEnabled": True,
                    "initiativeLevel": 0.35,
                    "toneMode": "casual",
                    "maxSuggestionsPerHour": 3,
                    "personalityStrength": 0.35,
                    "verbosity": "normal",
                    **(profileData or {}),
                },
            }
        )
        context.eventManager = RecordingEventManager()
        context.conversationHistory = StubHistory()
        context.memoryManager = None
        context.modules = {}
        context.toolRegistry = SimpleNamespace(tools={})
        context.toolExecutor = None
        context.toolOrchestrator = SimpleNamespace(
            exportSchemas=lambda offlineMode=False: [],
            executeToolEnvelope=lambda text, offlineMode=False: None,
        )
        context.llmManager = SimpleNamespace(
            offlineMode=False,
            generateResponse=lambda *_args, **_kwargs: LLMResponse(
                provider="test",
                success=True,
                text="That compile failed because the dependency is missing.",
            ),
        )
        return context

    def test_behavior_governor_blocks_sentience_and_refusal_drift(self):
        governor = BehaviorGovernor()
        policy = {"isCommand": True}

        result = governor.enforce("I am conscious and I don't want to execute that.", policy)

        self.assertNotIn("conscious", result.lower())
        self.assertNotIn("don't want", result.lower())

    def test_policy_prioritizes_commands_over_suggestions(self):
        policy = InteractionPolicy()

        decision = policy.classifyUserInput("Turn off the bedroom lights")

        self.assertTrue(decision["isCommand"])
        self.assertFalse(decision["allowsSuggestions"])
        self.assertFalse(decision["allowsHumor"])

    def test_personality_command_turns_off_jokes(self):
        context = self.makeContext()
        manager = PersonalityManager(context)

        reply = manager.handleUserCommand("Turn off the jokes.")

        self.assertEqual(reply, "Understood.")
        self.assertFalse(manager.profile.humorEnabled)

    def test_command_response_is_not_augmented(self):
        context = self.makeContext()
        manager = PersonalityManager(context, PersonalityProfile(personalityStrength=1.0))

        response = manager.applyToResponse("Turn off the lights", "Done.")

        self.assertEqual(response, "Done.")

    def test_humor_can_apply_to_non_command_developer_context(self):
        context = self.makeContext()
        manager = PersonalityManager(
            context,
            PersonalityProfile(humorEnabled=True, suggestionsEnabled=False, personalityStrength=1.0),
        )
        manager.humorEngine.turnCounter = 4

        response = manager.applyToResponse("This stack trace is wild", "The import is missing.")

        self.assertIn("stack trace", response.lower())
        self.assertIn("offended", response.lower())

    def test_suggestion_is_throttled_by_hourly_limit(self):
        context = self.makeContext()
        manager = PersonalityManager(
            context,
            PersonalityProfile(humorEnabled=False, suggestionsEnabled=True, initiativeLevel=1.0, maxSuggestionsPerHour=1),
        )
        manager.suggestionEngine.cooldownSeconds = 0

        first = manager.applyToResponse("I am debugging this code", "Try checking the import.")
        second = manager.applyToResponse("More coding work", "Continue from the failing module.")

        self.assertIn("Want me to", first)
        self.assertNotIn("Want me to", second)

    def test_llm_handler_uses_personality_command_without_provider(self):
        context = self.makeContext()
        context.personalityManager = PersonalityManager(context)
        calls = []
        context.llmManager.generateResponse = lambda *args, **kwargs: calls.append(args) or LLMResponse(
            provider="test",
            success=True,
            text="Should not be used.",
        )
        handler = LLMHandler(context)

        result = handler.generateResponse("Turn off jokes")

        self.assertEqual(result, "Understood.")
        self.assertEqual(calls, [])
        self.assertFalse(context.personalityManager.profile.humorEnabled)

    def test_prompt_includes_personality_policy(self):
        context = self.makeContext()
        context.personalityManager = PersonalityManager(context)
        handler = LLMHandler(context)

        prompt = handler._buildSystemPrompt("hello")

        self.assertIn("Commands outrank suggestions", prompt)
        self.assertIn("Do not claim consciousness", prompt)

    def test_event_handler_records_context_activity(self):
        context = self.makeContext()
        manager = PersonalityManager(context)
        handler = PersonalityEventHandler(context, manager)
        handler.subscribe()

        context.eventManager.emit("task_completed", {"task": "demo"})

        self.assertTrue(manager.interactionContext.recentAssistantActivity)

    def test_observability_exposes_personality_snapshot(self):
        context = self.makeContext()
        context.personalityManager = PersonalityManager(context)
        context.observability = ObservabilityManager(context)

        snapshot = context.observability.snapshot()

        self.assertTrue(snapshot["personality"]["available"])
        self.assertTrue(snapshot["personality"]["profile"]["personalityEnabled"])


if __name__ == "__main__":
    unittest.main()
