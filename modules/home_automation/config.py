"""Configuration models for Aura home automation integrations."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(slots=True)
class BridgeConfig:
    """Connection details for the home automation bridge service."""

    host: str = "127.0.0.1"
    port: int = 8080
    use_ssl: bool = False
    api_token: str = ""
    timeout_seconds: float = 3.0

    @property
    def base_url(self) -> str:
        """Return the bridge service base URL."""

        scheme = "https" if self.use_ssl else "http"
        return f"{scheme}://{self.host}:{self.port}"


@dataclass(slots=True)
class ServiceControlConfig:
    """Connection details for remotely starting automation services."""

    host: str = "127.0.0.1"
    port: int = 8091
    use_ssl: bool = False
    api_token: str = ""
    timeout_seconds: float = 5.0
    start_bridge_path: str = "/control/startbridge"
    start_hub_path: str = "/control/starthub"

    @property
    def base_url(self) -> str:
        """Return the service-control base URL."""

        scheme = "https" if self.use_ssl else "http"
        return f"{scheme}://{self.host}:{self.port}"


@dataclass(slots=True)
class HomeAutomationConfig:
    """Configuration bundle for the home automation module."""

    refresh_interval_seconds: float = 5.0
    bridge: BridgeConfig = field(default_factory=BridgeConfig)
    control: ServiceControlConfig = field(default_factory=ServiceControlConfig)
