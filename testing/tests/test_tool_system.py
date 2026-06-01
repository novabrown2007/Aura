"""Tests for Aura's deterministic tool system."""

import unittest
from types import SimpleNamespace

from core.tools.tool import Tool
from core.tools.toolExecutor import ToolExecutor
from core.tools.toolOrchestrator import ToolOrchestrator
from core.tools.toolRegistry import ToolRegistry
from testing.tests.support.fakes import make_context


class ToolSystemTests(unittest.TestCase):
    """Validate tool registration, schemas, and safe execution."""

    def setUp(self):
        """Create a lightweight context with one test tool."""

        self.calls = []
        self.context = make_context()
        self.context.toolRegistry = ToolRegistry(self.context)
        self.context.toolExecutor = ToolExecutor(self.context)
        self.context.toolOrchestrator = ToolOrchestrator(self.context)
        self.context.personalSchedule = SimpleNamespace(
            createScheduleItem=lambda **kwargs: self.calls.append(kwargs) or 7
        )
        self.tool = Tool(
            name="schedule.createItem",
            description="Create a schedule item.",
            parameters={"title": {"type": "string"}, "dueTime": {"type": "string"}},
            requiredParameters=("title",),
            module="personalSchedule",
            method="createScheduleItem",
            offlineAllowed=False,
        )

    def test_registry_exports_tool_schema(self):
        """Registry should export schemas for prompting."""

        self.context.toolRegistry.registerTool(self.tool)

        schemas = self.context.toolRegistry.exportSchemas()

        self.assertEqual(schemas[0]["name"], "schedule.createItem")
        self.assertIn("parameters", schemas[0])

    def test_executor_validates_and_executes_tool(self):
        """Executor should validate arguments before calling the module."""

        self.context.toolRegistry.registerTool(self.tool)

        result = self.context.toolExecutor.executeToolCall(
            "schedule.createItem",
            {"title": "Dentist", "dueTime": "2026-05-21 09:00:00"},
        )

        self.assertTrue(result["success"])
        self.assertEqual(self.calls[0]["title"], "Dentist")

    def test_executor_rejects_offline_disallowed_tool(self):
        """Offline mode should block tools that are not offline allowed."""

        self.context.toolRegistry.registerTool(self.tool)

        result = self.context.toolExecutor.executeToolCall(
            "schedule.createItem",
            {"title": "Dentist", "dueTime": "2026-05-21 09:00:00"},
            offlineMode=True,
        )

        self.assertFalse(result["success"])
        self.assertIn("offline mode", result["error"])

    def test_executor_rejects_missing_required_argument(self):
        """Missing required parameters should fail before execution."""

        self.context.toolRegistry.registerTool(self.tool)

        result = self.context.toolExecutor.executeToolCall(
            "schedule.createItem",
            {},
        )

        self.assertFalse(result["success"])
        self.assertEqual(self.calls, [])

    def test_orchestrator_exports_module_owned_tool_schemas(self):
        """Orchestrator should expose schemas from registered module tools."""

        self.context.toolRegistry.registerTool(self.tool)

        schemas = self.context.toolOrchestrator.exportSchemas()

        self.assertEqual(schemas[0]["name"], "schedule.createItem")
        self.assertIn("intents", ToolOrchestrator.TOOL_INTENT_SCHEMA["properties"])
        self.assertIn("toolCalls", ToolOrchestrator.TOOL_CALL_ENVELOPE_SCHEMA["properties"])

    def test_orchestrator_executes_tool_envelope(self):
        """Orchestrator should execute LLM-selected calls through ToolExecutor."""

        self.context.toolRegistry.registerTool(self.tool)
        envelope = (
            '{"response": "Scheduled.", "toolCalls": ['
            '{"toolName": "schedule.createItem", '
            '"arguments": {"title": "Dentist", "dueTime": "2026-05-21 09:00:00"}}'
            "]}"
        )

        result = self.context.toolOrchestrator.executeToolEnvelope(envelope)

        self.assertEqual(result, "Scheduled.")
        self.assertEqual(self.calls[0]["title"], "Dentist")


if __name__ == "__main__":
    unittest.main()
