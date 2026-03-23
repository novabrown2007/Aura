"""Core implementation for `outputManager` in the Aura assistant project."""

class OutputManager:
    """
    Handles outgoing responses from Aura.

    The OutputManager is responsible for sending responses to the
    appropriate output interfaces such as CLI, web clients, mobile
    apps, or speech systems.
    """

    def __init__(self, context):
        """
        Initialize the OutputManager.

        Args:
            context (RuntimeContext)
        """

        self.context = context
        self.logger = context.logger.getChild("Output") if context.logger else None

        if self.logger:
            self.logger.info("Initialized.")

    # --------------------------------------------------
    # Output Delivery
    # --------------------------------------------------

    def send(self, message: str):
        """
        Send a response message.

        Args:
            message (str)
        """

        if self.logger:
            self.logger.debug(f"Sending output: {message}")

        # Default output (CLI)
        print(f"Aura: {message}")
