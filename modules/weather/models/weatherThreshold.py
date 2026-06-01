"""Weather threshold rules for Aura."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any


@dataclass(slots=True)
class WeatherThreshold:
    """A user-configured weather threshold rule."""

    thresholdId: str = ""
    location: str = ""
    metric: str = "temperature"
    operator: str = "<"
    value: float = 0.0
    enabled: bool = True
    cooldownSeconds: int = 1800
    lastTriggeredAt: str = ""
    notificationPriority: str = "NORMAL"
    title: str = ""
    message: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def asDict(self) -> dict[str, Any]:
        return {
            "thresholdId": self.thresholdId,
            "location": self.location,
            "metric": self.metric,
            "operator": self.operator,
            "value": self.value,
            "enabled": bool(self.enabled),
            "cooldownSeconds": int(self.cooldownSeconds),
            "lastTriggeredAt": self.lastTriggeredAt,
            "notificationPriority": self.notificationPriority,
            "title": self.title,
            "message": self.message,
            "metadata": dict(self.metadata),
        }

    @classmethod
    def fromDict(cls, values: dict[str, Any] | None):
        values = dict(values or {})
        return cls(
            thresholdId=str(values.get("thresholdId") or values.get("id") or ""),
            location=str(values.get("location") or ""),
            metric=str(values.get("metric") or "temperature"),
            operator=str(values.get("operator") or "<"),
            value=float(values.get("value", 0.0) or 0.0),
            enabled=bool(values.get("enabled", True)),
            cooldownSeconds=int(values.get("cooldownSeconds", 1800) or 1800),
            lastTriggeredAt=str(values.get("lastTriggeredAt") or ""),
            notificationPriority=str(values.get("notificationPriority") or "NORMAL").upper(),
            title=str(values.get("title") or ""),
            message=str(values.get("message") or ""),
            metadata=dict(values.get("metadata") or {}),
        )

    def isCoolingDown(self, timestampText: str) -> bool:
        """Return whether this rule is still in cooldown."""

        if not self.lastTriggeredAt:
            return False
        try:
            lastTriggered = datetime.fromisoformat(self.lastTriggeredAt.replace("Z", "+00:00"))
            current = datetime.fromisoformat(timestampText.replace("Z", "+00:00"))
        except Exception:
            return False
        return current - lastTriggered < timedelta(seconds=max(0, int(self.cooldownSeconds)))

    def evaluate(self, weatherData) -> bool:
        """Return whether the rule should trigger for one weather payload."""

        if not self.enabled or weatherData is None:
            return False
        value = self._metricValue(weatherData)
        if value is None:
            return False
        try:
            target = float(self.value)
        except Exception:
            return False
        operator = str(self.operator or "<").strip()
        if operator == ">":
            return value > target
        if operator == ">=":
            return value >= target
        if operator == "<":
            return value < target
        if operator == "<=":
            return value <= target
        if operator == "==":
            return value == target
        if operator == "!=":
            return value != target
        return False

    def markTriggered(self, timestampText: str):
        self.lastTriggeredAt = str(timestampText or "")

    @staticmethod
    def _metricValue(weatherData) -> float | None:
        payload = weatherData.asDict() if hasattr(weatherData, "asDict") else dict(weatherData or {})
        metric = str(payload.get("metric") or "").lower()
        mapping = {
            "temperature": payload.get("temperature"),
            "temperaturec": payload.get("temperature"),
            "humidity": payload.get("humidity"),
            "humiditypercent": payload.get("humidity"),
            "pressure": payload.get("pressure"),
            "windspeed": payload.get("windSpeed"),
            "visibility": payload.get("visibility"),
            "uvindex": payload.get("uvIndex"),
            "feelslike": payload.get("feelsLike"),
        }
        if metric in mapping and mapping[metric] is not None:
            try:
                return float(mapping[metric])
            except Exception:
                return None
        key = str(payload.get("metric") or "temperature").lower()
        aliases = {
            "temperature": payload.get("temperature"),
            "humidity": payload.get("humidity"),
            "pressure": payload.get("pressure"),
            "wind": payload.get("windSpeed"),
            "windspeed": payload.get("windSpeed"),
            "visibility": payload.get("visibility"),
            "uv": payload.get("uvIndex"),
            "uvindex": payload.get("uvIndex"),
            "feelslike": payload.get("feelsLike"),
        }
        value = aliases.get(key)
        if value is None:
            return None
        try:
            return float(value)
        except Exception:
            return None
