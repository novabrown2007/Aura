"""Weather page for the Aura middle content area."""

from __future__ import annotations

from .base import Page
from ..drawing import shadow_round_rect


class WeatherPage(Page):
    """Render the full weather module snapshot as a scrollable dashboard."""

    name = "weather"

    def __init__(self, context=None):
        self.context = context
        self._weather = None
        self._weather_loaded = False
        self._scroll_offset = 0
        self._max_scroll = 0
        self._sections_bounds = (0, 0, 0, 0)
        self._section_blocks: list[tuple[str, dict[str, object]]] = []

    def set_context(self, context=None):
        self.context = context
        self._weather = None
        self._weather_loaded = False

    def render(self, canvas, width: int, height: int, theme, sidebar_visible: bool):
        self._weather = self._resolve_weather()
        bounds = self.content_bounds(width, height, sidebar_visible)
        left = bounds["left"] + 18
        right = bounds["right"] - 18
        top = bounds["top"] + 12
        bottom = bounds["bottom"] - 18

        canvas.create_text(left, top, anchor="nw", text="Weather", fill=theme.text, font=("Segoe UI", 18, "bold"))
        canvas.create_text(left, top + 28, anchor="nw", text="Current conditions, forecast, sensors, alerts, and thresholds", fill=theme.placeholder, font=("Segoe UI", 10))

        panel_top = top + 58
        self._draw_panel(canvas, theme, left, panel_top, right, bottom)

    def content_bounds(self, width: int, height: int, sidebar_visible: bool) -> dict[str, int]:
        left = 36
        right = width - 36
        top = 102
        bottom = height - 148
        if sidebar_visible:
            left = 24 + 210 + 28
        return {"left": left, "right": right, "top": top, "bottom": bottom}

    def handle_scroll(self, delta: int, x: int, y: int, width: int, height: int, sidebar_visible: bool) -> bool:
        if not self._point_in_bounds(x, y, self._sections_bounds):
            return False
        step = 42
        if delta > 0:
            self._scroll_offset = max(0, self._scroll_offset - step)
        else:
            self._scroll_offset = min(self._max_scroll, self._scroll_offset + step)
        return True

    def _draw_panel(self, canvas, theme, left: int, top: int, right: int, bottom: int):
        shadow_round_rect(canvas, left, top, right, bottom, 18, fill=theme.tertiary_background, outline=theme.border, width=2)
        self._sections_bounds = (left, top, right, bottom)

        if not self._weather:
            canvas.create_text(left + 20, top + 20, anchor="nw", text="No weather data is available yet.", fill=theme.placeholder, font=("Segoe UI", 11))
            return

        sections = self._build_sections(self._weather)
        cursor_y = top + 18 - self._scroll_offset
        content_height = 0
        self._section_blocks = []

        for title, payload in sections:
            if cursor_y > bottom:
                break
            if cursor_y + 24 >= top:
                canvas.create_text(left + 20, cursor_y, anchor="nw", text=title, fill=theme.text, font=("Segoe UI", 12, "bold"))
            cursor_y += 28
            block_height = self._draw_payload_block(canvas, theme, left + 20, cursor_y, right - 20, payload, bottom)
            self._section_blocks.append((title, payload))
            cursor_y += block_height + 18
            content_height = cursor_y - top

        viewport_height = max(1, bottom - top)
        self._max_scroll = max(0, content_height - viewport_height)
        self._scroll_offset = max(0, min(self._scroll_offset, self._max_scroll))
        self._draw_scrollbar(canvas, theme, right - 2, top, bottom, self._scroll_offset, self._max_scroll)

    def _draw_payload_block(self, canvas, theme, left: int, top: int, right: int, payload, bottom: int) -> int:
        if isinstance(payload, list):
            items = [self._to_display_line(item) for item in payload]
            text = "\n".join(items) if items else "[]"
        elif isinstance(payload, dict):
            lines = []
            for key, value in payload.items():
                lines.append(f"{key}: {self._format_value(value)}")
            text = "\n".join(lines) if lines else "{}"
        else:
            text = self._format_value(payload)

        lines = text.splitlines() or [""]
        height = max(52, 20 + len(lines) * 18)
        shadow_round_rect(canvas, left, top, right, top + height, 14, fill=theme.panel, outline=theme.border, width=1)
        canvas.create_text(left + 16, top + 12, anchor="nw", text=text, fill=theme.text, font=("Segoe UI", 10), width=max(180, right - left - 32), justify="left")
        return height

    def _build_sections(self, weather: dict[str, object]):
        sections = []
        snapshot = dict(weather.get("snapshot") or {})
        dashboard = dict(weather.get("dashboard") or {})
        current_view = dict(weather.get("currentView") or {})
        forecast_view = dict(weather.get("forecastView") or {})
        sections.append(("Module Snapshot", {
            "available": snapshot.get("available"),
            "enabled": snapshot.get("enabled"),
            "source": snapshot.get("source"),
        }))
        sections.append(("Current Weather", current_view or snapshot.get("currentWeather") or dashboard.get("current") or {}))
        sections.append(("Forecast", forecast_view or dashboard.get("forecast") or snapshot.get("forecast") or {}))
        sections.append(("Alerts", weather.get("alerts") or dashboard.get("alerts") or snapshot.get("alerts") or []))
        sections.append(("Thresholds", weather.get("thresholds") or dashboard.get("thresholds") or snapshot.get("thresholds") or []))
        sections.append(("Locations", weather.get("locations") or dashboard.get("locations") or snapshot.get("locations") or []))
        sections.append(("Sensors", weather.get("sensors") or dashboard.get("sensors") or snapshot.get("sensors") or {}))
        sections.append(("Indoor Temperature", weather.get("indoorTemperature") or {}))
        sections.append(("Hourly Forecast", weather.get("hourlyForecast") or {}))
        sections.append(("Weekly Forecast", weather.get("weeklyForecast") or {}))
        sections.append(("Monitor", snapshot.get("monitor") or {}))
        sections.append(("Alert State", snapshot.get("alertState") or {}))
        sections.append(("Cache", snapshot.get("cache") or {}))
        return sections

    def _resolve_weather(self):
        context = self.context
        if context is None:
            return {}
        weather = getattr(context, "weather", None)
        if weather is None:
            module_manager = getattr(context, "moduleManager", None)
            if module_manager is not None and hasattr(module_manager, "getModule"):
                try:
                    weather = module_manager.getModule("weather")
                except Exception:
                    weather = None
        if weather is None:
            return {}
        try:
            snapshot = dict(weather.snapshot() or {})
        except Exception:
            snapshot = {}

        result = {"snapshot": snapshot}
        if self._weather_loaded and snapshot.get("currentWeather"):
            result["currentView"] = snapshot.get("currentWeather") or {}
            result["dashboard"] = snapshot.get("dashboard") or {}
            return result

        try:
            if hasattr(weather, "getDashboard"):
                result["dashboard"] = dict(weather.getDashboard() or {})
            if hasattr(weather, "getWeatherViewModel"):
                result["currentView"] = dict(weather.getWeatherViewModel() or {})
            if hasattr(weather, "getForecastViewModel"):
                result["forecastView"] = dict(weather.getForecastViewModel() or {})
            if hasattr(weather, "getCurrentWeather"):
                result["currentWeather"] = dict(weather.getCurrentWeather() or {})
            if hasattr(weather, "getHourlyForecast"):
                result["hourlyForecast"] = dict(weather.getHourlyForecast() or {})
            if hasattr(weather, "getWeeklyForecast"):
                result["weeklyForecast"] = dict(weather.getWeeklyForecast() or {})
            if hasattr(weather, "getIndoorTemperature"):
                result["indoorTemperature"] = dict(weather.getIndoorTemperature() or {})
            if hasattr(weather, "getAlerts"):
                result["alerts"] = list(weather.getAlerts() or [])
            if hasattr(weather, "listLocations"):
                result["locations"] = list(weather.listLocations() or [])
            if hasattr(weather, "listThresholds"):
                result["thresholds"] = list(weather.listThresholds() or [])
        except Exception:
            pass

        self._weather_loaded = True
        return result if any(result.get(key) for key in result if key != "snapshot") else {"snapshot": snapshot}

    def _draw_scrollbar(self, canvas, theme, track_x: int, top: int, bottom: int, scroll_offset: int, max_scroll: int):
        track_left = track_x - 8
        track_right = track_x - 4
        canvas.create_rectangle(track_left, top, track_right, bottom, fill=theme.shadow, outline=theme.shadow, width=0)
        if max_scroll <= 0:
            return
        track_height = max(1, bottom - top)
        thumb_height = max(42, int((track_height * track_height) / max(1, track_height + max_scroll)))
        thumb_height = min(track_height, thumb_height)
        thumb_range = max(1, track_height - thumb_height)
        thumb_top = top + int((scroll_offset / max_scroll) * thumb_range)
        canvas.create_rectangle(track_left, thumb_top, track_right, thumb_top + thumb_height, fill=theme.soft_glow, outline=theme.soft_glow, width=0)

    @staticmethod
    def _format_value(value):
        if isinstance(value, dict):
            return ", ".join(f"{key}={WeatherPage._format_value(inner)}" for key, inner in value.items())
        if isinstance(value, list):
            if not value:
                return "[]"
            return "[" + ", ".join(WeatherPage._format_value(item) for item in value[:6]) + (", ..." if len(value) > 6 else "") + "]"
        if value is None:
            return "n/a"
        return str(value)

    @staticmethod
    def _to_display_line(item):
        if isinstance(item, dict):
            if "name" in item and "location" in item:
                return f"{item.get('name')} ({item.get('location')})"
            if "name" in item:
                return str(item.get("name"))
            if "title" in item:
                return str(item.get("title"))
            return ", ".join(f"{k}={v}" for k, v in item.items())
        return str(item)

    @staticmethod
    def _point_in_bounds(x: int, y: int, bounds: tuple[int, int, int, int]) -> bool:
        x1, y1, x2, y2 = bounds
        return x1 <= x <= x2 and y1 <= y <= y2
