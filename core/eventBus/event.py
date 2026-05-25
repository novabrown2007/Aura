"""Event model used by Aura's internal event bus."""

from typing import Optional


class Event:
    """
    Represents a single internal Aura event.

    Events are passed through the EventBus so subsystems can communicate
    without directly importing or depending on each other.
    """

    def __init__(self, name: str, data: Optional[dict] = None):
        """
        Initialize an event.

        Args:
            name (str):
                Event name or event type.

            data (dict | None):
                Optional event payload.
        """

        self.name = name
        self.data = data or {}

    def __repr__(self) -> str:
        """Return a debug-friendly event representation."""

        return f"Event(name={self.name}, data={self.data})"
