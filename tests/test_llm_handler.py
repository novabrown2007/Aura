"""Automated tests for `test_llm_handler` behavior and regression coverage."""

import os
import unittest
from types import SimpleNamespace
from unittest.mock import patch

import requests

from modules.llm.manager.llmManager import LLMManager
from modules.llm.models.llmResponse import LLMResponse
from modules.llm.llmHandler import LLMHandler
from tests.support.fakes import DictConfig


class DummyResponse:
    """Testing utility class used to simulate `DummyResponse` dependencies and behavior."""
    def __init__(self, status_code=200, payload=None, text=""):
        """Initialize `DummyResponse` with required dependencies and internal state."""
        self.status_code = status_code
        self._payload = payload or {}
        self.text = text

    def json(self):
        """Implement `json` as part of this component's public/internal behavior."""
        return self._payload


class StubHistory:
    """Testing utility class used to simulate `StubHistory` dependencies and behavior."""
    def __init__(self):
        """Initialize `StubHistory` with required dependencies and internal state."""
        self.messages = []

    def getRecentMessages(self, limit=25):
        """Return `getRecentMessages` data from the component's current state."""
        return self.messages[-limit:]

    def logMessage(self, author, content):
        """Implement `logMessage` as part of this component's public/internal behavior."""
        self.messages.append((author, content))


class StubMemory:
    """Testing utility class used to simulate `StubMemory` dependencies and behavior."""
    def __init__(self):
        """Initialize `StubMemory` with required dependencies and internal state."""
        self.learn_inputs = []
        self.memory = {"name": "Nova"}

    def learnFromMessage(self, text):
        """Implement `learnFromMessage` as part of this component's public/internal behavior."""
        self.learn_inputs.append(text)

    def getMemory(self):
        """Return `getMemory` data from the component's current state."""
        return self.memory


class StubProvider:
    """Small provider stub used to test manager routing behavior."""

    def __init__(self, provider_name, response):
        """Store provider identity and response returned by generation calls."""

        self.providerName = provider_name
        self.response = response
        self.initialized = True

    def initialize(self):
        """Mark provider initialized."""

        self.initialized = True

    def shutdown(self):
        """Mark provider shutdown."""

        self.initialized = False

    def generateResponse(self, systemPrompt, userPrompt, conversationHistory=None):
        """Return the configured plain response."""

        return self.response

    def generateStructuredResponse(self, systemPrompt, userPrompt, schema, conversationHistory=None):
        """Return the configured structured response."""

        return self.response


def make_llm_context(endpoint="http://localhost:11434/api/generate"):
    """Construct and return a configured helper object for tests/runtime wiring."""
    context = SimpleNamespace()
    context.logger = None
    context.config = DictConfig(
        {
            "llm": {
                "activeProvider": "ollama",
                "fallbackProvider": "ollama",
                "offlineMode": False,
                "endpoint": endpoint,
                "model": "llama3.1:8b",
                "timeout": 10,
                "retryCount": 1,
                "history": {"enabled": True, "limit": 10},
                "memory": {"enabled": True},
                "providers": {
                    "ollama": {
                        "endpoint": endpoint,
                        "model": "llama3.1:8b",
                    }
                },
            }
        }
    )
    context.conversationHistory = StubHistory()
    context.memoryManager = StubMemory()
    context.modules = {}
    return context


class LLMHandlerTests(unittest.TestCase):
    """Test cases covering `LLMHandlerTests` behavior and expected command/runtime outcomes."""

    @patch("modules.llm.providers.ollama.ollamaProvider.requests.post")
    def test_generate_response_success(self, mock_post):
        """Validate that generate response success behaves as expected."""
        mock_post.return_value = DummyResponse(200, {"response": "Hello from Aura"})
        handler = LLMHandler(make_llm_context())

        result = handler.generateResponse("Hello")

        self.assertEqual(result, "Hello from Aura")
        self.assertEqual(handler.history.messages[-2], ("user", "Hello"))
        self.assertEqual(handler.history.messages[-1], ("aura", "Hello from Aura"))

    @patch("modules.llm.providers.ollama.ollamaProvider.requests.post")
    def test_generate_response_handles_http_error(self, mock_post):
        """Validate that generate response handles http error behaves as expected."""
        mock_post.return_value = DummyResponse(500, text="server error")
        handler = LLMHandler(make_llm_context())

        result = handler.generateResponse("Hello")

        self.assertEqual(result, "I am currently unable to access my language model.")

    @patch("modules.llm.providers.ollama.ollamaProvider.requests.post")
    def test_generate_structured_response_uses_provider_validation(self, mock_post):
        """Structured responses should be parsed and returned as dictionaries."""

        mock_post.return_value = DummyResponse(
            200,
            {"response": '{"intent": "calendar.create", "confidence": 1}'},
        )
        handler = LLMHandler(make_llm_context())

        result = handler.generateStructuredResponse(
            "Create a calendar event",
            {
                "type": "object",
                "required": ["intent", "confidence"],
                "properties": {
                    "intent": {"type": "string"},
                    "confidence": {"type": "number"},
                },
            },
        )

        self.assertEqual(result["intent"], "calendar.create")
        self.assertEqual(result["confidence"], 1)

    def test_manager_falls_back_when_primary_fails(self):
        """The manager should route to fallback provider after primary failure."""

        context = make_llm_context()
        manager = LLMManager(context)
        manager.providers["primary"] = StubProvider(
            "primary",
            LLMResponse(provider="primary", success=False, error="down"),
        )
        manager.providers["fallback"] = StubProvider(
            "fallback",
            LLMResponse(provider="fallback", success=True, text="Recovered"),
        )
        manager.activeProviderName = "primary"
        manager.fallbackProviderName = "fallback"

        response = manager.generateResponse("system", "hello")

        self.assertTrue(response.success)
        self.assertEqual(response.provider, "fallback")
        self.assertEqual(response.text, "Recovered")

    def test_system_prompt_includes_memory_and_tool_contract(self):
        """The generic assistant prompt should expose memory and tool-call rules."""

        handler = LLMHandler(make_llm_context())

        prompt = handler._buildSystemPrompt()

        self.assertIn("You are Aura, a private AI assistant", prompt)
        self.assertIn("Known user information", prompt)
        self.assertIn("- name: Nova", prompt)
        self.assertIn("Available deterministic tools", prompt)
        self.assertIn("calendar.createEvent", prompt)
        self.assertIn('"toolCalls"', prompt)

    def test_offline_prompt_excludes_tools_and_instructs_generic_action_response(self):
        """Offline prompt should preserve context but avoid executable tools."""

        context = make_llm_context()
        context.llmManager = SimpleNamespace(offlineMode=True)
        handler = LLMHandler(context)

        prompt = handler._buildSystemPrompt()

        self.assertIn("running in offline mode", prompt)
        self.assertIn("Known user information", prompt)
        self.assertIn("- name: Nova", prompt)
        self.assertIn("cannot be completed in offline mode", prompt)
        self.assertNotIn("Available deterministic tools", prompt)
        self.assertNotIn("calendar.createEvent", prompt)
        self.assertNotIn('"toolCalls"', prompt)

    def test_generate_response_executes_calendar_tool_call(self):
        """A JSON tool-call response should execute the matching backend function."""

        calls = []
        context = make_llm_context()
        context.llmManager = SimpleNamespace(
            generateResponse=lambda *args, **kwargs: LLMResponse(
                provider="test",
                success=True,
                text=(
                    '{"response":"Added it to your calendar.",'
                    '"toolCalls":[{"toolName":"calendar.createEvent","arguments":'
                    '{"title":"Dentist","start_at":"2026-05-21 09:00:00"}}]}'
                ),
            )
        )
        context.calendar = SimpleNamespace(
            createEvent=lambda **kwargs: calls.append(kwargs) or 42
        )

        handler = LLMHandler(context)
        result = handler.generateResponse("Add dentist tomorrow at 9")

        self.assertEqual(result, "Added it to your calendar.")
        self.assertEqual(
            calls,
            [{"title": "Dentist", "start_at": "2026-05-21 09:00:00"}],
        )

    def test_live_llm_connection_optional(self):
        """Validate that live llm connection optional behaves as expected."""
        if os.getenv("RUN_LIVE_LLM_TEST", "").lower() != "true":
            self.skipTest("Set RUN_LIVE_LLM_TEST=true to run live LLM connection test.")

        endpoint = os.getenv("OLLAMA_ENDPOINT", "http://localhost:11434/api/generate")
        model = os.getenv("OLLAMA_MODEL", "llama3.1:8b")

        try:
            response = requests.post(
                endpoint,
                json={"model": model, "prompt": "Reply with: pong", "stream": False},
                timeout=10,
            )
        except requests.RequestException as error:
            self.fail(f"Live LLM request failed: {error}")

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertIn("response", payload)
        self.assertTrue(str(payload.get("response", "")).strip())


if __name__ == "__main__":
    unittest.main()

