"""Shutdown lifecycle action for Aura."""


class Shutdown:
    """
    Stop the active Aura runtime loop.

    This action marks the current runtime for exit without requesting a new
    runtime cycle afterward.
    """

    def __init__(self, context):
        """
        Initialize the shutdown action.

        Args:
            context:
                Runtime context whose lifecycle flags will be updated.
        """

        self.context = context
        self.logger = context.logger.getChild("System.Shutdown") if context.logger else None

    def execute(self) -> bool:
        """
        Request an orderly runtime shutdown.

        Returns:
            bool:
                `True` after the shutdown flags are applied.
        """

        self.context.restart_requested = False
        self.context.should_exit = True

        if self.logger:
            self.logger.info("Shutdown requested.")

        return True
