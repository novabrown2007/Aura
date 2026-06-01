"""Bridge sensor discovery and normalization for Aura weather."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from modules.weather.models import EnvironmentalSensor


class WeatherSensorManager:
    """Normalize environmental sensor data from the Home Automation bridge."""

    def __init__(self, context=None, bridgeState=None):
        self.context = context
        self.bridgeState = bridgeState
        self.logger = context.logger.getChild("Weather.Sensors") if context and getattr(context, "logger", None) else None

    def initialize(self, context=None):
        if context is not None:
            self.context = context
            self.logger = context.logger.getChild("Weather.Sensors") if getattr(context, "logger", None) else None
        return self

    def getSensors(self, location: str = "") -> list[EnvironmentalSensor]:
        """Return normalized environmental sensors from bridge state."""

        bridgeState = self._bridgeState()
        if bridgeState is None:
            return []

        devices = list(getattr(bridgeState, "devices", []) or [])
        sensors: list[EnvironmentalSensor] = []
        for device in devices:
            payload = self._devicePayload(device)
            if not self._isEnvironmentalSensor(payload):
                continue
            sensor = self._parseSensor(payload)
            if location and sensor.location and str(sensor.location).strip().lower() != str(location).strip().lower():
                continue
            sensors.append(sensor)
        return sensors

    def getCurrentReadings(self, location: str = "") -> dict[str, Any]:
        sensors = self.getSensors(location=location)
        readings = {"sensors": [sensor.asDict() for sensor in sensors]}
        for sensor in sensors:
            key = sensor.sensorType.lower()
            if key and sensor.value is not None and key not in readings:
                readings[key] = sensor.value
        return readings

    def getIndoorTemperature(self, location: str = "") -> float | None:
        for sensor in self.getSensors(location=location):
            if sensor.sensorType.lower() in {"temperature", "temp"} and sensor.value is not None:
                try:
                    return float(sensor.value)
                except Exception:
                    continue
        return None

    def snapshot(self) -> dict[str, Any]:
        sensors = [sensor.asDict() for sensor in self.getSensors()]
        return {"sensors": sensors, "count": len(sensors)}

    def _bridgeState(self):
        if self.bridgeState is not None:
            return self.bridgeState
        context = self.context
        if context is None:
            return None
        bridge = getattr(context, "homeAutomation", None) or getattr(context, "bridgeClient", None) or getattr(context, "auraBridgeClient", None)
        if bridge is None:
            return None
        if callable(getattr(bridge, "getBridgeState", None)):
            try:
                return bridge.getBridgeState()
            except Exception:
                return getattr(bridge, "state", None)
        return getattr(bridge, "state", None)

    @staticmethod
    def _devicePayload(device) -> dict[str, Any]:
        if isinstance(device, dict):
            return dict(device)
        if hasattr(device, "asDict"):
            return dict(device.asDict())
        if hasattr(device, "__dict__"):
            return dict(vars(device))
        return {"name": str(device)}

    @staticmethod
    def _isEnvironmentalSensor(payload: dict[str, Any]) -> bool:
        category = str(payload.get("category") or payload.get("type") or payload.get("sensorType") or "").lower()
        name = str(payload.get("name") or "").lower()
        sensor_type = str(payload.get("sensorType") or payload.get("sensor_type") or "").lower()
        keywords = ("sensor", "temperature", "humidity", "pressure", "environment", "weather")
        return any(term in category or term in name or term in sensor_type for term in keywords)

    def _parseSensor(self, payload: dict[str, Any]) -> EnvironmentalSensor:
        sensor_type = str(payload.get("sensorType") or payload.get("sensor_type") or payload.get("category") or payload.get("type") or "sensor")
        value = self._sensorValue(payload)
        unit = str(payload.get("unit") or payload.get("measurementUnit") or payload.get("measurement_unit") or "")
        location = str(payload.get("location") or payload.get("room") or payload.get("area") or "")
        metadata = dict(payload.get("metadata") or {})
        metadata.setdefault("raw", dict(payload))
        return EnvironmentalSensor(
            sensorId=str(payload.get("sensorId") or payload.get("sensor_id") or payload.get("device_id") or payload.get("id") or sensor_type),
            name=str(payload.get("name") or payload.get("label") or sensor_type.title()),
            sensorType=sensor_type,
            value=value,
            unit=unit,
            location=location,
            online=bool(payload.get("online", True)),
            timestamp=str(payload.get("timestamp") or payload.get("updatedAt") or payload.get("updated_at") or self._now()),
            metadata=metadata,
        )

    @staticmethod
    def _sensorValue(payload: dict[str, Any]):
        for key in ("temperature", "temperature_c", "temperatureC", "humidity", "humidity_percent", "pressure", "value", "reading"):
            if key in payload and payload[key] not in (None, ""):
                try:
                    return float(payload[key])
                except Exception:
                    return payload[key]
        return None

    @staticmethod
    def _now() -> str:
        return datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
