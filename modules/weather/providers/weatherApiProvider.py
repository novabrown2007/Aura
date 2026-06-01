"""External weather API provider abstraction for Aura."""

from __future__ import annotations

import json
from datetime import datetime
from typing import Any
from urllib import error, parse, request

from modules.weather.models import WeatherAlert, WeatherData, WeatherForecast, WeatherSource


class WeatherApiProvider:
    """Fetch weather data from a generic JSON weather API."""

    def __init__(self, context=None, config: dict[str, Any] | None = None):
        self.context = context
        self.config = dict(config or {})
        self.logger = context.logger.getChild("Weather.Api") if context and getattr(context, "logger", None) else None

    def initialize(self, context=None):
        if context is not None:
            self.context = context
            self.logger = context.logger.getChild("Weather.Api") if getattr(context, "logger", None) else None
        return self

    def isAvailable(self) -> bool:
        return bool(self._baseUrl())

    def shutdown(self):
        return None

    def embedText(self, text: str):  # pragma: no cover - compatibility with future provider style
        raise NotImplementedError

    def getCurrentWeather(self, location: str) -> WeatherData | None:
        payload = self._request("current", location=location)
        if payload is None:
            return None
        return self._parseCurrent(payload, location)

    def getHourlyForecast(self, location: str, hours: int = 24) -> WeatherForecast | None:
        payload = self._request("hourly", location=location, hours=int(hours))
        if payload is None:
            return None
        return self._parseForecast(payload, location)

    def getWeeklyForecast(self, location: str, days: int = 7) -> WeatherForecast | None:
        payload = self._request("weekly", location=location, days=int(days))
        if payload is None:
            return None
        return self._parseForecast(payload, location)

    def getAlerts(self, location: str) -> list[WeatherAlert]:
        payload = self._request("alerts", location=location)
        if payload is None:
            return []
        alerts = payload.get("alerts") if isinstance(payload, dict) else payload
        if not isinstance(alerts, list):
            return []
        return [WeatherAlert.fromDict(item) for item in alerts if isinstance(item, dict)]

    def _request(self, kind: str, **params) -> dict[str, Any] | None:
        baseUrl = self._baseUrl()
        if not baseUrl:
            return None

        path = self._endpointPath(kind)
        query = self._endpointQuery(kind, params)
        url = f"{baseUrl.rstrip('/')}/{path.lstrip('/')}"
        if query:
            url = f"{url}?{parse.urlencode(query)}"

        headers = {"Accept": "application/json"}
        apiKey = self._apiKey()
        if apiKey:
            headers["Authorization"] = f"Bearer {apiKey}"

        try:
            with request.urlopen(request.Request(url, headers=headers), timeout=self._timeout()) as response:
                raw = response.read().decode("utf-8")
        except (error.URLError, OSError) as exception:
            if self.logger:
                self.logger.warning(f"Weather API unavailable for {kind}: {exception}")
            return None

        try:
            parsed = json.loads(raw or "{}")
        except json.JSONDecodeError:
            return None
        return parsed if isinstance(parsed, dict) else {"data": parsed}

    def _parseCurrent(self, payload: dict[str, Any], location: str) -> WeatherData:
        current = payload.get("current") if isinstance(payload.get("current"), dict) else payload
        now = self._now()
        return WeatherData(
            location=str(payload.get("location") or current.get("location") or location or ""),
            temperature=self._number(current.get("temperature", current.get("temp", current.get("temperatureC")))),
            humidity=self._number(current.get("humidity", current.get("humidityPercent"))),
            pressure=self._number(current.get("pressure")),
            windSpeed=self._number(current.get("windSpeed", current.get("wind_speed"))),
            windDirection=str(current.get("windDirection") or current.get("wind_direction") or ""),
            condition=str(current.get("condition") or current.get("weather") or current.get("description") or ""),
            visibility=self._number(current.get("visibility")),
            uvIndex=self._number(current.get("uvIndex", current.get("uv_index"))),
            feelsLike=self._number(current.get("feelsLike", current.get("feels_like"))),
            source=WeatherSource.WEATHER_API,
            timestamp=str(current.get("timestamp") or payload.get("timestamp") or now),
            metadata=dict(payload.get("metadata") or {}),
        )

    def _parseForecast(self, payload: dict[str, Any], location: str) -> WeatherForecast:
        forecast = payload.get("forecast") if isinstance(payload.get("forecast"), dict) else payload
        hourly = forecast.get("hourly") if isinstance(forecast.get("hourly"), list) else []
        daily = forecast.get("daily") if isinstance(forecast.get("daily"), list) else []
        alerts = forecast.get("alerts") if isinstance(forecast.get("alerts"), list) else []
        if not hourly and isinstance(forecast.get("items"), list):
            hourly = list(forecast.get("items"))
        return WeatherForecast(
            location=str(payload.get("location") or forecast.get("location") or location or ""),
            source=WeatherSource.WEATHER_API,
            timestamp=str(forecast.get("timestamp") or payload.get("timestamp") or self._now()),
            hourly=[dict(item) for item in hourly if isinstance(item, dict)],
            daily=[dict(item) for item in daily if isinstance(item, dict)],
            alerts=[dict(item) for item in alerts if isinstance(item, dict)],
            metadata=dict(payload.get("metadata") or {}),
        )

    def _baseUrl(self) -> str:
        return str(self.config.get("baseUrl") or self.config.get("base_url") or "").strip()

    def _apiKey(self) -> str:
        return str(self.config.get("apiKey") or self.config.get("api_key") or "").strip()

    def _timeout(self) -> float:
        return float(self.config.get("timeoutSeconds") or self.config.get("timeout_seconds") or 10.0)

    def _endpointPath(self, kind: str) -> str:
        mapping = {
            "current": self.config.get("currentPath") or "/current",
            "hourly": self.config.get("hourlyPath") or "/forecast/hourly",
            "weekly": self.config.get("weeklyPath") or "/forecast/weekly",
            "alerts": self.config.get("alertsPath") or "/alerts",
        }
        return str(mapping.get(kind, "/current"))

    @staticmethod
    def _endpointQuery(kind: str, params: dict[str, Any]) -> dict[str, Any]:
        query = {"location": params.get("location") or ""}
        if kind == "hourly":
            query["hours"] = int(params.get("hours") or 24)
        if kind == "weekly":
            query["days"] = int(params.get("days") or 7)
        return {key: value for key, value in query.items() if value not in ("", None)}

    @staticmethod
    def _number(value):
        if value in (None, ""):
            return None
        try:
            return float(value)
        except Exception:
            return None

    @staticmethod
    def _now() -> str:
        return datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
