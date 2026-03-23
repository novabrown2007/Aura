"""Command-system implementation for `llmDebugCommand` within Aura's CLI architecture."""

import time

import requests

from modules.commands.baseCommand import BaseCommand


class LLMDebugCommand(BaseCommand):
    """
    Debug command for LLM connectivity checks.
    """

    name = "llm"
    help_message = "LLM diagnostics (ping)."

    def __init__(self, context):
        """Initialize `LLMDebugCommand` with required dependencies and internal state."""
        super().__init__(context)
        context.debugCommandHandler.registerCommand(self)

    def execute(self, args: list[str]) -> str:
        """Execute the command using parsed arguments and return a user-facing message."""
        action = args[0].lower() if args else "ping"
        if action != "ping":
            return "Usage: /debug llm ping"

        llm = self.context.require("llm")
        start = time.perf_counter()
        try:
            response = requests.post(
                llm.endpoint,
                json={"model": llm.model, "prompt": "Reply with: pong", "stream": False},
                timeout=10,
            )
        except requests.RequestException as error:
            return f"LLM ping failed: {error}"

        elapsed_ms = int((time.perf_counter() - start) * 1000)

        if response.status_code != 200:
            return f"LLM ping failed: HTTP {response.status_code}"

        payload = response.json()
        text = str(payload.get("response", "")).strip()
        if not text:
            return f"LLM ping failed: empty response ({elapsed_ms}ms)."
        return f"LLM ping: ok ({elapsed_ms}ms)."

