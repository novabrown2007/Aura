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


def _env_list(name: str, default: tuple[str, ...] = ()) -> tuple[str, ...]:
    value = _env_value(name, None)
    if value is None:
        return default
    if isinstance(value, (list, tuple)):
        return tuple(str(item) for item in value if str(item).strip())
    return tuple(part for part in str(value).split() if part)


def _normalize_command_list(value) -> tuple[str, ...]:
    """Normalize a config command definition into an executable argument tuple."""

    if value is None:
        return ()
    if isinstance(value, str):
        return tuple(part for part in value.split() if part)
    if isinstance(value, (list, tuple)):
        return tuple(str(item) for item in value if str(item).strip())
    return (str(value),)


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

    @property
    def ssl(self) -> bool:
        """Backward-compatible alias for use_ssl."""

        return self.use_ssl


@dataclass(slots=True)
class HomeAutomationManagerConfig:
    """Connection and launch details for the Home Automation Manager service."""

    host: str = field(default_factory=lambda: str(_env_value("HOME_AUTOMATION_MANAGER_HOST", "127.0.0.1")))
    port: int = field(default_factory=lambda: _env_int("HOME_AUTOMATION_MANAGER_PORT", 8080))
    use_ssl: bool = field(default_factory=lambda: _env_bool("HOME_AUTOMATION_MANAGER_SSL", False))
    timeout_seconds: float = field(default_factory=lambda: _env_float("HOME_AUTOMATION_MANAGER_TIMEOUT", 3.0))
    protocol_path: str = "/protocol/manager"
    status_path: str = "/status"
    launch_command: tuple[str, ...] = field(default_factory=lambda: _env_list("HOME_AUTOMATION_MANAGER_COMMAND"))
    launch_working_directory: str = field(default_factory=lambda: str(_env_value("HOME_AUTOMATION_MANAGER_WORKDIR", "")))
    auto_start: bool = field(default_factory=lambda: _env_bool("HOME_AUTOMATION_MANAGER_AUTO_START", False))
    auto_start_bridge: bool = field(default_factory=lambda: _env_bool("HOME_AUTOMATION_MANAGER_AUTO_START_BRIDGE", False))
    startup_wait_seconds: float = field(default_factory=lambda: _env_float("HOME_AUTOMATION_MANAGER_STARTUP_WAIT", 2.5))
    bridge_target: str = "bridge"
    hub_target: str = "hub"
    suite_target: str = "suite"

    @property
    def base_url(self) -> str:
        """Return the manager service base URL."""

        scheme = "https" if self.use_ssl else "http"
        return f"{scheme}://{self.host}:{self.port}"

    @property
    def ssl(self) -> bool:
        """Backward-compatible alias for use_ssl."""

        return self.use_ssl


@dataclass(slots=True)
class HomeAutomationConfig:
    """Configuration bundle for the home automation module."""

    refresh_interval_seconds: float = field(default_factory=lambda: _env_float("HOME_AUTOMATION_REFRESH_SECONDS", 5.0))
    bridge: BridgeConfig = field(default_factory=BridgeConfig)
    manager: HomeAutomationManagerConfig = field(default_factory=HomeAutomationManagerConfig)


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
    manager_defaults = HomeAutomationManagerConfig()

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
    manager = HomeAutomationManagerConfig(
        host=str(_config_value(
            aura_config,
            "homeAutomationManager.host",
            "homeAutomationManager.hostname",
            "home_automation.manager.host",
            default=manager_defaults.host,
        )),
        port=int(_config_value(
            aura_config,
            "homeAutomationManager.port",
            "home_automation.manager.port",
            default=manager_defaults.port,
        )),
        use_ssl=as_bool(_config_value(
            aura_config,
            "homeAutomationManager.ssl",
            "homeAutomationManager.use_ssl",
            "home_automation.manager.use_ssl",
            default=manager_defaults.use_ssl,
        )),
        timeout_seconds=float(_config_value(
            aura_config,
            "homeAutomationManager.timeout",
            "homeAutomationManager.timeoutSeconds",
            "homeAutomationManager.timeout_seconds",
            "home_automation.manager.timeout_seconds",
            default=manager_defaults.timeout_seconds,
        )),
        protocol_path=str(_config_value(
            aura_config,
            "homeAutomationManager.protocolPath",
            "homeAutomationManager.protocol_path",
            "home_automation.manager.protocol_path",
            default=manager_defaults.protocol_path,
        )),
        status_path=str(_config_value(
            aura_config,
            "homeAutomationManager.statusPath",
            "homeAutomationManager.status_path",
            "home_automation.manager.status_path",
            default=manager_defaults.status_path,
        )),
        launch_command=_normalize_command_list(_config_value(
            aura_config,
            "homeAutomationManager.launchCommand",
            "homeAutomationManager.launch_command",
            "home_automation.manager.launch_command",
            default=manager_defaults.launch_command,
        )),
        launch_working_directory=str(_config_value(
            aura_config,
            "homeAutomationManager.launchWorkingDirectory",
            "homeAutomationManager.launch_working_directory",
            "home_automation.manager.launch_working_directory",
            default=manager_defaults.launch_working_directory,
        )),
        auto_start=as_bool(_config_value(
            aura_config,
            "homeAutomationManager.autoStart",
            "homeAutomationManager.auto_start",
            "home_automation.manager.auto_start",
            default=manager_defaults.auto_start,
        )),
        auto_start_bridge=as_bool(_config_value(
            aura_config,
            "homeAutomationManager.autoStartBridge",
            "homeAutomationManager.auto_start_bridge",
            "home_automation.manager.auto_start_bridge",
            default=manager_defaults.auto_start_bridge,
        )),
        startup_wait_seconds=float(_config_value(
            aura_config,
            "homeAutomationManager.startupWaitSeconds",
            "homeAutomationManager.startup_wait_seconds",
            "home_automation.manager.startup_wait_seconds",
            default=manager_defaults.startup_wait_seconds,
        )),
        bridge_target=str(_config_value(
            aura_config,
            "homeAutomationManager.bridgeTarget",
            "homeAutomationManager.bridge_target",
            "home_automation.manager.bridge_target",
            default=manager_defaults.bridge_target,
        )),
        hub_target=str(_config_value(
            aura_config,
            "homeAutomationManager.hubTarget",
            "homeAutomationManager.hub_target",
            "home_automation.manager.hub_target",
            default=manager_defaults.hub_target,
        )),
        suite_target=str(_config_value(
            aura_config,
            "homeAutomationManager.suiteTarget",
            "homeAutomationManager.suite_target",
            "home_automation.manager.suite_target",
            default=manager_defaults.suite_target,
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
        manager=manager,
    )
