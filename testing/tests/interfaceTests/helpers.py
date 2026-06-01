"""Shared test doubles for interface testing.tests."""

from types import SimpleNamespace

from modules.home_automation.models import BridgeState, CameraDevice, LightDevice
from testing.tests.support.fakes import TestContext


class FakeInterpreter:
    """Minimal interpreter stub for chat route testing.tests."""

    def interpret(self, message):
        return {"text": message}


class FakeRouter:
    """Minimal router stub for chat route testing.tests."""

    def route(self, intent):
        return f"handled {intent['text']}"


class FakeNotifications:
    """Notification backend stub for interface route testing.tests."""

    def __init__(self):
        self.deleted = []

    def listNotifications(self, status=None, limit=None):
        rows = [{"id": 4, "title": "Alert", "status": status or "pending"}]
        return rows[:limit] if limit else rows

    def deleteNotification(self, notification_id):
        self.deleted.append(notification_id)


class FakePersonalSchedule:
    """Unified personal schedule backend stub for interface route testing.tests."""

    def __init__(self):
        self.rows = [
            {
                "itemId": "1",
                "title": "Standup",
                "description": "Morning check-in",
                "type": "REMINDER",
                "dueTime": "2026-05-20T09:00:00",
                "priority": "NORMAL",
                "state": "PENDING",
                "tags": ["work"],
                "metadata": {},
            }
        ]
        self.deleted = []

    def listScheduleItems(self, itemType=None, state=None):
        rows = list(self.rows)
        if itemType:
            rows = [row for row in rows if row["type"] == str(itemType).upper()]
        if state:
            rows = [row for row in rows if row["state"] == str(state).upper()]
        return [SimpleNamespace(**row) for row in rows]

    def getTodaysSchedule(self):
        return {"title": "Today", "count": len(self.rows), "items": list(self.rows)}

    def getUpcomingSchedule(self, limit=10):
        return {"title": "Upcoming", "count": len(self.rows[:limit]), "items": list(self.rows[:limit])}

    def buildDayView(self, day):
        return {
            "day": day,
            "summary": "1 item(s)",
            "items": list(self.rows),
            "events": [],
            "tasks": [],
            "reminders": list(self.rows),
            "timers": [],
            "bills": [],
            "routines": [],
            "deadlines": [],
        }

    def buildWeekView(self, day):
        return {
            "week_start": day,
            "week_end": day,
            "days": [],
            "events": [],
            "tasks": [],
            "reminders": [],
            "timers": [],
            "bills": [],
            "routines": [],
            "deadlines": [],
        }

    def buildMonthView(self, month_value):
        return {
            "month": str(month_value)[:7],
            "days": [],
            "events": [],
            "tasks": [],
            "reminders": [],
            "timers": [],
            "bills": [],
            "routines": [],
            "deadlines": [],
        }

    def searchSchedule(self, query, limit=20):
        return {"title": f"Search: {query}", "count": len(self.rows), "items": list(self.rows[:limit])}

    def createScheduleItem(self, **fields):
        item = {
            "itemId": "2",
            "title": fields.get("title", ""),
            "description": fields.get("description", ""),
            "type": str(fields.get("type") or "EVENT").upper(),
            "startTime": fields.get("startTime", ""),
            "endTime": fields.get("endTime", ""),
            "dueTime": fields.get("dueTime", ""),
            "priority": fields.get("priority", "NORMAL"),
            "state": "PENDING",
            "tags": list(fields.get("tags") or []),
            "metadata": dict(fields.get("metadata") or {}),
        }
        self.rows.append(item)
        return SimpleNamespace(**item)

    def updateScheduleItem(self, item_id, **fields):
        for row in self.rows:
            if str(row["itemId"]) == str(item_id):
                row.update(fields)
                return SimpleNamespace(**row)
        return SimpleNamespace(itemId=str(item_id))

    def deleteScheduleItem(self, item_id):
        self.deleted.append(item_id)
        self.rows = [row for row in self.rows if str(row["itemId"]) != str(item_id)]

    def createReminder(self, **fields):
        return self.createScheduleItem(type="REMINDER", **fields)

    def createTask(self, **fields):
        return self.createScheduleItem(type="TASK", **fields)

    def createTimer(self, **fields):
        return self.createScheduleItem(type="TIMER", **fields)


class FakeHomeAutomation:
    """Home automation backend stub for interface route testing.tests."""

    def __init__(self):
        self.state = BridgeState(
            connected=True,
            bridge_name="Home Automation Bridge",
            lights=[LightDevice("light1", "Kitchen Light", "light", is_on=False, brightness=0, color="warm_white")],
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

    def getLightState(self, device_id):
        return self.state.lights[0]

    def getLightStateByRoom(self, room):
        return self.state.lights[0]

    def setLightColorByRoom(self, room, color):
        return self.setLightColor(room, color)

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
    """Build a context with enough backend services for interface testing.tests."""

    context = TestContext()
    context.logger = None
    context.should_exit = False
    context.interpreter = FakeInterpreter()
    context.intentRouter = FakeRouter()
    context.notifications = FakeNotifications()
    context.personalSchedule = FakePersonalSchedule()
    context.homeAutomation = FakeHomeAutomation()
    return context
