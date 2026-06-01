"""Local sensor-backed weather provider for Aura."""

from __future__ import annotations

from typing import Any

from modules.weather.models import WeatherData, WeatherSource


class LocalWeatherProvider:
    """Build weather readings from connected bridge/environment sensors."""

    def __init__(self, context=None, sensorManager=None):
        self.context = context
        self.sensorManager = sensorManager
        self.logger = context.logger.getChild("Weather.Local") if context and getattr(context, "logger", None) else None

    def initialize(self, context=None):
        if context is not None:
            self.context = context
            self.logger = context.logger.getChild("Weather.Local") if getattr(context, "logger", None) else None
        return self

    def isAvailable(self) -> bool:
        return bool(self.sensorManager or getattr(self.context, "homeAutomation", None) or getattr(self.context, "bridgeClient", None))

    def shutdown(self):
        return None

    def getCurrentWeather(self, location: str = "") -> WeatherData | None:
        sensors = self._readSensors(location)
        if not sensors:
            return None

        readings = {sensor.sensorType.lower(): sensor for sensor in sensors if sensor.online}
        temperature = self._primaryValue(readings, ("temperature", "temp"))
        humidity = self._primaryValue(readings, ("humidity",))
        pressure = self._primaryValue(readings, ("pressure",))
        windSpeed = self._primaryValue(readings, ("wind", "windspeed"))
        feelsLike = temperature
        data = WeatherData(
            location=self._resolveLocation(location, sensors),
            temperature=temperature,
            humidity=humidity,
            pressure=pressure,
            windSpeed=windSpeed,
            windDirection="",
            condition="sensor",
            visibility=None,
            uvIndex=None,
            feelsLike=feelsLike,
            source=WeatherSource.LOCAL_SENSOR,
            timestamp=self._now(),
            metadata={"sensorCount": len(sensors), "sensors": [sensor.asDict() for sensor in sensors]},
        )
        return data

    def getHourlyForecast(self, location: str, hours: int = 24):
        return None

    def getWeeklyForecast(self, location: str, days: int = 7):
        return None

    def getAlerts(self, location: str):
        return []

    def getIndoorTemperature(self, location: str = "") -> float | None:
        data = self.getCurrentWeather(location)
        return None if data is None else data.temperature

    def _readSensors(self, location: str = ""):
        manager = self.sensorManager or getattr(self.context, "weatherSensorManager", None)
        if manager is not None:
            return list(manager.getSensors(location=location))
        if self.context is None:
            return []
        homeAutomation = getattr(self.context, "homeAutomation", None) or getattr(self.context, "bridgeClient", None) or getattr(self.context, "auraBridgeClient", None)
        if homeAutomation is None:
            return []
        state = getattr(homeAutomation, "getBridgeState", None)
        if callable(state):
            bridgeState = state()
        else:
            bridgeState = getattr(homeAutomation, "state", None)
        if bridgeState is None:
            return []
        return list(getattr(self.sensorManager or WeatherSensorShim(bridgeState), "getSensors", lambda **kwargs: [])(location=location))

    @staticmethod
    def _resolveLocation(location: str, sensors) -> str:
        if location:
            return str(location)
        for sensor in sensors:
            if sensor.location:
                return str(sensor.location)
        return "Local"

    @staticmethod
    def _primaryValue(readings: dict[str, Any], aliases: tuple[str, ...]):
        for alias in aliases:
            sensor = readings.get(alias)
            if sensor is not None and sensor.value is not None:
                try:
                    return float(sensor.value)
                except Exception:
                    continue
        return None

    @staticmethod
    def _now() -> str:
        from datetime import datetime

        return datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")


class WeatherSensorShim:
    """Fallback sensor parser when no dedicated sensor manager exists."""

    def __init__(self, bridgeState):
        self.bridgeState = bridgeState

    def getSensors(self, location: str = ""):
        from modules.weather.weatherSensorManager import WeatherSensorManager

        return WeatherSensorManager(None, bridgeState=self.bridgeState).getSensors(location=location)
