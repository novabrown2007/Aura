"""Shared test doubles for interface tests."""

from modules.home_automation.models import BridgeState, CameraDevice, LightDevice
from tests.support.fakes import TestContext


class FakeInterpreter:
    """Minimal interpreter stub for chat route tests."""

    def interpret(self, message):
        return {"text": message}


class FakeRouter:
    """Minimal router stub for chat route tests."""

    def route(self, intent):
        return f"handled {intent['text']}"


class FakeReminders:
    """Reminder backend stub for interface route tests."""

    def __init__(self):
        self.rows = [{"id": 1, "title": "Standup", "reminder_at": "2026-05-20 09:00:00"}]
        self.deleted = []

    def listReminders(self):
        return list(self.rows)

    def createReminder(self, title, content, module_of_origin, reminder_at=None):
        self.rows.append(
            {
                "id": 2,
                "title": title,
                "content": content,
                "module_of_origin": module_of_origin,
                "reminder_at": reminder_at,
            }
        )
        return 2

    def deleteReminder(self, reminder_id):
        self.deleted.append(reminder_id)


class FakeNotifications:
    """Notification backend stub for interface route tests."""

    def __init__(self):
        self.deleted = []

    def listNotifications(self, status=None, limit=None):
        rows = [{"id": 4, "title": "Alert", "status": status or "pending"}]
        return rows[:limit] if limit else rows

    def deleteNotification(self, notification_id):
        self.deleted.append(notification_id)


class FakeCalendar:
    """Calendar backend stub for interface route tests."""

    def __init__(self):
        self.created_events = []
        self.created_tasks = []
        self.created_reminders = []
        self.created_calendars = []

    def listCalendars(self):
        return [{"id": 7, "name": "Aura"}]

    def createCalendar(self, **fields):
        self.created_calendars.append(fields)

    def buildDayView(self, day, calendar_id=None):
        return {
            "day": day,
            "events": [{"id": 1, "title": "Event", "start_at": f"{day} 10:00:00"}],
            "tasks": [],
            "reminders": [],
        }

    def buildWeekView(self, day, calendar_id=None):
        return {"week_start": day, "week_end": day, "events": [], "tasks": [], "reminders": []}

    def buildMonthView(self, month_value, calendar_id=None):
        return {"month": str(month_value)[:7], "events": [], "tasks": [], "reminders": []}

    def _normalizeDateValue(self, value):
        return value

    def createEvent(self, **fields):
        self.created_events.append(fields)
        return 10

    def getEvent(self, event_id):
        return {"id": event_id}

    def updateEvent(self, event_id, **fields):
        self.updated_event = (event_id, fields)

    def deleteEvent(self, event_id):
        self.deleted_event = event_id

    def createTask(self, **fields):
        self.created_tasks.append(fields)
        return 20

    def getTask(self, task_id):
        return {"id": task_id}

    def updateTask(self, task_id, **fields):
        self.updated_task = (task_id, fields)

    def deleteTask(self, task_id):
        self.deleted_task = task_id

    def createReminder(self, **fields):
        self.created_reminders.append(fields)
        return 30

    def getReminder(self, reminder_id):
        return {"id": reminder_id}

    def updateReminder(self, reminder_id, **fields):
        self.updated_reminder = (reminder_id, fields)

    def deleteReminder(self, reminder_id):
        self.deleted_reminder = reminder_id

    def searchEvents(self, query=None, calendar_id=None):
        return [{"id": 1, "title": query or "Event"}]

    def searchTasks(self, query=None, calendar_id=None):
        return []

    def searchReminders(self, query=None, calendar_id=None):
        return []

    def detectConflicts(self, start_at, end_at, calendar_id=None, exclude_event_id=None):
        return [{"id": 1, "start_at": start_at, "end_at": end_at}]


class FakeHomeAutomation:
    """Home automation backend stub for interface route tests."""

    def __init__(self):
        self.state = BridgeState(
            connected=True,
            bridge_name="Home Automation Bridge",
            lights=[LightDevice("light1", "Kitchen Light", "light", is_on=False, brightness=0)],
            cameras=[CameraDevice("camera1", "Entry Camera", "camera")],
        )
        self.state.devices = [*self.state.lights, *self.state.cameras]

    def getBridgeState(self):
        return self.state

    def refresh(self):
        return self.state

    def startBridge(self):
        return {"status": "ok", "service": "bridge"}

    def startHub(self):
        return {"status": "ok", "service": "hub"}

    def toggleLight(self, device_id, is_on, brightness=None):
        light = self.state.lights[0]
        light.is_on = is_on
        if brightness is not None:
            light.brightness = brightness
        return light

    def setLightBrightness(self, device_id, brightness):
        self.state.lights[0].brightness = brightness
        return self.state.lights[0]

    def setLightTemperature(self, device_id, kelvin):
        self.state.lights[0].color_temperature_kelvin = kelvin
        return self.state.lights[0]

    def setLightColor(self, device_id, color):
        self.state.lights[0].color = color
        return self.state.lights[0]

    def startCameraStream(self, device_id):
        self.state.cameras[0].is_streaming = True
        return self.state.cameras[0]

    def stopCameraStream(self, device_id):
        self.state.cameras[0].is_streaming = False
        return self.state.cameras[0]

    def takeCameraSnapshot(self, device_id):
        self.state.cameras[0].snapshot_count += 1
        return self.state.cameras[0]

    def getNotifications(self):
        return []

    def queueNotification(self, source, severity, category, title, message, device_id=""):
        return {"status": "ok", "title": title}


def makeInterfaceContext():
    """Build a context with enough backend services for interface tests."""

    context = TestContext()
    context.logger = None
    context.should_exit = False
    context.interpreter = FakeInterpreter()
    context.intentRouter = FakeRouter()
    context.reminders = FakeReminders()
    context.notifications = FakeNotifications()
    context.calendar = FakeCalendar()
    context.homeAutomation = FakeHomeAutomation()
    return context
