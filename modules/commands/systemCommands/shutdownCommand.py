"""Command-system implementation for `shutdownCommand` within Aura's CLI architecture."""

from modules.commands.baseCommand import BaseCommand


class ShutdownCommand(BaseCommand):
    """
    Shuts down the Aura system.

    This command signals the engine to stop running.
    """

    name = "shutdown"
    help_message = "Shut down Aura. Use --force for immediate shutdown."

    def __init__(self, context):
        """
        Initialize the ShutdownCommand.

        Args:
            context (RuntimeContext):
                Global runtime context.
        """
        super().__init__(context)
        # Logger
        if context.logger:
            self.logger = context.logger.getChild("Commands.System.Shutdown")
        # Register with SystemCommandHandler
        context.systemCommandHandler.registerCommand(self)
        if self.logger:
            self.logger.info("Initialized.")


    # --------------------------------------------------
    # Execution
    # --------------------------------------------------
    def execute(self, args: list[str]) -> str:
        """
        Execute shutdown command.

        Args:
            args (list[str])

        Returns:
            str
        """
        force = "--force" in [arg.lower() for arg in args]

        self.context.should_exit = True
        if self.logger:
            self.logger.warning(f"Shutdown command executed (force={force})")
        if force:
            return "Force shutdown requested. Shutting down Aura..."
        return "Shutting down Aura..."
