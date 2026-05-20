"""Remote service-control skeleton for home automation."""

from __future__ import annotations

from modules.home_automation.config import ServiceControlConfig


class ServiceControlError(RuntimeError):
    """Raised when service control cannot complete a request."""


class ServiceControlConnection:
    """Connection boundary for starting home automation services."""

    def __init__(self, config: ServiceControlConfig):
        self.config = config

    def startBridge(self) -> dict[str, object]:
        """Start the bridge service."""

        raise NotImplementedError("Bridge service control is not implemented yet.")

    def startHub(self) -> dict[str, object]:
        """Start the hub service."""

        raise NotImplementedError("Hub service control is not implemented yet.")
