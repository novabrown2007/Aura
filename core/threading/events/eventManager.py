from typing import Callable, Dict, List
from .events import Event


class EventManager:
    """
    Central event bus for the Aura assistant.

    The EventManager provides a publish/subscribe system that allows
    different parts of the application to communicate without direct
    dependencies.

    Components can subscribe to specific event names and receive
    notifications when those events are emitted.

    Example:
        def on_user_input(event):
            print(event.data["text"])

        eventManager.subscribe("user_input", on_user_input)

        eventManager.emit(Event("user_input", {"text": "Hello"}))
    """

    def __init__(self, context):
        """
        Initialize the event manager.

        Args:
            context (RuntimeContext):
                Global runtime context.
        """

        self.context = context
        self.logger = None

        if context.logger:
            self.logger = context.logger.getChild("Events")

        # # Dictionary mapping event names to lists of listener callbacks.
        self.listeners: Dict[str, List[Callable]] = {}

        if self.logger:
            self.logger.info(f"eventManager.py has been initialized.")
    # --------------------------------------------------
    # Subscription
    # --------------------------------------------------

    def subscribe(self, event_name: str, callback: Callable):
        """
        Subscribe a callback function to an event.

        Args:
            event_name (str):
                Name of the event to listen for.

            callback (Callable):
                Function to call when the event is emitted.
                The callback must accept a single argument: Event.
        """

        if event_name not in self.listeners:
            self.listeners[event_name] = []

        self.listeners[event_name].append(callback)

        if self.logger:
            self.logger.debug(f"Listener subscribed to event: {event_name}")

    def unsubscribe(self, event_name: str, callback: Callable):
        """
        Remove a callback from an event.

        Args:
            event_name (str):
                Name of the event.

            callback (Callable):
                The callback to remove.
        """

        if event_name not in self.listeners:
            return

        if callback in self.listeners[event_name]:
            self.listeners[event_name].remove(callback)

            if self.logger:
                self.logger.debug(f"Listener removed from event: {event_name}")

    # --------------------------------------------------
    # Event Emission
    # --------------------------------------------------

    def emit(self, event: Event):
        """
        Emit an event to all subscribed listeners.

        Args:
            event (Event):
                The event to emit.
        """

        listeners = self.listeners.get(event.name, [])

        if self.logger:
            self.logger.debug(
                f"Emitting event '{event.name}' to {len(listeners)} listener(s)"
            )

        for callback in listeners:
            try:
                callback(event)
            except Exception as e:
                if self.logger:
                    self.logger.error(
                        f"Error handling event '{event.name}': {e}"
                    )

    # --------------------------------------------------
    # Debug Helpers
    # --------------------------------------------------

    def listEvents(self) -> List[str]:
        """
        List all registered event types.

        Returns:
            list[str]
        """

        return list(self.listeners.keys())

    def listenerCount(self, event_name: str) -> int:
        """
        Get the number of listeners registered for an event.

        Args:
            event_name (str)

        Returns:
            int
        """

        return len(self.listeners.get(event_name, []))
