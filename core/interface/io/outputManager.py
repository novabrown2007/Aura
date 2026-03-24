"""Interface-agnostic output API for Aura runtime responses."""

from typing import Optional


class OutputManager:
    """
    Store and publish runtime responses for attached interfaces.

    The OutputManager no longer prints directly to a terminal. Instead it
    records outbound response packets and optionally notifies subscribers so
    interface-specific branches can attach their own rendering logic.
    """

    def __init__(self, context):
        """
        Initialize the output API manager.

        Args:
            context:
                Global runtime context.
        """

        self.context = context
        self.logger = context.logger.getChild("Output") if context.logger else None
        self._messages = []
        self._subscribers = []

        if self.logger:
            self.logger.info("Initialized.")

    def publish(self, packet: dict) -> dict:
        """
        Store and broadcast one response packet.

        Args:
            packet:
                Structured request/response payload produced by the InputManager.

        Returns:
            dict:
                Stored copy of the packet.
        """

        stored_packet = dict(packet)
        self._messages.append(stored_packet)

        if self.logger:
            self.logger.debug(f"Published output packet {stored_packet.get('id')}")

        for subscriber in list(self._subscribers):
            subscriber(dict(stored_packet))

        return dict(stored_packet)

    def send(self, message: str) -> dict:
        """
        Publish a plain response message for compatibility with older callers.
        """

        return self.publish({"id": None, "input": None, "intent": None, "response": message, "source": "system"})

    def subscribe(self, callback):
        """
        Register a callback that receives each published output packet.
        """

        self._subscribers.append(callback)

    def unsubscribe(self, callback):
        """
        Remove a previously registered output subscriber.
        """

        self._subscribers = [subscriber for subscriber in self._subscribers if subscriber != callback]

    def getMessages(self, limit: Optional[int] = None) -> list[dict]:
        """
        Return stored output packets, optionally limited to recent entries.
        """

        if limit is None or limit >= len(self._messages):
            return [dict(packet) for packet in self._messages]
        return [dict(packet) for packet in self._messages[-int(limit):]]

    def getLastMessage(self):
        """
        Return the most recently published output packet when one exists.
        """

        if not self._messages:
            return None
        return dict(self._messages[-1])

    def clearMessages(self):
        """
        Clear stored output packets.
        """

        self._messages.clear()
