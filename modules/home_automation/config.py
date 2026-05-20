"""Configuration models for Aura home automation integrations."""

from __future__ import annotations

import os
from dataclasses import dataclass, field


@dataclass(slots=True)
class BridgeConfig:
    """Connection details for the home automation bridge service."""

    host: str = field(default_factory=lambda: os.getenv("HOME_AUTOMATION_BRIDGE_HOST", "127.0.0.1"))
    port: int = field(default_factory=lambda: int(os.getenv("HOME_AUTOMATION_BRIDGE_PORT", "8080")))
    use_ssl: bool = field(default_factory=lambda: os.getenv("HOME_AUTOMATION_BRIDGE_SSL", "0") == "1")
    api_token: str = field(default_factory=lambda: os.getenv("HOME_AUTOMATION_BRIDGE_TOKEN", ""))
    timeout_seconds: float = field(default_factory=lambda: float(os.getenv("HOME_AUTOMATION_BRIDGE_TIMEOUT", "3.0")))

    @property
    def base_url(self) -> str:
        """Return the bridge service base URL."""

        scheme = "https" if self.use_ssl else "http"
        return f"{scheme}://{self.host}:{self.port}"


@dataclass(slots=True)
class ServiceControlConfig:
    """Connection details for remotely starting automation services."""

    host: str = field(
        default_factory=lambda: os.getenv(
            "HOME_AUTOMATION_CONTROL_HOST",
            os.getenv("HOME_AUTOMATION_BRIDGE_HOST", "127.0.0.1"),
        )
    )
    port: int = field(default_factory=lambda: int(os.getenv("HOME_AUTOMATION_CONTROL_PORT", "8091")))
    use_ssl: bool = field(default_factory=lambda: os.getenv("HOME_AUTOMATION_CONTROL_SSL", "0") == "1")
    api_token: str = field(default_factory=lambda: os.getenv("HOME_AUTOMATION_CONTROL_TOKEN", ""))
    timeout_seconds: float = field(default_factory=lambda: float(os.getenv("HOME_AUTOMATION_CONTROL_TIMEOUT", "5.0")))
    start_bridge_path: str = field(default_factory=lambda: os.getenv("HOME_AUTOMATION_START_BRIDGE_PATH", "/control/startbridge"))
    start_hub_path: str = field(default_factory=lambda: os.getenv("HOME_AUTOMATION_START_HUB_PATH", "/control/starthub"))

    @property
    def base_url(self) -> str:
        """Return the service-control base URL."""

        scheme = "https" if self.use_ssl else "http"
        return f"{scheme}://{self.host}:{self.port}"


@dataclass(slots=True)
class HomeAutomationConfig:
    """Configuration bundle for the home automation module."""

    refresh_interval_seconds: float = field(default_factory=lambda: float(os.getenv("HOME_AUTOMATION_REFRESH_SECONDS", "5.0")))
    bridge: BridgeConfig = field(default_factory=BridgeConfig)
    control: ServiceControlConfig = field(default_factory=ServiceControlConfig)


def buildHomeAutomationConfig(context) -> HomeAutomationConfig:
    """Build module configuration from Aura config with environment fallbacks."""

    aura_config = getattr(context, "config", None)
    if aura_config is None:
        return HomeAutomationConfig()

    def get(key, default):
        return aura_config.get(f"home_automation.{key}", default)

    def as_bool(value) -> bool:
        if isinstance(value, bool):
            return value
        return str(value).strip().lower() in {"1", "true", "yes", "on"}

    bridge = BridgeConfig(
        host=str(get("bridge.host", BridgeConfig().host)),
        port=int(get("bridge.port", BridgeConfig().port)),
        use_ssl=as_bool(get("bridge.use_ssl", BridgeConfig().use_ssl)),
        api_token=str(get("bridge.api_token", BridgeConfig().api_token)),
        timeout_seconds=float(get("bridge.timeout_seconds", BridgeConfig().timeout_seconds)),
    )
    control = ServiceControlConfig(
        host=str(get("control.host", ServiceControlConfig().host)),
        port=int(get("control.port", ServiceControlConfig().port)),
        use_ssl=as_bool(get("control.use_ssl", ServiceControlConfig().use_ssl)),
        api_token=str(get("control.api_token", ServiceControlConfig().api_token)),
        timeout_seconds=float(get("control.timeout_seconds", ServiceControlConfig().timeout_seconds)),
        start_bridge_path=str(get("control.start_bridge_path", ServiceControlConfig().start_bridge_path)),
        start_hub_path=str(get("control.start_hub_path", ServiceControlConfig().start_hub_path)),
    )
    return HomeAutomationConfig(
        refresh_interval_seconds=float(get("refresh_interval_seconds", HomeAutomationConfig().refresh_interval_seconds)),
        bridge=bridge,
        control=control,
    )
