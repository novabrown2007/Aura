"""Configuration models for Aura home automation integrations."""

from __future__ import annotations

import os
from dataclasses import dataclass, field


def _env_value(name: str, default):
    value = os.getenv(name)
    if value is None or str(value).strip() == "":
        return default
    return value


def _env_int(name: str, default: int) -> int:
    return int(_env_value(name, default))


def _env_float(name: str, default: float) -> float:
    return float(_env_value(name, default))


def _env_bool(name: str, default: bool = False) -> bool:
    return str(_env_value(name, "1" if default else "0")).strip().lower() in {"1", "true", "yes", "on"}


def _config_value(config, *keys, default=None):
    """Return the first non-empty config value found for the provided paths."""

    if config is None:
        return default

    for key in keys:
        value = config.get(key, None)
        if value is None:
            continue
        if isinstance(value, str) and value.strip() == "":
            continue
        return value
    return default


@dataclass(slots=True)
class BridgeConfig:
    """Connection details for the home automation bridge service."""

    host: str = field(default_factory=lambda: str(_env_value("HOME_AUTOMATION_BRIDGE_HOST", "127.0.0.1")))
    port: int = field(default_factory=lambda: _env_int("HOME_AUTOMATION_BRIDGE_PORT", 8080))
    use_ssl: bool = field(default_factory=lambda: _env_bool("HOME_AUTOMATION_BRIDGE_SSL", False))
    timeout_seconds: float = field(default_factory=lambda: _env_float("HOME_AUTOMATION_BRIDGE_TIMEOUT", 3.0))
    protocol_path: str = "/protocol/aura"
    inbox_path: str = "/protocol/inbox"
    subscriptions_path: str = "/protocol/subscriptions"
    heartbeat_path: str = "/protocol/heartbeat"
    session_id: str = "auto"
    interface_name: str = "desktop"
    heartbeat_seconds: float = 30.0

    @property
    def base_url(self) -> str:
        """Return the bridge service base URL."""

        scheme = "https" if self.use_ssl else "http"
        return f"{scheme}://{self.host}:{self.port}"


@dataclass(slots=True)
class HomeAutomationConfig:
    """Configuration bundle for the home automation module."""

    refresh_interval_seconds: float = field(default_factory=lambda: _env_float("HOME_AUTOMATION_REFRESH_SECONDS", 5.0))
    bridge: BridgeConfig = field(default_factory=BridgeConfig)


def buildHomeAutomationConfig(context) -> HomeAutomationConfig:
    """Build module configuration from Aura config, config file, and env fallbacks."""

    aura_config = getattr(context, "config", None)
    if aura_config is None:
        return HomeAutomationConfig()

    def as_bool(value, default=False) -> bool:
        if value is None:
            return default
        if isinstance(value, bool):
            return value
        return str(value).strip().lower() in {"1", "true", "yes", "on"}

    bridge_defaults = BridgeConfig()
    config_defaults = HomeAutomationConfig()

    bridge = BridgeConfig(
        host=str(_config_value(aura_config, "homeAutomationBridge.host", "home_automation.bridge.host", default=bridge_defaults.host)),
        port=int(_config_value(aura_config, "homeAutomationBridge.port", "home_automation.bridge.port", default=bridge_defaults.port)),
        use_ssl=as_bool(_config_value(
            aura_config,
            "homeAutomationBridge.ssl",
            "homeAutomationBridge.use_ssl",
            "home_automation.bridge.use_ssl",
            default=bridge_defaults.use_ssl,
        )),
        timeout_seconds=float(_config_value(
            aura_config,
            "homeAutomationBridge.timeout",
            "homeAutomationBridge.timeoutSeconds",
            "homeAutomationBridge.timeout_seconds",
            "home_automation.bridge.timeout_seconds",
            default=bridge_defaults.timeout_seconds,
        )),
        protocol_path=str(_config_value(
            aura_config,
            "homeAutomationBridge.protocolPath",
            "homeAutomationBridge.protocol_path",
            "home_automation.bridge.protocol_path",
            default=bridge_defaults.protocol_path,
        )),
        inbox_path=str(_config_value(
            aura_config,
            "homeAutomationBridge.inboxPath",
            "homeAutomationBridge.inbox_path",
            "home_automation.bridge.inbox_path",
            default=bridge_defaults.inbox_path,
        )),
        subscriptions_path=str(_config_value(
            aura_config,
            "homeAutomationBridge.subscriptionsPath",
            "homeAutomationBridge.subscriptions_path",
            "home_automation.bridge.subscriptions_path",
            default=bridge_defaults.subscriptions_path,
        )),
        heartbeat_path=str(_config_value(
            aura_config,
            "homeAutomationBridge.heartbeatPath",
            "homeAutomationBridge.heartbeat_path",
            "home_automation.bridge.heartbeat_path",
            default=bridge_defaults.heartbeat_path,
        )),
        session_id=str(_config_value(
            aura_config,
            "homeAutomationBridge.sessionId",
            "homeAutomationBridge.session_id",
            "home_automation.bridge.session_id",
            default=bridge_defaults.session_id,
        )),
        interface_name=str(_config_value(
            aura_config,
            "homeAutomationBridge.interface",
            "homeAutomationBridge.interfaceName",
            "homeAutomationBridge.interface_name",
            "home_automation.bridge.interface_name",
            default=bridge_defaults.interface_name,
        )),
        heartbeat_seconds=float(_config_value(
            aura_config,
            "homeAutomationBridge.heartbeatSeconds",
            "homeAutomationBridge.heartbeat_seconds",
            "home_automation.bridge.heartbeat_seconds",
            default=bridge_defaults.heartbeat_seconds,
        )),
    )
    return HomeAutomationConfig(
        refresh_interval_seconds=float(_config_value(
            aura_config,
            "homeAutomationBridge.refreshSeconds",
            "homeAutomationBridge.refresh_interval_seconds",
            "home_automation.refresh_interval_seconds",
            default=config_defaults.refresh_interval_seconds,
        )),
        bridge=bridge,
    )
