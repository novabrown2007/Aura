"""Tests for the Aura weather page."""

from __future__ import annotations

from types import SimpleNamespace
import unittest

from interface.pages.weather_page import WeatherPage


class DummyCanvas:
    def __init__(self):
        self._next_id = 1

    def _alloc(self):
        item_id = self._next_id
        self._next_id += 1
        return item_id

    def create_text(self, *args, **kwargs):
        return self._alloc()

    def create_line(self, *args, **kwargs):
        return self._alloc()

    def create_rectangle(self, *args, **kwargs):
        return self._alloc()

    def create_polygon(self, *args, **kwargs):
        return self._alloc()

    def create_oval(self, *args, **kwargs):
        return self._alloc()

    def create_image(self, *args, **kwargs):
        return self._alloc()


class FakeWeather:
    def snapshot(self):
        return {
            "available": True,
            "enabled": True,
            "source": {"provider": "SIMULATED"},
            "currentWeather": {"location": "Toronto", "temperature": 21, "condition": "clear"},
            "forecast": {"daily": [{"day": "Mon", "condition": "clear"}]},
            "alerts": [{"title": "Heat warning"}],
            "thresholds": [{"metric": "temperature", "operator": ">", "value": 30}],
            "locations": [{"name": "Home", "locationId": "home"}],
            "sensors": {"count": 1, "sensors": [{"name": "Living Room"}]},
            "monitor": {"enabled": True},
            "alertState": {"active": False},
            "cache": {"enabled": True},
        }


class WeatherPageTests(unittest.TestCase):
    def test_renders_weather_snapshot(self):
        page = WeatherPage(context=SimpleNamespace(weather=FakeWeather()))
        canvas = DummyCanvas()
        theme = SimpleNamespace(
            text="#fff",
            placeholder="#999",
            tertiary_background="#222",
            border="#444",
            shadow="#111",
            secondary_accent="#0af",
            panel="#333",
            background="#000",
            soft_glow="#0af",
        )

        page.render(canvas, 1200, 800, theme, sidebar_visible=False)

        self.assertEqual(page._weather["currentWeather"]["location"], "Toronto")
        self.assertGreaterEqual(page._max_scroll, 0)


if __name__ == "__main__":
    unittest.main()
