"""Connection and launch helper for the Home Automation Manager service."""

from __future__ import annotations

import json
import os
import socket
import subprocess
import time
from typing import Any
from urllib import error, request

from modules.home_automation.config import HomeAutomationManagerConfig


class HomeAutomationManagerError(RuntimeError):
    """Raised when the manager service cannot complete an operation."""


class HomeAutomationManagerConnection:
    """HTTP and process launcher for the Home Automation Manager."""

    def __init__(self, config: HomeAutomationManagerConfig, logger=None):
        self.config = config
        self.logger = logger

    @property
    def base_url(self) -> str:
        """Return the manager service base URL."""

        return self.config.base_url

    def is_running(self) -> bool:
        """Return True when the configured host and port are accepting connections."""

        try:
            with socket.create_connection((self.config.host, int(self.config.port)), timeout=self.config.timeout_seconds):
                return True
        except OSError:
            return False

    def ensureRunning(self) -> bool:
        """Start the manager process if the configured port is not already reachable."""

        if self.is_running():
            return False

        return self.startProcess()

    def startProcess(self) -> bool:
        """Launch the configured manager command in the background."""

        command = list(self.config.launch_command or ())
        if not command:
            if self.logger:
                self.logger.warning("Home Automation Manager launch command is not configured.")
            return False

        popen_kwargs: dict[str, Any] = {
            "cwd": self.config.launch_working_directory or None,
            "stdout": subprocess.DEVNULL,
            "stderr": subprocess.DEVNULL,
        }

        if os.name == "nt":
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            startupinfo.wShowWindow = subprocess.SW_HIDE
            popen_kwargs["startupinfo"] = startupinfo
            popen_kwargs["creationflags"] = subprocess.CREATE_NO_WINDOW | subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP
        else:
            popen_kwargs["start_new_session"] = True

        try:
            subprocess.Popen(command, **popen_kwargs)
        except Exception as error:
            if self.logger:
                self.logger.error(f"Failed to launch Home Automation Manager: {error}")
            return False

        if self.logger:
            self.logger.info("Home Automation Manager launch command started in the background.")
        self._waitForAvailability()
        return True

    def request(self, command: str, target: str, **fields) -> dict[str, Any]:
        """Send one manager protocol command."""

        payload: dict[str, Any] = {
            "command": str(command or "").strip().lower(),
            "target": str(target or "").strip().lower(),
            "managed": str(target or "").strip().lower(),
            "service": str(target or "").strip().lower(),
        }
        if fields:
            payload["fields"] = dict(fields)
            payload.update({key: value for key, value in fields.items() if key not in payload})
        return self._requestJson("POST", self.config.protocol_path, payload)

    def getStatus(self) -> dict[str, Any]:
        """Fetch manager status when the service exposes a status endpoint."""

        return self._requestJson("GET", self.config.status_path)

    def start(self, target: str, **fields) -> dict[str, Any]:
        return self.request("start", target, **fields)

    def stop(self, target: str, **fields) -> dict[str, Any]:
        return self.request("stop", target, **fields)

    def restart(self, target: str, **fields) -> dict[str, Any]:
        return self.request("restart", target, **fields)

    def forceStop(self, target: str, **fields) -> dict[str, Any]:
        return self.request("forcestop", target, **fields)

    def _waitForAvailability(self) -> None:
        """Give a freshly-launched manager a brief window to bind its port."""

        timeout = max(0.0, float(self.config.startup_wait_seconds))
        if timeout <= 0:
            return

        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            if self.is_running():
                return
            time.sleep(min(0.25, timeout))

    def _requestJson(self, method: str, path: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        """Send one JSON request to the manager."""

        body = None if payload is None else json.dumps(payload).encode("utf-8")
        headers = {"Accept": "application/json"}
        if payload is not None:
            headers["Content-Type"] = "application/json"

        manager_request = request.Request(
            url=f"{self.base_url}{path}",
            data=body,
            headers=headers,
            method=method,
        )

        try:
            with request.urlopen(manager_request, timeout=self.config.timeout_seconds) as response:
                raw_body = response.read().decode("utf-8")
        except error.URLError as exception:
            reason = getattr(exception, "reason", exception)
            raise HomeAutomationManagerError(f"Failed to reach manager at {self.base_url}: {reason}") from exception
        except OSError as exception:
            raise HomeAutomationManagerError(f"Manager request failed: {exception}") from exception

        try:
            parsed = json.loads(raw_body or "{}")
        except json.JSONDecodeError as exception:
            raise HomeAutomationManagerError(f"Manager returned invalid JSON for {path}.") from exception

        if not isinstance(parsed, dict):
            raise HomeAutomationManagerError(f"Manager returned an unexpected payload for {path}.")
        return parsed
