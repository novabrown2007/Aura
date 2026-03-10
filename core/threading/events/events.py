from typing import Optional


class Event:
    """
    Represents an event within the Aura system.

    Events are the primary communication mechanism between different
    components of the assistant. They allow subsystems and modules to
    interact without direct dependencies.

    Each event has a name identifying the event type and an optional
    data payload containing event-specific information.

    Example:
        Event("user_input", {"text": "what's the weather?"})

        Event("reminder_triggered", {
            "reminder_id": 42
        })
    """

    def __init__(self, name: str, data: Optional[dict] = None):
        """
        Initialize an event.

        Args:
            name (str):
                The name or type of the event.

            data (dict | None):
                Optional payload containing event data.
        """

        # Name identifying the event type.
        self.name = name

        # Dictionary containing event payload data.
        self.data = data or {}

    def __repr__(self) -> str:
        """
        Return a debug-friendly representation of the event.

        Returns:
            str
        """

        return f"Event(name={self.name}, data={self.data})"
