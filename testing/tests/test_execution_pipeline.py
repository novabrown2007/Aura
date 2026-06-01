"""Tests for Aura's unified execution pipeline."""

from __future__ import annotations

import unittest

from assistant.safety import SafetyManager
from core.tools.tool import Tool
from core.tools.toolExecutor import ToolExecutor
from core.tools.toolRegistry import ToolRegistry
from assistant.execution import ExecutionManager
from testing.tests.support.fakes import make_context


class DummyModule:
    """Tiny module used to validate routed execution."""

    def __init__(self):
        self.calls = []

    def pause(self):
        self.calls.append(("pause", {}))
        return {"spokenText": "Paused.", "uiText": "Playback paused."}

    def sendEmail(self, to):
        self.calls.append(("sendEmail", {"to": list(to)}))
        return {"spokenText": "Email sent.", "uiText": "Email delivered."}

    def setBrightness(self, brightness: int):
        self.calls.append(("setBrightness", {"brightness": brightness}))
        return {"spokenText": f"Brightness set to {brightness}.", "uiText": f"Brightness: {brightness}."}


class ExecutionPipelineTests(unittest.TestCase):
    """Validate the new unified execution architecture."""

    def setUp(self):
        self.context = make_context(extra={})
        self.context.toolRegistry = ToolRegistry(self.context)
        self.context.toolExecutor = ToolExecutor(self.context)
        self.context.safetyManager = SafetyManager(self.context)
        self.context.executionManager = ExecutionManager(self.context)
        self.dummy = DummyModule()
        self.context.modules["dummy"] = self.dummy

    def test_module_action_routes_through_pipeline(self):
        tool = Tool(
            name="dummy.pause",
            description="Pause dummy media.",
            module="dummy",
            method="pause",
            safe=True,
            offlineAllowed=True,
            requiredPermissions=(),
            riskLevel="LOW",
        )
        self.context.toolRegistry.registerTool(tool)
        self.context.executionManager.refreshRegistry()

        result = self.context.toolExecutor.executeToolCall("dummy.pause", {})

        self.assertTrue(result["success"])
        self.assertEqual(self.dummy.calls[-1][0], "pause")
        self.assertIn("dummy.pause", [action["actionName"] for action in self.context.executionManager.snapshot()["actions"]])

    def test_validation_failure_is_reported(self):
        tool = Tool(
            name="dummy.setBrightness",
            description="Set brightness.",
            parameters={"brightness": {"type": "integer", "minimum": 0, "maximum": 100}},
            requiredParameters=("brightness",),
            module="dummy",
            method="setBrightness",
            safe=True,
            offlineAllowed=True,
            riskLevel="LOW",
        )
        self.context.toolRegistry.registerTool(tool)
        self.context.executionManager.refreshRegistry()

        result = self.context.toolExecutor.executeToolCall("dummy.setBrightness", {"brightness": 120})

        self.assertFalse(result["success"])
        self.assertIn("brightness", result["error"].lower())
        self.assertEqual(self.dummy.calls, [])

    def test_high_risk_action_requires_confirmation_then_executes(self):
        tool = Tool(
            name="email.sendEmail",
            description="Send email.",
            parameters={"to": {"type": "array"}},
            requiredParameters=("to",),
            module="dummy",
            method="sendEmail",
            safe=False,
            offlineAllowed=True,
            confirmRequired=True,
            requiredPermissions=("email.send",),
            riskLevel="HIGH",
        )
        self.context.toolRegistry.registerTool(tool)
        self.context.executionManager.refreshRegistry()

        initial = self.context.toolExecutor.executeToolCall("email.sendEmail", {"to": ["john@example.com"]})
        self.assertFalse(initial["success"])
        self.assertTrue(initial["requiresConfirmation"])
        requestId = next(iter(self.context.safetyManager.pendingConfirmations.keys()))

        confirmed = self.context.safetyManager.confirm(requestId, approved=True)

        self.assertTrue(confirmed["success"])
        self.assertGreaterEqual(len(self.dummy.calls), 1)

    def test_bridge_router_is_available(self):
        class FakeBridge:
            def executeAction(self, actionName, payload):
                return {"actionName": actionName, "payload": payload, "bridge": True}

        self.context.bridgeClient = FakeBridge()
        tool = Tool(
            name="bridge.light.turnOn",
            description="Turn on a bridge light.",
            module="bridge",
            method="executeAction",
            safe=True,
            offlineAllowed=True,
            requiredPermissions=(),
            riskLevel="LOW",
        )
        self.context.toolRegistry.registerTool(tool)
        self.context.executionManager.refreshRegistry()

        result = self.context.toolExecutor.executeToolCall("bridge.light.turnOn", {"room": "bedroom"})

        self.assertTrue(result["success"])
        self.assertTrue(result["result"]["bridge"])


if __name__ == "__main__":
    unittest.main()
