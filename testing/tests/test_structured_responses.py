"""Tests for Aura's structured assistant response system."""

from __future__ import annotations

from types import SimpleNamespace
import unittest

from assistant.responses import AssistantResponse, ResponseManager, ResponseValidator
from modules.llm.llmHandler import LLMHandler
from modules.llm.models.llmResponse import LLMResponse
from testing.tests.support.fakes import DictConfig


class FakeEventBus:
    """Minimal event bus for structured response tests."""

    def __init__(self):
        self.events = []
        self.subscriptions = {}

    def subscribe(self, name, callback):
        self.subscriptions.setdefault(name, []).append(callback)

    def unsubscribe(self, name, callback):
        handlers = self.subscriptions.get(name, [])
        if callback in handlers:
            handlers.remove(callback)

    def emit(self, name, data=None):
        event = SimpleNamespace(name=name, data=dict(data or {}))
        self.events.append(event)
        for callback in list(self.subscriptions.get(name, [])):
            callback(event)
        return event


class FakeVoiceManager:
    """Record text routed to voice delivery."""

    def __init__(self):
        self.spoken = []

    def speakResponse(self, text):
        self.spoken.append(text)
        return {"success": True, "text": text}


class FakeOverlayManager:
    """Record UI updates routed to the desktop overlay."""

    def __init__(self):
        self.updates = []
        self.visible = False

    def updateAssistant(self, state, message=""):
        self.updates.append((state, message))

    def showBubble(self):
        self.visible = True


class FakeNotificationManager:
    """Record notifications routed through the assistant attention layer."""

    def __init__(self):
        self.created = []

    def createNotification(self, payload, eventName=""):
        payload = dict(payload or {})
        payload["eventName"] = eventName
        self.created.append(payload)
        return SimpleNamespace(asDict=lambda: dict(payload))


class FakeToolExecutor:
    """Record tool calls requested by structured response actions."""

    def __init__(self):
        self.calls = []

    def executeToolCall(self, toolName, arguments=None, offlineMode=False, confirmed=False, allowAdmin=False):
        call = {
            "toolName": toolName,
            "arguments": dict(arguments or {}),
            "offlineMode": bool(offlineMode),
            "confirmed": bool(confirmed),
            "allowAdmin": bool(allowAdmin),
        }
        self.calls.append(call)
        return {"success": True, "toolName": toolName, "result": {"ok": True}}


class StructuredResponseTests(unittest.TestCase):
    """Validate the response orchestration layer and LLM integration."""

    def _makeContext(self):
        context = SimpleNamespace()
        context.logger = None
        context.config = DictConfig(
            {
                "responses": {
                    "structuredResponsesEnabled": True,
                    "spokenResponseEnabled": True,
                    "uiResponseEnabled": True,
                    "responseMetadataEnabled": True,
                    "responseFollowupsEnabled": True,
                    "responseValidationEnabled": True,
                },
                "llm": {
                    "history": {"enabled": True, "limit": 5},
                    "memory": {"enabled": False},
                },
            }
        )
        context.eventManager = FakeEventBus()
        context.voiceManager = FakeVoiceManager()
        context.desktopOverlayManager = FakeOverlayManager()
        context.notificationManager = FakeNotificationManager()
        context.toolExecutor = FakeToolExecutor()
        context.toolOrchestrator = SimpleNamespace(
            exportSchemas=lambda **_kwargs: [],
            executeToolEnvelope=lambda *_args, **_kwargs: None,
        )
        context.conversationHistory = SimpleNamespace(getRecentMessages=lambda limit=5: [], logMessage=lambda *_args, **_kwargs: None)
        context.memoryManager = SimpleNamespace(injectPrompt=lambda prompt, userInput, conversationHistory=None: (prompt, {}))
        context.modules = {}
        return context

    def test_response_manager_routes_all_structured_surfaces(self):
        """The response manager should build and route a structured response packet."""

        context = self._makeContext()
        manager = ResponseManager(context)

        response = manager.createResponse(
            "Play Spotify.",
            providerResponse=LLMResponse(
                provider="gemini",
                success=True,
                text="Opening Spotify.",
                rawResponse={
                    "spokenText": "Opening Spotify.",
                    "uiText": "Opening Spotify in the overlay.",
                    "notifications": [
                        {
                            "title": "Media",
                            "message": "Spotify opened.",
                            "priority": "LOW",
                        }
                    ],
                    "actions": [
                        {
                            "target": "music.play",
                            "arguments": {"track": "Example"},
                        }
                    ],
                    "followups": [
                        {
                            "prompt": "Anything else?",
                        }
                    ],
                    "metadata": {
                        "confidence": 0.93,
                        "modulesInvolved": ["spotify"],
                        "intentsResolved": ["music.play"],
                    },
                },
            ),
        )

        self.assertIsInstance(response, AssistantResponse)
        self.assertEqual(response.spokenText, "Opening Spotify.")
        self.assertEqual(response.uiText, "Opening Spotify in the overlay.")
        self.assertEqual(response.metadata.provider, "gemini")
        self.assertEqual(response.metadata.confidence, 0.93)
        self.assertEqual(response.metadata.modulesInvolved, ["spotify"])
        self.assertEqual(response.followups[0].prompt, "Anything else?")
        self.assertEqual(context.voiceManager.spoken, ["Opening Spotify."])
        self.assertEqual(context.desktopOverlayManager.updates[-1], ("RESPONDING", "Opening Spotify in the overlay."))
        self.assertEqual(len(context.notificationManager.created), 1)
        self.assertEqual(len(context.toolExecutor.calls), 1)
        self.assertIn("response.created", [event.name for event in context.eventManager.events])
        self.assertIn("response.delivered", [event.name for event in context.eventManager.events])
        self.assertEqual(manager.snapshot()["lastResponse"]["spokenText"], "Opening Spotify.")

    def test_llm_handler_returns_text_and_preserves_structured_response(self):
        """The legacy LLM handler should still return text while storing a structured packet."""

        context = self._makeContext()
        context.llmManager = SimpleNamespace(
            offlineMode=False,
            generateResponse=lambda *_args, **_kwargs: LLMResponse(
                provider="gemini",
                success=True,
                text="Opening Spotify.",
                rawResponse={
                    "spokenText": "Opening Spotify.",
                    "uiText": "Opening Spotify in the overlay.",
                    "followups": [{"prompt": "Anything else?"}],
                },
            ),
        )

        handler = LLMHandler(context)
        result = handler.generateResponse("Play Spotify.")

        self.assertEqual(result, "Opening Spotify.")
        self.assertIsNotNone(handler.lastStructuredResponse)
        self.assertEqual(handler.lastStructuredResponse.uiText, "Opening Spotify in the overlay.")
        self.assertEqual(handler.lastStructuredResponse.followups[0].prompt, "Anything else?")
        self.assertIn("response.created", [event.name for event in context.eventManager.events])

    def test_response_validator_rejects_empty_packets(self):
        """Empty response packets should fail validation."""

        validator = ResponseValidator(self._makeContext())
        valid, errors = validator.validate(AssistantResponse())

        self.assertFalse(valid)
        self.assertGreaterEqual(len(errors), 1)


if __name__ == "__main__":
    unittest.main()
