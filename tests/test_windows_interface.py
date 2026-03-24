"""Regression tests for Aura's Windows desktop interface layer."""

import unittest
from queue import Queue
from types import SimpleNamespace
from unittest.mock import patch

from tests.support.fakes import make_context


class _FakeChildLogger:
    """Minimal logger child used by the Windows interface tests."""

    def __init__(self):
        """Initialize the fake logger with captured child requests."""

        self.children = []
        self.messages = []

    def getChild(self, name):
        """Return another fake child logger."""

        self.children.append(name)
        return self

    def info(self, message):
        """Record an info log call."""

        self.messages.append(("info", message))

    def error(self, message):
        """Record an error log call."""

        self.messages.append(("error", message))

    def debug(self, message):
        """Record a debug log call."""

        self.messages.append(("debug", message))

    def close(self):
        """Record logger shutdown for bootstrap tests."""

        self.messages.append(("close", None))


class _FakeConfigLoader:
    """Simple config loader stub for runtime bootstrap tests."""

    def __init__(self, context):
        """Attach a deterministic config payload to the runtime context."""

        self.context = context


class _FakeThreadingManager:
    """Threading manager placeholder used during bootstrap tests."""

    def __init__(self, context):
        """Store the runtime context."""

        self.context = context


class _FakeEventManager:
    """Event manager placeholder used during bootstrap tests."""

    def __init__(self, context):
        """Store the runtime context."""

        self.context = context


class _FakeTaskManager:
    """Task manager placeholder used during bootstrap tests."""

    def __init__(self, context):
        """Store the runtime context."""

        self.context = context


class _FakeScheduler:
    """Scheduler stub that records start and stop calls."""

    def __init__(self, context):
        """Initialize scheduler state."""

        self.context = context
        self.started = False
        self.stopped = False

    def start(self):
        """Record that scheduler startup occurred."""

        self.started = True

    def stop(self):
        """Record that scheduler shutdown occurred."""

        self.stopped = True


class _FakeDatabase:
    """Database stub for bootstrap tests."""

    def __init__(self, context):
        """Initialize connection lifecycle state."""

        self.context = context
        self.connected = False
        self.initialized = False
        self.closed = False

    def connect(self):
        """Record a database connection attempt."""

        self.connected = True

    def initialize(self):
        """Record database schema initialization."""

        self.initialized = True

    def close(self):
        """Record database shutdown."""

        self.closed = True


class _FakeMemoryManager:
    """Memory manager placeholder used during bootstrap tests."""

    def __init__(self, context):
        """Store the runtime context."""

        self.context = context


class _FakeConversationHistory:
    """Conversation history placeholder used during bootstrap tests."""

    def __init__(self, context):
        """Store the runtime context."""

        self.context = context


class _FakeLLMHandler:
    """LLM handler placeholder used during bootstrap tests."""

    def __init__(self, context):
        """Store the runtime context."""

        self.context = context


class _FakeInterpreter:
    """Interpreter placeholder used during bootstrap tests."""

    def __init__(self, context):
        """Store the runtime context."""

        self.context = context


class _FakeIntentRouter:
    """Intent router placeholder used during bootstrap tests."""

    def __init__(self, context):
        """Store the runtime context."""

        self.context = context


class _FakeInputManager:
    """Input manager stub used during bootstrap tests."""

    def __init__(self, context):
        """Store the runtime context."""

        self.context = context


class _FakeOutputManager:
    """Output manager stub used during bootstrap tests."""

    def __init__(self, context):
        """Store the runtime context."""

        self.context = context


class _FakeModuleLoader:
    """Module loader stub that records whether loading happened."""

    def __init__(self, context):
        """Store the runtime context and initialize call tracking."""

        self.context = context
        self.loaded = False

    def loadModules(self):
        """Record module loading."""

        self.loaded = True


class _FakeEngine:
    """Engine placeholder used during bootstrap tests."""

    def __init__(self, context):
        """Store the runtime context."""

        self.context = context


class _FakeWidget:
    """Base widget stub that records configuration and geometry calls."""

    def __init__(self, *args, **kwargs):
        """Initialize shared widget state."""

        self.args = args
        self.kwargs = dict(kwargs)
        self.pack_calls = []
        self.place_calls = []
        self.bindings = {}
        self.state = kwargs.get("state")
        self.text = kwargs.get("text", "")
        self.destroyed = False

    def pack(self, *args, **kwargs):
        """Record a pack geometry request."""

        self.pack_calls.append((args, kwargs))

    def pack_forget(self):
        """Record that the widget was hidden."""

        self.pack_calls.append(("forget", {}))

    def pack_propagate(self, flag):
        """Record pack propagation changes."""

        self.pack_calls.append((("propagate", flag), {}))

    def place(self, *args, **kwargs):
        """Record a place geometry request."""

        self.place_calls.append((args, kwargs))

    def place_forget(self):
        """Record that the placed widget was hidden."""

        self.place_calls.append(("forget", {}))

    def configure(self, **kwargs):
        """Apply widget configuration updates."""

        self.kwargs.update(kwargs)
        if "state" in kwargs:
            self.state = kwargs["state"]
        if "text" in kwargs:
            self.text = kwargs["text"]

    config = configure

    def bind(self, event_name, callback):
        """Record an event binding."""

        self.bindings[event_name] = callback

    def destroy(self):
        """Record widget destruction."""

        self.destroyed = True

    def lift(self):
        """Support lift calls from the sidebar drawer."""

        return None


class _FakeEntry(_FakeWidget):
    """Entry widget stub with mutable text content."""

    def __init__(self, *args, **kwargs):
        """Initialize entry state."""

        super().__init__(*args, **kwargs)
        self.value = ""
        self.focused = False

    def get(self):
        """Return the current entry value."""

        return self.value

    def delete(self, start, end=None):
        """Clear the entry value."""

        self.value = ""

    def insert(self, index, value):
        """Set the entry value."""

        self.value = value

    def focus_set(self):
        """Record that focus moved to the entry."""

        self.focused = True


class _FakeScrolledText(_FakeWidget):
    """ScrolledText stub that stores written transcript content."""

    def __init__(self, *args, **kwargs):
        """Initialize text state."""

        super().__init__(*args, **kwargs)
        self.content = ""

    def insert(self, index, value):
        """Append content to the text widget."""

        self.content += value

    def see(self, index):
        """Ignore scroll requests during tests."""

        return None


class _FakeRoot(_FakeWidget):
    """Tk root stub for exercising the Windows UI without a real display."""

    def __init__(self):
        """Initialize root window state."""

        super().__init__()
        self.protocols = {}
        self.after_calls = []
        self.mainloop_called = False
        self.window_exists = True
        self.title_value = None
        self.geometry_value = None
        self.minsize_value = None

    def title(self, value):
        """Record the requested window title."""

        self.title_value = value

    def geometry(self, value):
        """Record the requested geometry."""

        self.geometry_value = value

    def minsize(self, width, height):
        """Record the minimum window size."""

        self.minsize_value = (width, height)

    def protocol(self, name, callback):
        """Record protocol callbacks such as close handling."""

        self.protocols[name] = callback

    def after(self, delay, callback):
        """Record scheduled callbacks without running them automatically."""

        self.after_calls.append((delay, callback))

    def mainloop(self):
        """Record that the event loop was entered."""

        self.mainloop_called = True

    def winfo_exists(self):
        """Report whether the window still exists."""

        return self.window_exists

    def destroy(self):
        """Destroy the root window."""

        self.destroyed = True
        self.window_exists = False


class _ImmediateThread:
    """Thread replacement that runs work synchronously in tests."""

    def __init__(self, target=None, args=(), daemon=None):
        """Store the target and arguments for immediate execution."""

        self.target = target
        self.args = args
        self.daemon = daemon

    def start(self):
        """Execute the worker immediately on the calling thread."""

        if self.target is not None:
            self.target(*self.args)


class _FakeNotifications:
    """Notification service stub used by Windows UI tests."""

    def __init__(self):
        """Initialize notification rows and deletion tracking."""

        self.rows = [
            {
                "id": 1,
                "title": "Older",
                "content": "Older content",
                "notification_at": "2026-03-24 09:00:00",
            },
            {
                "id": 2,
                "title": "Newest",
                "content": "Newest content",
                "notification_at": "2026-03-24 10:00:00",
            },
        ]
        self.deleted_ids = []

    def listNotifications(self):
        """Return the current notification rows."""

        return [dict(row) for row in self.rows]

    def deleteNotification(self, notification_id):
        """Delete one notification row and record the request."""

        self.deleted_ids.append(notification_id)
        self.rows = [row for row in self.rows if row["id"] != notification_id]


class _FakeReminders:
    """Reminder service stub used by Windows UI tests."""

    def __init__(self):
        """Initialize reminder rows and creation tracking."""

        self.rows = [
            {
                "id": 1,
                "title": "Morning meds",
                "content": "Take with water",
                "reminder_at": "2026-03-24 08:00:00",
            },
            {
                "id": 2,
                "title": "Dentist",
                "content": "Bring insurance card",
                "reminder_at": "2026-03-24 13:30:00",
            },
        ]
        self.created = []

    def listReminders(self):
        """Return the current reminder rows."""

        return [dict(row) for row in self.rows]

    def createReminder(self, title, content, module_of_origin, reminder_at=None):
        """Store one reminder row and return its ID."""

        reminder_id = len(self.rows) + 1
        self.created.append((title, content, module_of_origin, reminder_at))
        self.rows.append(
            {
                "id": reminder_id,
                "title": title,
                "content": content,
                "reminder_at": "2026-03-25 14:45:00",
            }
        )
        return reminder_id


class WindowsRuntimeBootstrapTests(unittest.TestCase):
    """Test the lifecycle helpers used by the Windows bootstrap layer."""

    @patch("core.interface.desktopInterface.windows.windowsRuntimeBootstrap.Engine", _FakeEngine)
    @patch("core.interface.desktopInterface.windows.windowsRuntimeBootstrap.ModuleLoader", _FakeModuleLoader)
    @patch("core.interface.desktopInterface.windows.windowsRuntimeBootstrap.OutputManager", _FakeOutputManager)
    @patch("core.interface.desktopInterface.windows.windowsRuntimeBootstrap.InputManager", _FakeInputManager)
    @patch("core.interface.desktopInterface.windows.windowsRuntimeBootstrap.IntentRouter", _FakeIntentRouter)
    @patch("core.interface.desktopInterface.windows.windowsRuntimeBootstrap.Interpreter", _FakeInterpreter)
    @patch("core.interface.desktopInterface.windows.windowsRuntimeBootstrap.LLMHandler", _FakeLLMHandler)
    @patch("core.interface.desktopInterface.windows.windowsRuntimeBootstrap.ConversationHistory", _FakeConversationHistory)
    @patch("core.interface.desktopInterface.windows.windowsRuntimeBootstrap.MemoryManager", _FakeMemoryManager)
    @patch("core.interface.desktopInterface.windows.windowsRuntimeBootstrap.MySQLDatabase", _FakeDatabase)
    @patch("core.interface.desktopInterface.windows.windowsRuntimeBootstrap.Scheduler", _FakeScheduler)
    @patch("core.interface.desktopInterface.windows.windowsRuntimeBootstrap.TaskManager", _FakeTaskManager)
    @patch("core.interface.desktopInterface.windows.windowsRuntimeBootstrap.EventManager", _FakeEventManager)
    @patch("core.interface.desktopInterface.windows.windowsRuntimeBootstrap.ThreadingManager", _FakeThreadingManager)
    @patch("core.interface.desktopInterface.windows.windowsRuntimeBootstrap.ConfigLoader", _FakeConfigLoader)
    @patch("core.interface.desktopInterface.windows.windowsRuntimeBootstrap.AuraLogger", _FakeChildLogger)
    def test_create_runtime_context_and_lifecycle(self):
        """Bootstrap should initialize core services and clean them up on shutdown."""

        from core.interface.desktopInterface.windows.windowsRuntimeBootstrap import (
            createRuntimeContext,
            shutdown,
            startup,
        )

        context = createRuntimeContext()

        self.assertTrue(context.database.connected)
        self.assertTrue(context.database.initialized)
        self.assertIsNotNone(context.engine)
        self.assertFalse(context.should_exit)

        startup(context)
        self.assertTrue(context.scheduler.started)

        shutdown(context)
        self.assertTrue(context.scheduler.stopped)
        self.assertTrue(context.database.closed)
        self.assertIn(("close", None), context.logger.messages)


class WindowsRuntimeEntrypointTests(unittest.TestCase):
    """Test the top-level Windows entrypoint behavior."""

    @patch("core.interface.desktopInterface.windows.runAuraWindows.showStandaloneErrorPopup")
    @patch("core.interface.desktopInterface.windows.runAuraWindows.shutdown")
    @patch("core.interface.desktopInterface.windows.runAuraWindows.startup")
    @patch("core.interface.desktopInterface.windows.runAuraWindows.createRuntimeContext")
    @patch("core.interface.desktopInterface.windows.runAuraWindows.AuraWindowsApp")
    def test_main_shows_popup_and_shuts_down_on_gui_error(
        self,
        app_class,
        create_runtime_context,
        startup_runtime,
        shutdown_runtime,
        show_popup,
    ):
        """The entrypoint should surface GUI startup failures and still shut down cleanly."""

        from core.interface.desktopInterface.windows.runAuraWindows import main

        context = SimpleNamespace()
        create_runtime_context.return_value = context
        app_class.side_effect = RuntimeError("boom")

        main()

        startup_runtime.assert_called_once_with(context)
        shutdown_runtime.assert_called_once_with(context)
        show_popup.assert_called_once()
        self.assertIn("boom", show_popup.call_args.args[0])


class AuraWindowsAppTests(unittest.TestCase):
    """Test the reduced-scope Windows desktop shell."""

    def _build_context(self):
        """Construct a headless context suitable for the Windows app tests."""

        logger = _FakeChildLogger()
        context = make_context(extra={"logger": logger})
        context.inputManager = SimpleNamespace()
        context.notifications = _FakeNotifications()
        context.reminders = _FakeReminders()
        context.should_exit = False
        return context

    def _create_app(self, context):
        """Create the Windows app with Tk widgets patched out."""

        from core.interface.desktopInterface.windows.auraWindowsApp import AuraWindowsApp

        patches = [
            patch("core.interface.desktopInterface.windows.auraWindowsApp.Tk", _FakeRoot),
            patch("core.interface.desktopInterface.windows.auraWindowsApp.Frame", _FakeWidget),
            patch("core.interface.desktopInterface.windows.auraWindowsApp.Label", _FakeWidget),
            patch("core.interface.desktopInterface.windows.auraWindowsApp.Button", _FakeWidget),
            patch("core.interface.desktopInterface.windows.auraWindowsApp.Entry", _FakeEntry),
            patch("core.interface.desktopInterface.windows.auraWindowsApp.ScrolledText", _FakeScrolledText),
            patch("core.interface.desktopInterface.windows.auraWindowsApp.Thread", _ImmediateThread),
        ]

        for patched in patches:
            patched.start()
            self.addCleanup(patched.stop)

        return AuraWindowsApp(context)

    def test_submit_flow_appends_response_to_transcript(self):
        """Submitting text should call the input API and append the response."""

        context = self._build_context()
        submitted = []

        def _submit(text, source="api", metadata=None):
            submitted.append((text, source, metadata))
            return {"response": "Hello from Aura"}

        context.inputManager.submit = _submit

        app = self._create_app(context)
        app.inputEntry.value = "hello"

        app._onSubmit()
        app._pollPendingResponses()

        self.assertEqual(submitted, [("hello", "windows", None)])
        self.assertIn("You: hello", app.transcript.content)
        self.assertIn("Aura: Hello from Aura", app.transcript.content)
        self.assertFalse(app.isBusy)

    def test_sidebar_toggle_and_page_selection(self):
        """The drawer should toggle visibility and switch between placeholder pages."""

        context = self._build_context()
        context.inputManager.submit = lambda *args, **kwargs: {"response": "ok"}

        app = self._create_app(context)

        self.assertEqual(app.activePage, "chat")
        self.assertFalse(app.sidebarVisible)

        app._toggleSidebar()
        self.assertTrue(app.sidebarVisible)
        self.assertTrue(app.sidebar.place_calls)

        app._showCalendarPage()
        self.assertEqual(app.activePage, "calendar")
        self.assertFalse(app.sidebarVisible)

    def test_reminders_page_lists_existing_reminders(self):
        """Reminder page should render the currently scheduled reminder rows."""

        context = self._build_context()
        context.inputManager.submit = lambda *args, **kwargs: {"response": "ok"}

        app = self._create_app(context)
        app._showRemindersPage()

        self.assertEqual(app.activePage, "reminders")
        self.assertEqual(len(app.renderedReminderItems), 2)
        self.assertEqual(app.renderedReminderItems[0]["row"]["title"], "Morning meds")
        self.assertEqual(app.renderedReminderItems[1]["row"]["title"], "Dentist")

    def test_header_contains_placeholder_notification_and_profile_buttons(self):
        """The header should expose right-side placeholder action buttons."""

        context = self._build_context()
        context.inputManager.submit = lambda *args, **kwargs: {"response": "ok"}

        app = self._create_app(context)

        self.assertEqual(app.notificationButton.text, "N")
        self.assertEqual(app.profileButton.text, "P")
        self.assertTrue(app.notificationButton.pack_calls)
        self.assertTrue(app.profileButton.pack_calls)

    def test_notification_button_toggles_persistent_overlay(self):
        """Notification button should show and hide one shared overlay panel."""

        context = self._build_context()
        context.inputManager.submit = lambda *args, **kwargs: {"response": "ok"}

        app = self._create_app(context)

        self.assertFalse(app.notificationsVisible)

        app._onNotificationPressed()
        self.assertTrue(app.notificationsVisible)
        self.assertTrue(app.notificationsOverlay.place_calls)
        self.assertTrue(app.notificationsListContainer.pack_calls)
        self.assertEqual(app.renderedNotificationItems[0]["row"]["title"], "Newest")
        self.assertEqual(app.renderedNotificationItems[1]["row"]["title"], "Older")

        app._showCalendarPage()
        self.assertTrue(app.notificationsVisible)

        app._onNotificationPressed()
        self.assertFalse(app.notificationsVisible)
        self.assertIn(("forget", {}), app.notificationsOverlay.place_calls)

    def test_notification_delete_button_removes_row_and_refreshes_overlay(self):
        """Deleting one notification should remove it from the backend and rendered list."""

        context = self._build_context()
        context.inputManager.submit = lambda *args, **kwargs: {"response": "ok"}

        app = self._create_app(context)
        app._onNotificationPressed()

        app._deleteNotification(2)

        self.assertEqual(context.notifications.deleted_ids, [2])
        self.assertEqual(len(app.renderedNotificationItems), 1)
        self.assertEqual(app.renderedNotificationItems[0]["row"]["title"], "Older")

    def test_reminder_create_overlay_creates_reminder_and_refreshes_list(self):
        """Reminder composer should create a reminder and refresh the rendered list."""

        context = self._build_context()
        context.inputManager.submit = lambda *args, **kwargs: {"response": "ok"}

        app = self._create_app(context)
        app._showRemindersPage()

        self.assertFalse(app.reminderComposerVisible)

        app._toggleReminderComposer()
        self.assertTrue(app.reminderComposerVisible)

        app.reminderTitleEntry.value = "Pick up package"
        app.reminderDescriptionEntry.value = "Front desk"
        app.reminderDateEntry.value = "25/03/2026"
        app.reminderTimeEntry.value = "14:45"

        app._createReminderFromComposer()

        self.assertEqual(
            context.reminders.created,
            [("Pick up package", "Front desk", "windows", "14:45 25/03/2026")],
        )
        self.assertFalse(app.reminderComposerVisible)
        self.assertEqual(len(app.renderedReminderItems), 3)
        self.assertEqual(app.renderedReminderItems[-1]["row"]["title"], "Pick up package")

    def test_processing_error_shows_popup(self):
        """Worker failures should display an error popup and reset busy state."""

        context = self._build_context()

        def _submit(text, source="api", metadata=None):
            raise RuntimeError("broken request")

        context.inputManager.submit = _submit

        app = self._create_app(context)
        app.pendingResponses = Queue()
        app.inputEntry.value = "hello"

        with patch.object(app, "_showErrorPopup") as show_popup:
            app._onSubmit()
            app._pollPendingResponses()

        show_popup.assert_called_once()
        self.assertIn("broken request", show_popup.call_args.args[0])
        self.assertIn("Aura: Error: broken request", app.transcript.content)
        self.assertFalse(app.isBusy)


if __name__ == "__main__":
    unittest.main()
