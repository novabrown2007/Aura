"""Tests for Aura's unified weather module."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from types import SimpleNamespace
import tempfile
import unittest

from core.threading.events.eventManager import EventManager
from modules.weather import WeatherModule
from modules.weather.models import WeatherAlert, WeatherData, WeatherForecast, WeatherSource
from modules.weather.weatherManager import WeatherManager
from testing.tests.support.fakes import make_context


class FakeNotificationManager:
    """Capture weather notification payloads without invoking the full attention stack."""

    def __init__(self):
        self.created = []

    def createNotification(self, payload, eventName=""):
        record = {"payload": dict(payload), "eventName": eventName}
        self.created.append(record)
        return record


class FakeWeatherApiProvider:
    """Deterministic API provider used for weather fallback testing.tests."""

    def __init__(self):
        self.currentCalls = 0
        self.hourlyCalls = 0
        self.weeklyCalls = 0
        self.alertCalls = 0
        self.available = True

    def initialize(self, context=None):
        return self

    def isAvailable(self):
        return bool(self.available)

    def shutdown(self):
        return None

    def getCurrentWeather(self, location: str):
        self.currentCalls += 1
        return WeatherData(
            location=location or "Toronto",
            temperature=18.0,
            humidity=71.0,
            pressure=1008.0,
            windSpeed=12.0,
            windDirection="SW",
            condition="cloudy",
            visibility=8.0,
            uvIndex=1.0,
            feelsLike=16.0,
            source=WeatherSource.WEATHER_API,
            timestamp=_now(),
            metadata={"provider": "fake"},
        )

    def getHourlyForecast(self, location: str, hours: int = 24):
        self.hourlyCalls += 1
        return WeatherForecast(
            location=location or "Toronto",
            source=WeatherSource.WEATHER_API,
            timestamp=_now(),
            hourly=[{"hour": 1, "temperature": 18.0, "condition": "cloudy"} for _ in range(max(1, int(hours)))],
            daily=[],
            alerts=[],
            metadata={"provider": "fake"},
        )

    def getWeeklyForecast(self, location: str, days: int = 7):
        self.weeklyCalls += 1
        return WeatherForecast(
            location=location or "Toronto",
            source=WeatherSource.WEATHER_API,
            timestamp=_now(),
            hourly=[],
            daily=[{"day": index + 1, "temperature": 18.0 + index, "condition": "cloudy"} for index in range(max(1, int(days)))],
            alerts=[],
            metadata={"provider": "fake"},
        )

    def getAlerts(self, location: str):
        self.alertCalls += 1
        return [
            WeatherAlert(
                alertId="alert-1",
                title="Tornado warning",
                message="Tornado warning issued for the area.",
                severity="CRITICAL",
                alertType="tornado",
                source="fake-api",
                issuedAt=_now(),
                location=location or "Toronto",
            )
        ]


class WeatherModuleTests(unittest.TestCase):
    """Validate the unified weather capability and its fallback behavior."""

    def setUp(self):
        self.tempDir = tempfile.TemporaryDirectory()
        self.context = make_context()
        self.context.config._data["weather"] = {
            "weatherEnabled": True,
            "weatherApiEnabled": True,
            "localSensorWeatherEnabled": True,
            "weatherAlertsEnabled": True,
            "weatherThresholdNotificationsEnabled": True,
            "weatherForecastCacheEnabled": True,
            "weatherRefreshIntervalMinutes": 15,
            "preferredWeatherProvider": "openweathermap",
            "databasePath": str(Path(self.tempDir.name) / "weather.sqlite3"),
            "defaultLocation": "Toronto",
            "api": {
                "baseUrl": "",
                "apiKey": "",
                "timeoutSeconds": 5,
            },
        }
        self.context.logger = None
        self.context.eventManager = EventManager(self.context)
        self.context.notificationManager = FakeNotificationManager()
        self.cleanupTargets = []

    def tearDown(self):
        for target in self.cleanupTargets:
            if hasattr(target, "shutdown"):
                target.shutdown()
        self.tempDir.cleanup()

    def test_module_exposes_standard_weather_contract(self):
        module = WeatherModule()
        tools = {tool.name for tool in module.getTools()}
        self.assertEqual(module.metadata.name, "weather")
        self.assertGreaterEqual(len(module.getIntents()), 1)
        self.assertGreaterEqual(len(module.getActions()), 1)
        self.assertGreaterEqual(len(module.getTools()), 1)
        self.assertIn("weather.read", module.metadata.capabilities)
        self.assertIn("weather.getCurrent", tools)
        self.assertIn("weather.getHourlyForecast", tools)
        self.assertIn("weather.getWeeklyForecast", tools)
        self.assertIn("weather.getIndoorTemperature", tools)
        self.assertIn("weather.getAlerts", tools)
        self.assertIn("weather.addThreshold", tools)
        self.assertIn("weather.addLocation", tools)
        self.assertIn("weather.listLocations", tools)
        self.assertEqual(module.getCurrentWeather("Toronto")["location"], "Toronto")

    def test_bridge_sensors_take_priority_over_api(self):
        bridgeState = SimpleNamespace(
            devices=[
                {
                    "id": "sensor-bedroom-temp",
                    "name": "Bedroom Temperature",
                    "category": "sensor",
                    "sensorType": "temperature",
                    "value": 21.5,
                    "unit": "C",
                    "location": "Bedroom",
                    "online": True,
                },
                {
                    "id": "sensor-bedroom-humidity",
                    "name": "Bedroom Humidity",
                    "category": "sensor",
                    "sensorType": "humidity",
                    "value": 49.0,
                    "unit": "%",
                    "location": "Bedroom",
                    "online": True,
                },
            ]
        )
        self.context.homeAutomation = SimpleNamespace(getBridgeState=lambda: bridgeState)
        manager = self._makeManager()
        api = FakeWeatherApiProvider()
        manager.apiProvider = api
        manager.providerRouter.apiProvider = api

        weather = manager.getCurrentWeather("Bedroom")

        self.assertEqual(weather["source"], WeatherSource.LOCAL_SENSOR)
        self.assertEqual(weather["temperature"], 21.5)
        self.assertEqual(api.currentCalls, 0)

    def test_api_fallback_is_cached_when_sensors_missing(self):
        self.context.homeAutomation = SimpleNamespace(getBridgeState=lambda: SimpleNamespace(devices=[]))
        manager = self._makeManager()
        api = FakeWeatherApiProvider()
        manager.apiProvider = api
        manager.providerRouter.apiProvider = api

        first = manager.getCurrentWeather("Toronto")
        self.assertEqual(first["source"], WeatherSource.WEATHER_API)
        self.assertEqual(api.currentCalls, 1)

        api.available = False
        second = manager.getCurrentWeather("Toronto")

        self.assertEqual(second["source"], WeatherSource.CACHED_API)
        self.assertEqual(api.currentCalls, 1)

    def test_threshold_rules_trigger_notifications(self):
        self.context.homeAutomation = SimpleNamespace(
            getBridgeState=lambda: SimpleNamespace(
                devices=[
                    {
                        "id": "sensor-outdoor-temp",
                        "name": "Outdoor Temperature",
                        "category": "sensor",
                        "sensorType": "temperature",
                        "value": -15.0,
                        "unit": "C",
                        "location": "Toronto",
                        "online": True,
                    }
                ]
            )
        )
        manager = self._makeManager()
        manager.addThreshold(
            location="Toronto",
            metric="temperature",
            operator="<",
            value=-10,
            title="Freezing weather",
            message="Temperature dropped below freezing.",
            notificationPriority="HIGH",
        )

        weather = manager.getCurrentWeather("Toronto")

        self.assertEqual(weather["source"], WeatherSource.LOCAL_SENSOR)
        self.assertEqual(len(self.context.notificationManager.created), 1)
        self.assertEqual(self.context.notificationManager.created[0]["eventName"], "weather.threshold.triggered")
        self.assertEqual(self.context.notificationManager.created[0]["payload"]["title"], "Freezing weather")

    def test_emergency_weather_alerts_trigger_notifications(self):
        self.context.homeAutomation = SimpleNamespace(getBridgeState=lambda: SimpleNamespace(devices=[]))
        manager = self._makeManager()
        api = FakeWeatherApiProvider()
        manager.apiProvider = api
        manager.providerRouter.apiProvider = api

        alerts = manager.getAlerts("Toronto")

        self.assertEqual(len(alerts), 1)
        self.assertEqual(alerts[0]["severity"], "CRITICAL")
        self.assertEqual(self.context.notificationManager.created[0]["eventName"], "weather.alert.received")
        self.assertIn("Tornado warning", self.context.notificationManager.created[0]["payload"]["title"])

    def test_forecasts_support_multiple_locations(self):
        manager = self._makeManager()
        api = FakeWeatherApiProvider()
        manager.apiProvider = api
        manager.providerRouter.apiProvider = api
        manager.addLocation("Toronto", isHome=True)
        manager.addLocation("Windsor", isFavorite=True)

        weekly = manager.getWeeklyForecast("Toronto", days=3)
        hourly = manager.getHourlyForecast("Windsor", hours=4)
        compare = manager.queryEngine.compareLocations("Toronto", "Windsor")

        self.assertEqual(len(manager.listLocations()), 2)
        self.assertEqual(weekly["source"], WeatherSource.WEATHER_API)
        self.assertEqual(len(weekly["daily"]), 3)
        self.assertEqual(len(hourly["hourly"]), 4)
        self.assertIn("temperatureDifference", compare)

    def test_indoor_temperature_comes_from_bridge_sensor(self):
        bridgeState = SimpleNamespace(
            devices=[
                {
                    "id": "sensor-downstairs-temp",
                    "name": "Downstairs Temperature",
                    "category": "sensor",
                    "sensorType": "temperature",
                    "value": 19.0,
                    "unit": "C",
                    "location": "Downstairs",
                    "online": True,
                }
            ]
        )
        self.context.homeAutomation = SimpleNamespace(getBridgeState=lambda: bridgeState)
        manager = self._makeManager()

        indoor = manager.getIndoorTemperature("Downstairs")

        self.assertEqual(indoor["source"], WeatherSource.LOCAL_SENSOR)
        self.assertEqual(indoor["temperature"], 19.0)

    def _makeManager(self):
        manager = WeatherManager(self.context).initialize(self.context)
        self.cleanupTargets.append(manager)
        return manager


def _now():
    return datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")


if __name__ == "__main__":
    unittest.main()
