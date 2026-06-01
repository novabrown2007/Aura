"""Tests for Aura's centralized execution governance."""

from __future__ import annotations

from types import SimpleNamespace
import unittest

from assistant.safety import SafetyManager
from core.tools.tool import Tool
from core.tools.toolExecutor import ToolExecutor
from core.tools.toolRegistry import ToolRegistry
from testing.tests.support.fakes import make_context


class SafetyLayerTests(unittest.TestCase):
    """Validate action gating, confirmations, and rate limits."""

    def setUp(self):
        self.calls = []
        self.events = []
        self.context = make_context(
            extra={
                "eventManager": SimpleNamespace(
                    subscribe=lambda *args, **kwargs: None,
                    unsubscribe=lambda *args, **kwargs: None,
                    emit=lambda name, data: self.events.append((name, data)),
                )
            }
        )
        self.context.toolRegistry = ToolRegistry(self.context)
        self.context.toolExecutor = ToolExecutor(self.context)
        self.context.calendar = SimpleNamespace(createEvent=lambda **kwargs: self.calls.append(kwargs) or 7)
        self.context.lightController = SimpleNamespace(setBrightness=lambda **kwargs: self.calls.append(kwargs) or True)
        self.context.system = SimpleNamespace(shutdown=lambda: self.calls.append({"shutdown": True}) or True)
        self.context.safetyManager = SafetyManager(self.context)

    def test_safe_action_executes_through_guard(self):
        tool = Tool(
            name="calendar.createEvent",
            description="Create a calendar event.",
            parameters={"title": {"type": "string"}, "start_at": {"type": "string"}},
            requiredParameters=("title", "start_at"),
            module="calendar",
            method="createEvent",
            offlineAllowed=True,
            riskLevel="LOW",
        )
        self.context.toolRegistry.registerTool(tool)

        result = self.context.toolExecutor.executeToolCall(
            "calendar.createEvent",
            {"title": "Dentist", "start_at": "2026-05-21 09:00:00"},
        )

        self.assertTrue(result["success"])
        self.assertEqual(self.calls[0]["title"], "Dentist")
        self.assertTrue(any(name == "execution.allowed" for name, _ in self.events))

    def test_high_risk_action_requires_confirmation(self):
        tool = Tool(
            name="system.shutdown",
            description="Shutdown the system.",
            parameters={},
            module="system",
            method="shutdown",
            offlineAllowed=True,
            riskLevel="CRITICAL",
        )
        self.context.toolRegistry.registerTool(tool)

        result = self.context.toolExecutor.executeToolCall("system.shutdown")

        self.assertFalse(result["success"])
        self.assertTrue(result["requiresConfirmation"])
        self.assertTrue(any(name == "execution.confirmation.required" for name, _ in self.events))

    def test_dangerous_action_can_be_denied_by_validation(self):
        tool = Tool(
            name="lights.setBrightness",
            description="Set brightness.",
            parameters={"brightness": {"type": "number"}},
            requiredParameters=("brightness",),
            module="lightController",
            method="setBrightness",
            offlineAllowed=True,
            riskLevel="MODERATE",
        )
        self.context.toolRegistry.registerTool(tool)

        result = self.context.toolExecutor.executeToolCall("lights.setBrightness", {"brightness": 150})

        self.assertFalse(result["success"])
        self.assertIn("brightness", result["error"])
        self.assertTrue(any(name == "execution.denied" for name, _ in self.events))

    def test_rate_limit_blocks_repeated_execution(self):
        tool = Tool(
            name="calendar.createEvent",
            description="Create a calendar event.",
            parameters={"title": {"type": "string"}, "start_at": {"type": "string"}},
            requiredParameters=("title", "start_at"),
            module="calendar",
            method="createEvent",
            offlineAllowed=True,
            riskLevel="LOW",
        )
        self.context.toolRegistry.registerTool(tool)
        self.context.safetyManager.rateLimitManager.maxExecutionsPerMinute = 1

        first = self.context.toolExecutor.executeToolCall(
            "calendar.createEvent",
            {"title": "Dentist", "start_at": "2026-05-21 09:00:00"},
        )
        second = self.context.toolExecutor.executeToolCall(
            "calendar.createEvent",
            {"title": "Dentist", "start_at": "2026-05-21 09:00:00"},
        )

        self.assertTrue(first["success"])
        self.assertFalse(second["success"])
        self.assertTrue(second.get("cooldownRemaining", 0.0) > 0.0)
        self.assertTrue(any(name == "execution.rate_limited" for name, _ in self.events))

    def test_confirmation_can_be_resolved_without_looping(self):
        tool = Tool(
            name="system.shutdown",
            description="Shutdown the system.",
            parameters={},
            module="system",
            method="shutdown",
            offlineAllowed=True,
            riskLevel="CRITICAL",
        )
        self.context.toolRegistry.registerTool(tool)

        initial = self.context.toolExecutor.executeToolCall("system.shutdown")
        self.assertFalse(initial["success"])
        self.assertTrue(self.context.safetyManager.pendingConfirmations)

        requestId = next(iter(self.context.safetyManager.pendingConfirmations.keys()))
        resolved = self.context.safetyManager.confirm(requestId, approved=True)

        self.assertIsNotNone(resolved)
        self.assertTrue(resolved["success"])
        self.assertTrue(any(call.get("shutdown") for call in self.calls))
        self.assertFalse(self.context.safetyManager.pendingConfirmations)


if __name__ == "__main__":
    unittest.main()
