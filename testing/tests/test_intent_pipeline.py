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
from testing.tests.test_llm_handler import make_llm_context


class StubIntentManager:
    """Manager stub that returns one structured intent and one final response."""

    def __init__(self, intentPayload, finalText="Done."):
        """Store deterministic responses for the pipeline."""

        self.intentPayload = intentPayload
        self.finalText = finalText
        self.offlineMode = False
        self.rawLogger = None
        self.structuredCalls = []

    def generateStructuredResponse(self, *args, **kwargs):
        """Return the configured structured intent payload."""

        self.structuredCalls.append({"args": args, "kwargs": kwargs})
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

    def registerLightTurnOnTool(self, context, calls):
        """Register a light tool backed by a deterministic test module."""

        context.toolRegistry.registerTool(
            Tool(
                name="lights.turnOn",
                description="Turn on a light by room or light name.",
                parameters={"room": {"type": "string"}, "brightness": {"type": "integer"}},
                requiredParameters=("room",),
                module="homeAutomation",
                method="turnLightOnByRoom",
            )
        )
        context.homeAutomation = SimpleNamespace(
            turnLightOnByRoom=lambda **kwargs: calls.append(kwargs) or {"is_on": True, **kwargs}
        )

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

    def test_handler_recovers_missing_room_from_original_light_request(self):
        """Obvious room text in the original message should repair an incomplete intent."""

        calls = []
        context = make_llm_context()
        self.registerLightTurnOnTool(context, calls)
        context.llmManager = StubIntentManager(
            {
                "intent": "lights.turnOn",
                "arguments": {},
                "confidence": 0.96,
                "response": "Turning on the lights.",
            },
            finalText="The bedroom lights are on.",
        )

        handler = LLMHandler(context)
        reply = handler.generateResponse("Can you turn on my bedroom lights please?")

        self.assertEqual(reply, "The bedroom lights are on.")
        self.assertEqual(calls, [{"room": "bedroom"}])

    def test_follow_up_supplies_missing_room_for_pending_light_intent(self):
        """A short clarification reply should complete the pending tool call."""

        calls = []
        context = make_llm_context()
        self.registerLightTurnOnTool(context, calls)
        context.llmManager = StubIntentManager(
            {
                "intent": "lights.turnOn",
                "arguments": {},
                "confidence": 0.96,
                "response": "Turning on the lights.",
            },
            finalText="The bedroom lights are on.",
        )

        handler = LLMHandler(context)
        firstReply = handler.generateResponse("Can you turn on my lights please?")
        secondReply = handler.generateResponse("bedroom")

        self.assertIn("Missing required parameter: room", firstReply)
        self.assertEqual(secondReply, "The bedroom lights are on.")
        self.assertEqual(calls, [{"room": "bedroom"}])

    def test_cancel_pending_clarification_returns_to_conversation(self):
        """Dismissing a pending tool clarification should not poison later chat."""

        calls = []
        context = make_llm_context()
        self.registerLightTurnOnTool(context, calls)
        context.llmManager = StubIntentManager(
            {
                "intent": "lights.turnOn",
                "arguments": {},
                "confidence": 0.96,
                "response": "Turning on the lights.",
            },
            finalText="Your name is Nova.",
        )

        handler = LLMHandler(context)
        firstReply = handler.generateResponse("Can you turn on my lights please?")
        cancelReply = handler.generateResponse("Don't worry about it for now.")
        context.llmManager.intentPayload = {
            "intent": "conversation.respond",
            "arguments": {},
            "confidence": 0.98,
            "response": "Your name is Nova.",
        }
        finalReply = handler.generateResponse("What is my name?")

        self.assertIn("Missing required parameter: room", firstReply)
        self.assertIn("won't worry", cancelReply)
        self.assertEqual(finalReply, "Your name is Nova.")
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

    def test_handler_executes_multi_step_tool_chain_in_order(self):
        """A compound request should execute each parsed tool in sequence."""

        calls = []
        context = make_llm_context()
        context.toolRegistry.registerTool(
            Tool(
                name="test.firstStep",
                description="Run the first test step.",
                parameters={"value": {"type": "string"}},
                requiredParameters=("value",),
                module="firstModule",
                method="run",
            )
        )
        context.toolRegistry.registerTool(
            Tool(
                name="test.secondStep",
                description="Run the second test step.",
                parameters={"value": {"type": "string"}},
                requiredParameters=("value",),
                module="secondModule",
                method="run",
            )
        )
        context.llmManager = StubIntentManager(
            {
                "response": "Running both steps.",
                "intents": [
                    {
                        "intent": "test.firstStep",
                        "arguments": {"value": "dim lights"},
                        "confidence": 0.96,
                    },
                    {
                        "intent": "test.secondStep",
                        "arguments": {"value": "start music"},
                        "confidence": 0.93,
                    },
                ],
            },
            finalText="Both steps are done.",
        )
        context.firstModule = SimpleNamespace(
            run=lambda **kwargs: calls.append(("first", kwargs)) or {"ok": True}
        )
        context.secondModule = SimpleNamespace(
            run=lambda **kwargs: calls.append(("second", kwargs)) or {"ok": True}
        )

        handler = LLMHandler(context)
        reply = handler.generateResponse("Do two related actions.")

        self.assertEqual(reply, "Both steps are done.")
        self.assertEqual(
            calls,
            [
                ("first", {"value": "dim lights"}),
                ("second", {"value": "start music"}),
            ],
        )

    def test_harness_compares_expected_tool_chain(self):
        """The harness should support ordered multi-step intent cases."""

        context = make_llm_context()
        manager = StubIntentManager(
            {
                "intents": [
                    {
                        "intent": "test.firstStep",
                        "arguments": {"value": "dim lights"},
                        "confidence": 0.96,
                    },
                    {
                        "intent": "test.secondStep",
                        "arguments": {"value": "start music"},
                        "confidence": 0.93,
                    },
                ],
            }
        )
        pipeline = IntentPipeline(context, manager)
        harness = IntentTestHarness(pipeline)

        result = harness.testToolChain(
            "Do two related actions.",
            [
                {"tool": "test.firstStep", "arguments": {"value": "dim lights"}},
                {"tool": "test.secondStep", "arguments": {"value": "start music"}},
            ],
        )

        self.assertTrue(result["success"], result)

    def test_intent_prompt_injects_contextual_memory_and_prior_tool_context(self):
        """Follow-up requests should receive memory and prior tool context."""

        context = make_llm_context()
        context.memoryManager.memory = {
            "current_room": "bedroom",
            "preferred_light_level": "20",
        }
        manager = StubIntentManager(
            {
                "intents": [
                    {
                        "intent": "test.turnOff",
                        "arguments": {"room": "bedroom"},
                        "confidence": 0.96,
                    }
                ],
            }
        )
        pipeline = IntentPipeline(context, manager)
        pipeline.recentToolContext.append(
            {
                "intent": "lights.setBrightness",
                "arguments": {"room": "bedroom", "brightness": 20},
                "success": True,
                "result": {"device_id": "bedroom_lamp"},
            }
        )

        pipeline.parseIntents(
            "Turn them off too.",
            "You are Aura.",
            conversationHistory=[
                ("user", "Dim the bedroom lights."),
                ("aura", "The bedroom lights are dimmed."),
            ],
        )

        prompt = manager.structuredCalls[0]["args"][0]
        self.assertIn("Context for resolving references", prompt)
        self.assertIn("current_room: bedroom", prompt)
        self.assertIn("lights.setBrightness", prompt)
        self.assertIn("bedroom_lamp", prompt)
        self.assertIn("Dim the bedroom lights.", prompt)


if __name__ == "__main__":
    unittest.main()
