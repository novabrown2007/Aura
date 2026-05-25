"""Tests for Aura's assistant ecosystem simulation and debugging helpers."""

from __future__ import annotations

from types import SimpleNamespace
import unittest

from core.bridge.state.bridgeStateCache import BridgeStateCache
from testing import (
    AssistantConsole,
    AssistantSimulator,
    EventTracer,
    IntegrationTester,
    IntentDebugger,
    IntentTester,
    MockNotifications,
    MockUser,
    MockVoiceInput,
    SessionDebugger,
    TracedEvent,
    VoiceTester,
    WorkflowSimulator,
    WorkflowTester,
)
from tests.support.fakes import make_context


class FakeBridgeClient:
    """Deterministic bridge client stub for assistant ecosystem tests."""

    def __init__(self):
        self.stateCache = BridgeStateCache()
        self.subscriptionManager = SimpleNamespace(
            subscribe=lambda **kwargs: SimpleNamespace(**kwargs)
        )
        self.submitted = []

    def submitIntent(self, intent, sessionId: str = "", interface: str = "desktop", extraContext=None):
        payload = {
            "intent": dict(intent),
            "sessionId": sessionId,
            "interface": interface,
            "extraContext": dict(extraContext or {}),
        }
        self.submitted.append(payload)
        return {
            "messages": [
                {
                    "category": "assistant.response",
                    "data": {
                        "requestId": "req-1",
                        "success": True,
                        "response": f"executed:{intent['intent']}",
                    },
                }
            ]
        }


class AssistantTestingTests(unittest.TestCase):
    """Cover the mock assistant ecosystem testing layer."""

    def setUp(self):
        self.context = make_context(
            extra={
                "interpreter": SimpleNamespace(
                    interpret=lambda text: SimpleNamespace(name="intent", raw=str(text))
                ),
                "intentRouter": SimpleNamespace(
                    route=lambda intent: f"routed:{intent.raw}"
                ),
            }
        )
        self.bridgeClient = FakeBridgeClient()
        self.context.bridgeClient = self.bridgeClient
        self.context.voiceManager = SimpleNamespace(speakResponse=lambda text: {"spoken": text})

    def test_debuggers_and_console_capture_state(self):
        console = AssistantConsole(self.context)
        tracer = EventTracer(self.context)
        sessions = SessionDebugger(self.context)
        intents = IntentDebugger(self.context)

        console.displayVoice("Hello")
        console.displayNotification("motionDetected -> hallway")
        tracer.traceNotification({"event": "motionDetected", "location": "hallway"})
        session = sessions.createSession(interface="voice", sessionId="session-1")
        intents.recordIntent("lights.setBrightness", 0.94, {"brightness": 20})
        intents.recordValidationFailure("lights.setBrightness", "Invalid brightness", {"brightness": 200})

        self.assertIn("[VOICE] Hello", console.getLines())
        self.assertIsInstance(tracer.events[0], TracedEvent)
        self.assertEqual(tracer.getLastEvent()["name"], "motionDetected")
        self.assertEqual(session.sessionId, "session-1")
        self.assertEqual(intents.getLatestIntent()["validation"], "failed")

    def test_assistant_simulator_handles_voice_notification_and_streams(self):
        simulator = AssistantSimulator(self.context, bridgeClient=self.bridgeClient, voiceManager=self.context.voiceManager)
        session = simulator.createSession(interface="voice", sessionId="voice-session-1")
        subscription = simulator.subscribe(["assistant.notification"], interface="voice", sessionId=session.sessionId)
        voiceResult = simulator.simulateVoiceConversation("turn on the bedroom lights", sessionId=session.sessionId, speak=True)
        notificationResult = simulator.simulateNotificationWorkflow(MockNotifications.motionDetected("hallway"), sessionId=session.sessionId)
        streamResult = simulator.simulateStreamWorkflow(MockNotifications.streamAvailable()["data"], sessionId=session.sessionId)
        contextResult = simulator.simulateAssistantContext({"activeRoom": "hallway"}, sessionId=session.sessionId, interface="voice")

        self.assertEqual(subscription.categories, ["assistant.notification"])
        self.assertTrue(voiceResult["success"])
        self.assertEqual(voiceResult["assistantResponse"], "executed:lights.turnOn")
        self.assertIn("Motion detected", notificationResult["response"])
        self.assertEqual(streamResult["stream"]["streamId"], "camera-bedroom-01")
        self.assertEqual(contextResult["activeRoom"], "hallway")
        self.assertTrue(simulator.snapshot()["console"])

    def test_voice_tester_routes_text_without_audio(self):
        voiceManager = SimpleNamespace(speakResponse=lambda text: {"spoken": text})
        tester = VoiceTester(self.context, voiceManager=voiceManager, tracer=EventTracer(self.context))

        result = tester.simulatePushToTalk("turn on the lights", voiceInput=MockVoiceInput.create("turn on the lights").toDict())

        self.assertEqual(result.transcription, "turn on the lights")
        self.assertEqual(result.response, "routed:turn on the lights")
        self.assertGreaterEqual(result.transcriptionTime, 0.0)
        self.assertGreaterEqual(result.responseTime, 0.0)

    def test_integration_and_workflow_testers_use_simulator(self):
        simulator = AssistantSimulator(self.context, bridgeClient=self.bridgeClient, voiceManager=self.context.voiceManager)
        workflowSimulator = WorkflowSimulator(self.context, assistantSimulator=simulator)
        voiceTester = VoiceTester(self.context, voiceManager=self.context.voiceManager, tracer=EventTracer(self.context))
        workflowTester = WorkflowTester(self.context, simulator=workflowSimulator, tracer=EventTracer(self.context))
        tester = IntegrationTester(self.context, simulator=simulator, voiceTester=voiceTester, workflowTester=workflowTester)

        full = tester.runFullIntegration(
            "turn off the bedroom lights",
            notification=MockNotifications.deviceOffline("bedroomlight1"),
            sessionId="session-2",
        )
        workflow = workflowTester.runFullWorkflow(
            "turn on the lights",
            notification=MockNotifications.automationCompleted(),
            stream=MockNotifications.streamAvailable()["data"],
            sessionId="session-3",
        )

        self.assertIn("voice", full)
        self.assertTrue(full["voice"].response)
        self.assertIn("notification", full)
        self.assertIn("conversation", workflow)
        self.assertIn("stream", workflow)

    def test_mock_generators_produce_expected_payloads(self):
        user = MockUser()
        repeated = user.repeatRequest("test", count=2)
        clarification = user.clarificationFlow("Need details?", "Use the bedroom")
        voiceInput = MockVoiceInput.create("hello aura").toTranscriptionCase()
        notification = MockNotifications.assistantError()

        self.assertEqual(len(repeated), 2)
        self.assertEqual(clarification["answer"]["text"], "Use the bedroom")
        self.assertEqual(voiceInput["text"], "hello aura")
        self.assertEqual(notification["category"], "assistant.error")

    def test_intent_tester_validates_and_builds_bridge_request(self):
        tester = IntentTester(self.context, tracer=EventTracer(self.context), intentDebugger=IntentDebugger(self.context))
        intent = {"intent": "lights.setBrightness", "confidence": 0.9, "arguments": {"brightness": "20"}}

        valid, message = tester.validateIntent(intent)
        request = tester.buildBridgeRequest(intent, sessionId="session-4", interface="voice")

        self.assertTrue(valid)
        self.assertEqual(message, "")
        self.assertEqual(request["data"]["arguments"]["brightness"], 20)
        self.assertEqual(request["context"]["sessionId"], "session-4")


if __name__ == "__main__":
    unittest.main()
