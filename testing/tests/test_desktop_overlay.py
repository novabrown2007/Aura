"""Tests for Aura's Windows desktop overlay and tray coordination."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from interface.desktop.windows import OverlayEventHandler, OverlayManager, OverlayPositionManager
from interface.desktop.windows.interaction.quickInteractionWindow import QuickInteractionWindow
from interface.desktop.windows.models import OverlayPosition
from interface.desktop.windows.overlay.assistantBubble import AssistantBubble
from interface.desktop.windows.lifecycle.windowLifecycleManager import WindowLifecycleManager
from testing.tests.support.fakes import DictConfig


class FakeEventManager:
    def __init__(self):
        self.listeners = {}

    def subscribe(self, eventName, callback):
        self.listeners.setdefault(eventName, []).append(callback)

    def unsubscribe(self, eventName, callback):
        if eventName in self.listeners:
            self.listeners[eventName] = [item for item in self.listeners[eventName] if item is not callback]


class FakeRoot:
    def __init__(self):
        self.withdrawn = False
        self.destroyed = False
        self.quit_called = False
        self.geometry_value = "900x620+120+80"
        self.protocols = {}
        self.attributes_calls = []

    def protocol(self, name, callback):
        self.protocols[name] = callback

    def withdraw(self):
        self.withdrawn = True

    def deiconify(self):
        self.withdrawn = False

    def lift(self):
        return None

    def focus_force(self):
        return None

    def quit(self):
        self.quit_called = True

    def destroy(self):
        self.destroyed = True

    def winfo_exists(self):
        return not self.destroyed

    def winfo_screenwidth(self):
        return 1920

    def winfo_screenheight(self):
        return 1080

    def geometry(self, value=None):
        if value is not None:
            self.geometry_value = value
        return self.geometry_value

    def attributes(self, *_args, **_kwargs):
        self.attributes_calls.append((_args, _kwargs))
        return None

    def after(self, *_args, **_kwargs):
        return None


class FakeApp:
    def __init__(self, root):
        self.root = root
        self.exitRequested = False

    def requestExit(self):
        self.exitRequested = True
        self.root.quit()
        self.root.destroy()


class FakeOverlayManager:
    def __init__(self):
        self.calls = []

    def updateAssistant(self, *args):
        self.calls.append(("assistant", args))

    def updateMic(self, *args, **kwargs):
        self.calls.append(("mic", args, kwargs))

    def showBubble(self):
        self.calls.append(("bubble",))

    def showNotification(self, payload):
        self.calls.append(("notification", payload))

    def markEvent(self, name):
        self.calls.append(("mark", name))

    def requestExit(self, reason="user"):
        self.calls.append(("exit", reason))


class FakeBubbleWindow:
    def __init__(self):
        self.geometry_value = "+60+60"
        self.destroyed = False
        self.deiconified = False
        self.lifted = False
        self.title_value = ""
        self.x = 40
        self.y = 50
        self.screen_width = 1920
        self.screen_height = 1080
        self.children = []
        self.attributes_calls = []

    def bind(self, *_args, **_kwargs):
        return None

    def winfo_children(self):
        return self.children

    def winfo_x(self):
        return self.x

    def winfo_y(self):
        return self.y

    def winfo_screenwidth(self):
        return self.screen_width

    def winfo_screenheight(self):
        return self.screen_height

    def geometry(self, value=None):
        if value is not None:
            self.geometry_value = value
            if value.startswith("+"):
                _, _, offset = value.partition("+")
                x, _, y = offset.partition("+")
                self.x = int(x or 0)
                self.y = int(y or 0)
        return self.geometry_value

    def deiconify(self):
        self.deiconified = True

    def lift(self):
        self.lifted = True

    def attributes(self, *_args, **_kwargs):
        self.attributes_calls.append((_args, _kwargs))
        return None

    def configure(self, *_args, **_kwargs):
        return None

    def overrideredirect(self, *_args, **_kwargs):
        return None

    def title(self, value=None):
        if value is not None:
            self.title_value = value
        return self.title_value

    def destroy(self):
        self.destroyed = True

    def withdraw(self):
        self.deiconified = False


class DesktopOverlayTests(unittest.TestCase):
    """Validate close-to-tray, shutdown, and overlay event behavior."""

    def makeContext(self, tempDir):
        context = SimpleNamespace()
        context.logger = None
        context.eventManager = FakeEventManager()
        context.should_exit = False
        context.config = DictConfig(
            {
                "interface": {
                    "desktop": {
                        "windows": {
                            "desktopOverlayEnabled": True,
                            "assistantBubbleEnabled": False,
                            "systemTrayEnabled": False,
                            "minimizeToTrayOnClose": True,
                            "overlayAlwaysOnTop": True,
                            "overlayOpacity": 0.92,
                            "overlayAnimationsEnabled": False,
                            "overlayNotificationsEnabled": True,
                            "overlayCompactMode": True,
                            "overlayStartMinimized": False,
                        }
                    }
                }
            }
        )
        context._tempDir = tempDir
        return context

    def test_close_request_minimizes_to_tray_without_exiting(self):
        with tempfile.TemporaryDirectory() as tempDir:
            context = self.makeContext(tempDir)
            root = FakeRoot()
            app = FakeApp(root)
            manager = OverlayManager(context, root=root, app=app)
            manager.start()

            consumed = manager.handleWindowCloseRequest()

            self.assertTrue(consumed)
            self.assertTrue(root.withdrawn)
            self.assertFalse(root.destroyed)
            self.assertFalse(app.exitRequested)
            self.assertTrue(manager.stateManager.snapshot()["minimizedToTray"])

    def test_nested_overlay_config_is_resolved_from_desktop_window_section(self):
        with tempfile.TemporaryDirectory() as tempDir:
            context = self.makeContext(tempDir)
            root = FakeRoot()
            app = FakeApp(root)
            manager = OverlayManager(context, root=root, app=app)

            self.assertTrue(manager.enabled)
            self.assertTrue(manager.windowLifecycleManager.minimizeToTrayOnClose)
            self.assertEqual(manager.overlayWindow.snapshot()["opacity"], 0.92)
            self.assertEqual(root.geometry_value, "900x620+120+80")
            self.assertFalse(any(args and args[0] == "-alpha" for args, _kwargs in root.attributes_calls))
            self.assertIsNone(manager.windowLifecycleManager.positionManager)
            self.assertIs(manager.positionManager, manager.bubblePositionManager)

    def test_bubble_and_quick_window_skip_real_tk_construction_without_tk_root(self):
        with tempfile.TemporaryDirectory() as tempDir:
            context = self.makeContext(tempDir)
            root = FakeRoot()

            bubble = AssistantBubble(context, root=root)
            quickWindow = QuickInteractionWindow(context, root=root)

            self.assertIsNone(bubble.ensureWindow())
            self.assertIsNone(quickWindow.ensureWindow())

            bubble.show()
            quickWindow.show()

            self.assertIsNone(bubble.window)
            self.assertIsNone(quickWindow.window)

    def test_bubble_drag_updates_geometry_and_persists_position(self):
        with tempfile.TemporaryDirectory() as tempDir:
            context = self.makeContext(tempDir)
            bubble = AssistantBubble(context, root=FakeRoot(), positionManager=OverlayPositionManager(context, storagePath=str(Path(tempDir) / "bubble.json")))
            bubble.window = FakeBubbleWindow()

            bubble._onDragStart(SimpleNamespace(x_root=100, y_root=100))
            bubble._onDragMove(SimpleNamespace(x_root=160, y_root=145))
            bubble._onDragEnd(SimpleNamespace(x_root=160, y_root=145))

            self.assertEqual(bubble.window.x, 100)
            self.assertEqual(bubble.window.y, 95)
            self.assertEqual(bubble.positionManager.load().x, 100)
            self.assertEqual(bubble.positionManager.load().y, 95)

    def test_bubble_click_without_drag_opens_assistant(self):
        with tempfile.TemporaryDirectory() as tempDir:
            context = self.makeContext(tempDir)
            opened = []
            bubble = AssistantBubble(context, root=FakeRoot(), onOpen=lambda: opened.append(True))
            bubble.window = FakeBubbleWindow()

            bubble._onDragStart(SimpleNamespace(x_root=100, y_root=100))
            bubble._onDragEnd(SimpleNamespace(x_root=100, y_root=100))

            self.assertEqual(opened, [True])

    def test_bubble_style_uses_blue_chat_bubble_dimensions(self):
        with tempfile.TemporaryDirectory() as tempDir:
            context = self.makeContext(tempDir)
            bubble = AssistantBubble(context, root=FakeRoot())
            style = bubble._bubbleStyle()

            self.assertEqual(style["diameter"], 56)
            self.assertEqual(style["bubble"], "#2f73b6")
            self.assertEqual(style["outline"], "#8ec3ff")
            self.assertEqual(style["shell"], "#07111d")

    def test_bubble_requests_transparent_corners_on_windows(self):
        with tempfile.TemporaryDirectory() as tempDir:
            context = self.makeContext(tempDir)
            bubble = AssistantBubble(context, root=FakeRoot())
            window = FakeBubbleWindow()
            bubble._applyBubbleMask(window, bubble._bubbleStyle())

            self.assertTrue(
                any(
                    args and args[0] == "-transparentcolor"
                    for args, _kwargs in window.attributes_calls
                )
            )

    def test_bubble_is_a_small_circle_without_text_surface(self):
        with tempfile.TemporaryDirectory() as tempDir:
            context = self.makeContext(tempDir)
            bubble = AssistantBubble(context, root=FakeRoot())

            self.assertIsNone(getattr(bubble, "contentFrame", None))
            self.assertIsNone(getattr(bubble, "canvas", None))

    def test_bubble_drag_does_not_open_assistant(self):
        with tempfile.TemporaryDirectory() as tempDir:
            context = self.makeContext(tempDir)
            opened = []
            bubble = AssistantBubble(context, root=FakeRoot(), onOpen=lambda: opened.append(True))
            bubble.window = FakeBubbleWindow()

            bubble._onDragStart(SimpleNamespace(x_root=100, y_root=100))
            bubble._onDragMove(SimpleNamespace(x_root=160, y_root=145))
            bubble._onDragEnd(SimpleNamespace(x_root=160, y_root=145))

            self.assertEqual(opened, [])

    def test_window_lifecycle_manager_honors_nested_config_on_close_behavior(self):
        with tempfile.TemporaryDirectory() as tempDir:
            context = self.makeContext(tempDir)
            root = FakeRoot()
            app = FakeApp(root)
            lifecycle = WindowLifecycleManager(context, app=app)
            lifecycle.bindWindow(root)

            self.assertEqual(lifecycle.closeBehavior, "tray")
            consumed = lifecycle.handleCloseRequest()

            self.assertTrue(consumed)
            self.assertTrue(root.withdrawn)
            self.assertFalse(root.destroyed)

    def test_exit_request_shuts_down_the_shell(self):
        with tempfile.TemporaryDirectory() as tempDir:
            context = self.makeContext(tempDir)
            context.config._data["interface"]["desktop"]["windows"]["minimizeToTrayOnClose"] = False
            root = FakeRoot()
            app = FakeApp(root)
            manager = OverlayManager(context, root=root, app=app)
            manager.start()

            manager.requestExit("tray")

            self.assertTrue(app.exitRequested)
            self.assertTrue(root.quit_called)
            self.assertTrue(root.destroyed)
            self.assertTrue(context.should_exit)

    def test_event_handler_updates_overlay_state_without_recursing_shutdown(self):
        with tempfile.TemporaryDirectory() as tempDir:
            context = self.makeContext(tempDir)
            manager = FakeOverlayManager()
            handler = OverlayEventHandler(context, manager)

            handler.handleEvent(SimpleNamespace(name="wakeword.detected", data={"phrase": "Hey Aura", "confidence": 0.8}))
            handler.handleEvent(SimpleNamespace(name="notification.created", data={"title": "Motion detected downstairs"}))
            handler.handleEvent(SimpleNamespace(name="assistant.shutdown.requested", data={"reason": "tray"}))

            self.assertIn(("assistant", ("LISTENING", "Hey Aura")), manager.calls)
            self.assertTrue(any(call[0] == "notification" for call in manager.calls))
            self.assertIn(("mark", "assistant.shutdown.requested"), manager.calls)
            self.assertNotIn(("exit", "tray"), manager.calls)

    def test_position_manager_persists_and_clamps_geometry(self):
        with tempfile.TemporaryDirectory() as tempDir:
            context = self.makeContext(tempDir)
            storage = Path(tempDir) / "overlay.json"
            manager = OverlayPositionManager(context, storagePath=str(storage))
            position = manager.clamp(OverlayPosition(x=5000, y=5000, width=800, height=600), 1920, 1080)
            manager.save(position)
            loaded = manager.load()

            self.assertLessEqual(loaded.x, 1120)
            self.assertLessEqual(loaded.y, 480)
            self.assertEqual(loaded.width, 800)
            self.assertEqual(loaded.height, 600)


if __name__ == "__main__":
    unittest.main()
