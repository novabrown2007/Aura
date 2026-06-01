"""Weather module event names."""


class WeatherEvents:
    """Weather event constants."""

    REQUESTED = "weather.requested"
    CURRENT_UPDATED = "weather.updated"
    FORECAST_UPDATED = "weather.forecast.updated"
    ALERT_RECEIVED = "weather.alert.received"
    THRESHOLD_TRIGGERED = "weather.threshold.triggered"
    SENSOR_UPDATED = "bridge.sensor.updated"
