"""Tests for Aura's deterministic tool system."""

import unittest
from types import SimpleNamespace

from core.tools.tool import Tool
from core.tools.toolExecutor import ToolExecutor
from core.tools.toolRegistry import ToolRegistry
from tests.support.fakes import make_context


class ToolSystemTests(unittest.TestCase):
    """Validate tool registration, schemas, and safe execution."""

    def setUp(self):
        """Create a lightweight context with one test tool."""

        self.calls = []
        self.context = make_context()
        self.context.toolRegistry = ToolRegistry(self.context)
        self.context.toolExecutor = ToolExecutor(self.context)
        self.context.calendar = SimpleNamespace(
            createEvent=lambda **kwargs: self.calls.append(kwargs) or 7
        )
        self.tool = Tool(
            name="calendar.createEvent",
            description="Create a calendar event.",
            parameters={"title": {"type": "string"}, "start_at": {"type": "string"}},
            requiredParameters=("title", "start_at"),
            module="calendar",
            method="createEvent",
            offlineAllowed=False,
        )

    def test_registry_exports_tool_schema(self):
        """Registry should export schemas for prompting."""

        self.context.toolRegistry.registerTool(self.tool)

        schemas = self.context.toolRegistry.exportSchemas()

        self.assertEqual(schemas[0]["name"], "calendar.createEvent")
        self.assertIn("parameters", schemas[0])

    def test_executor_validates_and_executes_tool(self):
        """Executor should validate arguments before calling the module."""

        self.context.toolRegistry.registerTool(self.tool)

        result = self.context.toolExecutor.executeToolCall(
            "calendar.createEvent",
            {"title": "Dentist", "start_at": "2026-05-21 09:00:00"},
        )

        self.assertTrue(result["success"])
        self.assertEqual(self.calls[0]["title"], "Dentist")

    def test_executor_rejects_offline_disallowed_tool(self):
        """Offline mode should block tools that are not offline allowed."""

        self.context.toolRegistry.registerTool(self.tool)

        result = self.context.toolExecutor.executeToolCall(
            "calendar.createEvent",
            {"title": "Dentist", "start_at": "2026-05-21 09:00:00"},
            offlineMode=True,
        )

        self.assertFalse(result["success"])
        self.assertIn("offline mode", result["error"])

    def test_executor_rejects_missing_required_argument(self):
        """Missing required parameters should fail before execution."""

        self.context.toolRegistry.registerTool(self.tool)

        result = self.context.toolExecutor.executeToolCall(
            "calendar.createEvent",
            {"title": "Dentist"},
        )

        self.assertFalse(result["success"])
        self.assertEqual(self.calls, [])


if __name__ == "__main__":
    unittest.main()
