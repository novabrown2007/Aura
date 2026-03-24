"""Restart lifecycle action for Aura."""


class Restart:
    """
    Request a full Aura runtime restart.

    Restarting stops the current runtime loop and signals the outer application
    bootstrap to create a fresh context and reinitialize every subsystem.
    """

    def __init__(self, context):
        """
        Initialize the restart action.

        Args:
            context:
                Runtime context whose lifecycle flags will be updated.
        """

        self.context = context
        self.logger = context.logger.getChild("System.Restart") if context.logger else None

    def execute(self) -> bool:
        """
        Request an orderly runtime restart.

        Returns:
            bool:
                `True` after the restart flags are applied.
        """

        self.context.restart_requested = True
        self.context.should_exit = True

        if self.logger:
            self.logger.info("Restart requested.")

        return True
