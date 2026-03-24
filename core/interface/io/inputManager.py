"""Interface-agnostic input API for Aura runtime requests."""

from datetime import datetime
from typing import Optional


class InputManager:
    """
    Handle incoming runtime requests without assuming any interface type.

    Interfaces call `submit()` with raw text and receive a structured packet
    describing the interpreted intent and generated response. This keeps the
    core runtime independent from CLI, desktop, web, or mobile frontends.
    """

    def __init__(self, context):
        """
        Initialize the input API manager.

        Args:
            context:
                Global runtime context.
        """

        self.context = context
        self.logger = context.logger.getChild("Input") if context.logger else None
        self._next_request_id = 1
        self._request_log = []

        if self.logger:
            self.logger.info("Initialized.")

    def submit(self, text: str, source: str = "api", metadata: Optional[dict] = None) -> dict:
        """
        Process one inbound request and return a structured response packet.

        Args:
            text:
                Raw user input.
            source:
                Interface identifier such as `api`, `windows`, or `web`.
            metadata:
                Optional interface metadata to retain with the request.

        Returns:
            dict:
                Request/response packet for the caller.
        """

        if self.logger:
            self.logger.debug(f"Received input from {source}: {text}")

        interpreter = self.context.require("interpreter")
        router = self.context.require("intentRouter")
        intent = interpreter.interpret(text)
        response = router.route(intent)

        packet = {
            "id": self._next_request_id,
            "source": source,
            "input": text,
            "intent": getattr(intent, "name", None),
            "response": response,
            "metadata": dict(metadata or {}),
            "created_at": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"),
        }
        self._next_request_id += 1
        self._request_log.append(packet)

        output_manager = getattr(self.context, "outputManager", None)
        if output_manager is not None:
            output_manager.publish(packet)

        return dict(packet)

    def process(self, text: str) -> str:
        """
        Process text and return only the response body for compatibility.
        """

        return str(self.submit(text).get("response", ""))

    def getRequests(self, limit: Optional[int] = None) -> list[dict]:
        """
        Return processed request packets, optionally limited to recent entries.
        """

        if limit is None or limit >= len(self._request_log):
            return [dict(packet) for packet in self._request_log]
        return [dict(packet) for packet in self._request_log[-int(limit):]]

    def clearRequests(self):
        """
        Clear the processed request log.
        """

        self._request_log.clear()
