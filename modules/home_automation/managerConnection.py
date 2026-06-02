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
        """Return True when the manager responds with a valid status payload."""

        try:
            status = self.getStatus()
            return self._isManagerResponse(status)
        except OSError:
            return False
        except HomeAutomationManagerError:
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

        normalized_target = self._normalizeTarget(target)
        normalized_action = self._normalizeAction(command)
        if normalized_target not in self._supported_targets():
            raise HomeAutomationManagerError(f"Unsupported manager target: {target!r}")

        payload = {
            "target": normalized_target,
            "action": normalized_action,
        }
        if fields and self.logger:
            self.logger.debug(f"Manager command fields ignored by current protocol: {sorted(fields.keys())}")

        response = self._requestJson("POST", self.config.command_path, payload)
        if self._isSuccessfulManagerResponse(response):
            return response

        error_message = self._managerErrorMessage(response, normalized_action, normalized_target)
        if self._canFallbackToDirectRoute(response):
            fallback_response = self._requestJson(
                "POST",
                self._directRoute(normalized_target, normalized_action),
                None,
            )
            if self._isSuccessfulManagerResponse(fallback_response):
                return fallback_response
            error_message = self._managerErrorMessage(fallback_response, normalized_action, normalized_target)

        raise HomeAutomationManagerError(error_message)

    def getStatus(self) -> dict[str, Any]:
        """Fetch manager status when the service exposes a status endpoint."""

        response = self._requestJson("GET", self.config.status_path)
        if not self._isManagerResponse(response):
            raise HomeAutomationManagerError(self._managerErrorMessage(response, "status", "manager"))
        return response

    def start(self, target: str, **fields) -> dict[str, Any]:
        return self.request("start", target, **fields)

    def stop(self, target: str, **fields) -> dict[str, Any]:
        return self.request("stop", target, **fields)

    def restart(self, target: str, **fields) -> dict[str, Any]:
        return self.request("restart", target, **fields)

    def forceStop(self, target: str, **fields) -> dict[str, Any]:
        return self.request("force_stop", target, **fields)

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
                status_code = int(getattr(response, "status", 200) or 200)
                status_text = str(getattr(response, "reason", "OK") or "OK")
        except error.URLError as exception:
            if isinstance(exception, error.HTTPError):
                raw_body = exception.read().decode("utf-8") if exception.fp else ""
                status_code = int(getattr(exception, "code", 500) or 500)
                status_text = str(getattr(exception, "reason", "HTTPError") or "HTTPError")
            else:
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
        parsed.setdefault("_http_status", status_code)
        parsed.setdefault("_http_reason", status_text)
        return parsed

    @staticmethod
    def _normalizeAction(command: str) -> str:
        action = str(command or "").strip().lower().replace("-", "_").replace(" ", "_")
        aliases = {
            "forcequit": "force_stop",
            "forcestop": "force_stop",
            "force_stop": "force_stop",
            "kill": "force_stop",
        }
        return aliases.get(action, action)

    @staticmethod
    def _normalizeTarget(target: str) -> str:
        return str(target or "").strip().lower()

    @staticmethod
    def _supported_targets() -> tuple[str, ...]:
        return ("bridge", "hub")

    def _directRoute(self, target: str, action: str) -> str:
        normalized_action = self._normalizeAction(action)
        if normalized_action == "force_stop":
            normalized_action = "force-stop"
        route = f"/{target}/{normalized_action}"
        return route

    @staticmethod
    def _isSuccessfulManagerResponse(response: dict[str, Any]) -> bool:
        if not response:
            return False
        status = response.get("_http_status")
        if isinstance(status, int) and status >= 400:
            return False
        if response.get("ok") is False:
            return False
        return True

    def _isManagerResponse(self, response: dict[str, Any]) -> bool:
        return (
            isinstance(response, dict)
            and response.get("protocol") == "home-automation-manager-control/1"
            and response.get("ok") is True
            and response.get("status") == "ok"
        )

    def _canFallbackToDirectRoute(self, response: dict[str, Any]) -> bool:
        status = response.get("_http_status")
        return isinstance(status, int) and status in {404, 405}

    def _managerErrorMessage(self, response: dict[str, Any], action: str, target: str) -> str:
        if not isinstance(response, dict):
            return f"Manager request failed for {target}.{action}."
        message = str(response.get("error") or response.get("status") or response.get("message") or "").strip()
        status = response.get("_http_status")
        if status:
            prefix = f"Manager request failed with HTTP {status}"
            if message:
                return f"{prefix}: {message}"
            return f"{prefix} for {target}.{action}."
        if message:
            return message
        return f"Manager returned an unexpected response for {target}.{action}."
