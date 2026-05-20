"""Tests for Aura's structured intent execution pipeline."""

import unittest
from types import SimpleNamespace

from core.tools.tool import Tool
from core.tools.toolExecutor import ToolExecutor
from core.tools.toolRegistry import ToolRegistry
from modules.llm.intent.intentPipeline import IntentPipeline
from modules.llm.llmHandler import LLMHandler
from modules.llm.models.llmResponse import LLMResponse
from modules.llm.testing.intentTestHarness import IntentTestHarness
from tests.test_llm_handler import make_llm_context


class StubIntentManager:
    """Manager stub that returns one structured intent and one final response."""

    def __init__(self, intentPayload, finalText="Done."):
        """Store deterministic responses for the pipeline."""

        self.intentPayload = intentPayload
        self.finalText = finalText
        self.offlineMode = False
        self.rawLogger = None

    def generateStructuredResponse(self, *_args, **_kwargs):
        """Return the configured structured intent payload."""

        return LLMResponse(
            provider="test",
            success=True,
            rawResponse=self.intentPayload,
            text="{}",
        )

    def generateResponse(self, *_args, **_kwargs):
        """Return the configured final user-facing response."""

        return LLMResponse(provider="test", success=True, text=self.finalText)


class IntentPipelineTests(unittest.TestCase):
    """Validate structured intent parsing, validation, execution, and replies."""

    def test_handler_runs_structured_intent_end_to_end(self):
        """User input should parse, validate, execute, and return a final reply."""

        calls = []
        context = make_llm_context()
        context.llmManager = StubIntentManager(
            {
                "intent": "calendar.createEvent",
                "arguments": {"title": "Dentist", "start_at": "2026-05-21 09:00:00"},
                "confidence": 0.96,
                "response": "Added it.",
            },
            finalText="Added it to your calendar.",
        )
        context.calendar = SimpleNamespace(
            createEvent=lambda **kwargs: calls.append(kwargs) or 42
        )

        handler = LLMHandler(context)
        reply = handler.generateResponse("Add dentist tomorrow at 9")

        self.assertEqual(reply, "Added it to your calendar.")
        self.assertEqual(
            calls,
            [{"title": "Dentist", "start_at": "2026-05-21 09:00:00"}],
        )

    def test_low_confidence_intent_asks_for_clarification(self):
        """Low confidence should stop before execution."""

        calls = []
        context = make_llm_context()
        context.llmManager = StubIntentManager(
            {
                "intent": "calendar.createEvent",
                "arguments": {"title": "Dentist", "start_at": "2026-05-21 09:00:00"},
                "confidence": 0.4,
            }
        )
        context.calendar = SimpleNamespace(
            createEvent=lambda **kwargs: calls.append(kwargs) or 42
        )

        handler = LLMHandler(context)
        reply = handler.generateResponse("Maybe put something on my calendar")

        self.assertIn("understood correctly", reply)
        self.assertEqual(calls, [])

    def test_intent_harness_compares_expected_tool_and_arguments(self):
        """The harness should make intent parser cases easy to add."""

        context = make_llm_context()
        manager = StubIntentManager(
            {
                "intent": "lights.setBrightness",
                "arguments": {"room": "bedroom", "brightness": 20},
                "confidence": 0.96,
            }
        )
        pipeline = IntentPipeline(context, manager)
        harness = IntentTestHarness(pipeline)

        result = harness.testIntent(
            "Set bedroom lights to 20 percent",
            "lights.setBrightness",
            {"room": "bedroom", "brightness": 20},
        )

        self.assertTrue(result["success"], result)

    def test_tool_executor_blocks_admin_category(self):
        """Admin tools should not execute without explicit admin permission."""

        context = make_llm_context()
        context.toolRegistry = ToolRegistry(context)
        context.toolExecutor = ToolExecutor(context)
        context.system = SimpleNamespace(reload=lambda: {"reloaded": True})
        context.toolRegistry.registerTool(
            Tool(
                name="system.reload",
                description="Reload config.",
                module="system",
                method="reload",
                category="ADMIN_ONLY",
            )
        )

        result = context.toolExecutor.executeToolCall("system.reload")

        self.assertFalse(result["success"])
        self.assertIn("admin permission", result["error"])


if __name__ == "__main__":
    unittest.main()
