"""Remote service-control skeleton for home automation."""

from __future__ import annotations

import json
from typing import Any
from urllib import error, request

from modules.home_automation.config import ServiceControlConfig


class ServiceControlError(RuntimeError):
    """Raised when service control cannot complete a request."""


class ServiceControlConnection:
    """Connection boundary for starting home automation services."""

    def __init__(self, config: ServiceControlConfig):
        self.config = config

    def startBridge(self) -> dict[str, object]:
        """Start the bridge service."""

        return self._requestJson("POST", self.config.start_bridge_path, {"service": "bridge"})

    def startHub(self) -> dict[str, object]:
        """Start the hub service."""

        return self._requestJson("POST", self.config.start_hub_path, {"service": "hub"})

    def _requestJson(self, method: str, path: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        """Send one JSON request to the service-control endpoint."""

        body = None if payload is None else json.dumps(payload).encode("utf-8")
        headers = {"Accept": "application/json"}
        if payload is not None:
            headers["Content-Type"] = "application/json"
        if self.config.api_token:
            headers["Authorization"] = f"Bearer {self.config.api_token}"

        control_request = request.Request(
            url=f"{self.config.base_url}{path}",
            data=body,
            headers=headers,
            method=method,
        )

        try:
            with request.urlopen(control_request, timeout=self.config.timeout_seconds) as response:
                raw_body = response.read().decode("utf-8")
        except error.URLError as exception:
            reason = getattr(exception, "reason", exception)
            raise ServiceControlError(f"Failed to reach service control at {self.config.base_url}: {reason}") from exception
        except OSError as exception:
            raise ServiceControlError(f"Service control request failed: {exception}") from exception

        try:
            parsed = json.loads(raw_body or "{}")
        except json.JSONDecodeError as exception:
            raise ServiceControlError(f"Service control returned invalid JSON for {path}.") from exception

        if not isinstance(parsed, dict):
            raise ServiceControlError(f"Service control returned an unexpected payload for {path}.")
        return parsed
