"""Automated tests for `test_llm_handler` behavior and regression coverage."""

import os
import unittest
from types import SimpleNamespace
from unittest.mock import patch

import requests

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


def make_llm_context(endpoint="http://localhost:11434/api/generate"):
    """Construct and return a configured helper object for tests/runtime wiring."""
    context = SimpleNamespace()
    context.logger = None
    context.config = DictConfig(
        {
            "llm": {
                "endpoint": endpoint,
                "model": "llama3.1:8b",
                "history": {"enabled": True, "limit": 10},
                "memory": {"enabled": True},
            }
        }
    )
    context.conversationHistory = StubHistory()
    context.memoryManager = StubMemory()
    return context


class LLMHandlerTests(unittest.TestCase):
    """Test cases covering `LLMHandlerTests` behavior and expected command/runtime outcomes."""

    @patch("modules.llm.llmHandler.requests.post")
    def test_generate_response_success(self, mock_post):
        """Validate that generate response success behaves as expected."""
        mock_post.return_value = DummyResponse(200, {"response": "Hello from Aura"})
        handler = LLMHandler(make_llm_context())

        result = handler.generateResponse("Hello")

        self.assertEqual(result, "Hello from Aura")
        self.assertEqual(handler.history.messages[-2], ("user", "Hello"))
        self.assertEqual(handler.history.messages[-1], ("aura", "Hello from Aura"))

    @patch("modules.llm.llmHandler.requests.post")
    def test_generate_response_handles_http_error(self, mock_post):
        """Validate that generate response handles http error behaves as expected."""
        mock_post.return_value = DummyResponse(500, text="server error")
        handler = LLMHandler(make_llm_context())

        result = handler.generateResponse("Hello")

        self.assertEqual(result, "I encountered an issue contacting my language model.")

    def test_live_llm_connection_optional(self):
        """Validate that live llm connection optional behaves as expected."""
        if os.getenv("RUN_LIVE_LLM_TEST", "").lower() != "true":
            self.skipTest("Set RUN_LIVE_LLM_TEST=true to run live LLM connection test.")

        endpoint = os.getenv("LLM_ENDPOINT", "http://localhost:11434/api/generate")
        model = os.getenv("LLM_MODEL", "llama3.1:8b")

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

