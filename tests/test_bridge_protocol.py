"""Tests for Aura Protocol bridge integration."""

from __future__ import annotations

from types import SimpleNamespace
import unittest

from auraassistant.core.bridge import (
    AuraBridgeClient,
    AuraCategories,
    AuraMessage,
    IntentRequestBuilder,
    AuraSubscriptionManager,
)
from modules.home_automation.config import BridgeConfig, HomeAutomationConfig
from tests.support.fakes import make_context


class FakeAuraProtocolTransport:
    """Deterministic protocol transport stub for bridge integration tests."""

    def __init__(self):
        self.sent = []
        self.subscriptions = []
        self.state = {
            "connected": True,
            "bridgeName": "Home Automation Bridge",
            "devices": [
                {
                    "device_id": "bedroomlight1",
                    "name": "Bedroom Light 1",
                    "category": "light",
                    "online": True,
                    "last_command": "",
                }
            ],
            "lights": [
                {
                    "device_id": "bedroomlight1",
                    "name": "Bedroom Light 1",
                    "category": "light",
                    "online": True,
                    "last_command": "",
                    "is_on": False,
                    "brightness": 10,
                    "light_type": "rgb",
                    "max_brightness": 100,
                    "color_temperature_kelvin": 2700,
                    "color": "white",
                }
            ],
            "cameras": [],
            "notifications": [],
            "streams": [],
        }

    def send(self, message):
        payload = message.toDict() if hasattr(message, "toDict") else dict(message)
        self.sent.append(payload)

        category = payload.get("category")
        if category == AuraCategories.ASSISTANT_INTENT:
            self._applyIntent(payload.get("data", {}))
            return {
                "messages": [
                    {
                        "category": AuraCategories.ASSISTANT_RESPONSE,
                        "data": {
                            "requestId": payload.get("messageId"),
                            "success": True,
                            "state": dict(self.state),
                        },
                    }
                ]
            }

        if category == AuraCategories.ASSISTANT_CONTEXT:
            return {
                "messages": [
                    {
                        "category": AuraCategories.ASSISTANT_RESPONSE,
                        "data": {
                            "requestId": payload.get("messageId"),
                            "success": True,
                            "state": dict(self.state),
                        },
                    }
                ]
            }

        return {
            "messages": [
                {
                    "category": AuraCategories.ASSISTANT_RESPONSE,
                    "data": {
                        "requestId": payload.get("messageId"),
                        "success": True,
                    },
                }
            ]
        }

    def receive(self, sessionId="", categories=None, since=""):
        return {"messages": []}

    def subscribe(self, payload):
        self.subscriptions.append(payload)
        return {"status": "ok"}

    def heartbeat(self, payload):
        return {"status": "ok"}

    def _applyIntent(self, data):
        intent = data.get("intent")
        arguments = data.get("arguments", {})
        light = self.state["lights"][0]

        if intent == "lights.setBrightness":
            light["brightness"] = int(arguments["brightness"])
            light["is_on"] = True
            light["last_command"] = "set_brightness"
        elif intent == "lights.setColor":
            light["color"] = str(arguments["color"])
            light["last_command"] = "set_color"
        elif intent == "lights.turnOn":
            light["is_on"] = True
            if "brightness" in arguments:
                light["brightness"] = int(arguments["brightness"])
            light["last_command"] = "light_on"
        elif intent == "lights.turnOff":
            light["is_on"] = False
            light["last_command"] = "light_off"


class BridgeProtocolTests(unittest.TestCase):
    """Validate the Aura Protocol bridge client and helpers."""

    def test_intent_request_builder_includes_session_context(self):
        context = make_context()
        sessions = AuraBridgeClient(context, transport=FakeAuraProtocolTransport()).sessionManager
        builder = IntentRequestBuilder(context, sessions)

        message = builder.buildIntentRequest(
            {
                "intent": "lights.setBrightness",
                "confidence": 0.92,
                "arguments": {"device_id": "bedroomlight1", "brightness": 35},
            },
            interface="voice",
        )

        self.assertEqual(message.category, AuraCategories.ASSISTANT_INTENT)
        self.assertEqual(message.context["interface"], "voice")
        self.assertEqual(message.data["intent"], "lights.setBrightness")
        self.assertEqual(message.data["arguments"]["brightness"], 35)

    def test_subscription_manager_supports_wildcards(self):
        manager = AuraSubscriptionManager()
        exact = manager.subscribe(categories=[AuraCategories.ASSISTANT_NOTIFICATION], interface="desktop")
        wildcard = manager.subscribe(categories=["assistant.*"], wildcard=False)

        self.assertEqual(len(manager.matchingSubscriptions(AuraCategories.ASSISTANT_NOTIFICATION, interface="desktop")), 2)
        self.assertTrue(exact.subscriptionId)
        self.assertTrue(wildcard.subscriptionId)

    def test_bridge_client_updates_cached_light_state_from_protocol_response(self):
        context = make_context()
        context.homeAutomationConfig = HomeAutomationConfig(bridge=BridgeConfig())
        transport = FakeAuraProtocolTransport()
        client = AuraBridgeClient(context, transport=transport)

        snapshot = client.connect()
        self.assertTrue(snapshot["connected"])
        self.assertGreaterEqual(len(client.subscriptionManager.listSubscriptions()), 5)

        light = client.setLightBrightness("bedroomlight1", 42)
        self.assertEqual(light.brightness, 42)
        self.assertTrue(light.is_on)
        self.assertEqual(light.last_command, "set_brightness")

        updated = client.setLightColor("bedroomlight1", "blue")
        self.assertEqual(updated.color, "blue")
        self.assertEqual(updated.last_command, "set_color")

        bridge_state = client.getBridgeState()
        self.assertTrue(bridge_state.connected)
        self.assertEqual(bridge_state.bridge_name, "Home Automation Bridge")
        self.assertEqual(bridge_state.lights[0].brightness, 42)
        self.assertEqual(bridge_state.lights[0].color, "blue")

    def test_client_emits_protocol_messages_to_runtime_cache(self):
        context = make_context()
        context.homeAutomationConfig = HomeAutomationConfig(bridge=BridgeConfig())
        transport = FakeAuraProtocolTransport()
        client = AuraBridgeClient(context, transport=transport)
        client.connect()

        message = AuraMessage(
            category=AuraCategories.ASSISTANT_NOTIFICATION,
            data={"event": "motionDetected", "location": "hallway", "priority": "normal"},
            context={"sessionId": "session-1", "interface": "voice"},
            source={"system": "bridge"},
        )
        client.router.route(message)

        snapshot = client.stateCache.snapshot()
        self.assertEqual(len(snapshot["notifications"]), 1)
        self.assertEqual(snapshot["notifications"][0]["event"], "motionDetected")


if __name__ == "__main__":
    unittest.main()
