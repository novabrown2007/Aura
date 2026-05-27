"""Windows interface testing.tests."""

from queue import Queue
from pathlib import Path
from types import SimpleNamespace
import unittest

from interface.windows import AuraWindowsApp
from modules.home_automation.models import BridgeState, LightDevice
from scripts.interface_build import createBundlePlan


class WindowsInterfaceTests(unittest.TestCase):
    """Tests that cover only the Windows interface package."""

    def test_windows_package_exports_app(self):
        self.assertEqual(AuraWindowsApp.__name__, "AuraWindowsApp")

    def test_windows_build_plan_includes_only_windows_interface(self):
        plan = createBundlePlan("windows")
        self.assertIn("modules", plan.included_paths)
        self.assertIn("interface/windows", plan.included_paths)
        self.assertNotIn("interface/android", plan.included_paths)
        self.assertNotIn("interface/web", plan.included_paths)

    def test_windows_build_files_exist(self):
        root = Path(__file__).resolve().parents[3]
        self.assertTrue((root / "interface" / "windows" / "requirements.txt").is_file())
        self.assertTrue((root / "interface" / "windows" / "build.py").is_file())

    def test_windows_formats_home_automation_state(self):
        light = LightDevice("light1", "Kitchen Light", "light", is_on=True, brightness=80, color="blue")
        state = BridgeState(True, "Home", lights=[light], devices=[light])

        text = AuraWindowsApp._formatHomeAutomationState(None, state)

        self.assertIn("Bridge: Home", text)
        self.assertIn("Kitchen Light", text)
        self.assertIn("on 80% color=blue", text)

    def test_microphone_button_starts_push_to_talk_on_press(self):
        app = AuraWindowsApp.__new__(AuraWindowsApp)
        app.pushToTalkActive = False
        app.appended = []
        app.microphoneButton = FakeButton()
        manager = FakePushToTalkManager()
        app.context = SimpleNamespace(pushToTalkManager=manager)
        app._appendTranscript = lambda speaker, message: app.appended.append((speaker, message))

        result = AuraWindowsApp._onMicrophonePressed(app, None)

        self.assertEqual(result, "break")
        self.assertTrue(manager.started)
        self.assertTrue(app.pushToTalkActive)
        self.assertEqual(app.microphoneButton.options["text"], "Listening")
        self.assertIn(("Aura", "Listening..."), app.appended)

    def test_enter_starts_push_to_talk_when_chat_input_is_empty(self):
        app = AuraWindowsApp.__new__(AuraWindowsApp)
        app.inputEntry = FakeEntry("")
        app.pushToTalkActive = False
        app.appended = []
        app.microphoneButton = FakeButton()
        manager = FakePushToTalkManager()
        app.context = SimpleNamespace(pushToTalkManager=manager)
        app._appendTranscript = lambda speaker, message: app.appended.append((speaker, message))

        result = AuraWindowsApp._onChatEnterPressed(app, None)

        self.assertEqual(result, "break")
        self.assertTrue(manager.started)
        self.assertTrue(app.pushToTalkActive)
        self.assertIn(("Aura", "Listening..."), app.appended)

    def test_enter_submits_text_instead_of_starting_push_to_talk(self):
        app = AuraWindowsApp.__new__(AuraWindowsApp)
        app.inputEntry = FakeEntry("hello")
        app.pushToTalkActive = False
        app.submitted = False
        app.context = SimpleNamespace(pushToTalkManager=FakePushToTalkManager())
        app._onSubmit = lambda: setattr(app, "submitted", True)

        result = AuraWindowsApp._onChatEnterPressed(app, None)

        self.assertEqual(result, "break")
        self.assertTrue(app.submitted)
        self.assertFalse(app.context.pushToTalkManager.started)

    def test_microphone_release_processes_active_push_to_talk(self):
        app = AuraWindowsApp.__new__(AuraWindowsApp)
        app.pushToTalkActive = True
        app.microphoneButton = FakeButton()
        app.workerStarted = False
        app._setBusyState = lambda isBusy: setattr(app, "busy", isBusy)

        original_thread = __import__("interface.windows.aura_windows_app", fromlist=["Thread"]).Thread

        class FakeThread:
            def __init__(self, target, daemon=False):
                self.target = target
                self.daemon = daemon

            def start(self):
                app.workerStarted = True

        import interface.windows.aura_windows_app as windows_app

        windows_app.Thread = FakeThread
        try:
            result = AuraWindowsApp._onMicrophoneReleased(app, None)
        finally:
            windows_app.Thread = original_thread

        self.assertEqual(result, "break")
        self.assertFalse(app.pushToTalkActive)
        self.assertEqual(app.microphoneButton.options["text"], "Mic")
        self.assertTrue(app.busy)
        self.assertTrue(app.workerStarted)

    def test_push_to_talk_worker_queues_voice_response(self):
        app = AuraWindowsApp.__new__(AuraWindowsApp)
        app.pendingResponses = Queue()
        app.context = SimpleNamespace(pushToTalkManager=FakePushToTalkManager())

        AuraWindowsApp._processPushToTalkInWorker(app)

        resultType, payload = app.pendingResponses.get_nowait()
        self.assertEqual(resultType, "voice_response")
        self.assertEqual(payload["user"], "hello aura")
        self.assertEqual(payload["response"], "Hello Nova.")
        self.assertEqual(payload["speechError"], "")

    def test_voice_response_shows_nonfatal_speech_failure(self):
        app = AuraWindowsApp.__new__(AuraWindowsApp)
        app.pendingResponses = Queue()
        app.pendingResponses.put(
            (
                "voice_response",
                {
                    "user": "hello aura",
                    "response": "Hello Nova.",
                    "speechError": "Voice model not found: en_US-lessac-medium",
                },
            )
        )
        app.isClosing = False
        app.appended = []
        app.root = SimpleNamespace(after=lambda delay, callback: None)
        app.logger = None
        app._refreshModelLabel = lambda: None
        app._setBusyState = lambda isBusy: setattr(app, "busy", isBusy)
        app._appendTranscript = lambda speaker, message: app.appended.append((speaker, message))

        AuraWindowsApp._pollPendingResponses(app)

        self.assertIn(("You", "hello aura"), app.appended)
        self.assertIn(("Aura", "Hello Nova."), app.appended)
        self.assertIn(("Voice", "Speech output failed: Voice model not found: en_US-lessac-medium"), app.appended)
        self.assertFalse(app.busy)

    def test_wake_word_voice_event_queues_chat_response(self):
        app = AuraWindowsApp.__new__(AuraWindowsApp)
        app.pendingResponses = Queue()

        AuraWindowsApp._onWakeWordVoiceCompletedEvent(
            app,
            SimpleNamespace(
                data={
                    "transcribedText": "turn on the lights",
                    "assistantResponse": "Turning on the lights.",
                    "speechError": "",
                }
            ),
        )

        resultType, payload = app.pendingResponses.get_nowait()
        self.assertEqual(resultType, "voice_response")
        self.assertEqual(payload["user"], "turn on the lights")
        self.assertEqual(payload["response"], "Turning on the lights.")

    def test_wake_word_events_are_subscribed_and_unsubscribed(self):
        app = AuraWindowsApp.__new__(AuraWindowsApp)
        app.logger = None
        eventManager = FakeEventManager()
        app.context = SimpleNamespace(eventManager=eventManager)

        AuraWindowsApp._subscribeWakeWordEvents(app)
        AuraWindowsApp._unsubscribeWakeWordEvents(app)

        self.assertEqual(
            [name for name, _handler in eventManager.subscriptions],
            ["wakeword.detected", "wakeword.voice.completed", "wakeword.error"],
        )
        self.assertEqual(
            [name for name, _handler in eventManager.unsubscriptions],
            ["wakeword.detected", "wakeword.voice.completed", "wakeword.error"],
        )


class FakeEntry:
    """Minimal Tk Entry stand-in for Windows UI key handling tests."""

    def __init__(self, value):
        self.value = value

    def get(self):
        return self.value


class FakeButton:
    """Minimal Tk Button stand-in for configure assertions."""

    def __init__(self):
        self.options = {}

    def configure(self, **kwargs):
        self.options.update(kwargs)


class FakePushToTalkManager:
    """Push-to-talk fake for Windows UI tests."""

    def __init__(self):
        self.enabled = True
        self.started = False
        self.lastResult = SimpleNamespace(errorMessage="")

    def startCapture(self):
        self.started = True
        return True

    def stopAndProcess(self):
        return SimpleNamespace(success=True, transcribedText="hello aura", assistantResponse="Hello Nova.")


class FakeEventManager:
    """Collect subscriptions for Windows UI event wiring tests."""

    def __init__(self):
        self.subscriptions = []
        self.unsubscriptions = []

    def subscribe(self, eventName, handler):
        self.subscriptions.append((eventName, handler))

    def unsubscribe(self, eventName, handler):
        self.unsubscriptions.append((eventName, handler))


if __name__ == "__main__":
    unittest.main()
