"""Command-system implementation for `baseCommand` within Aura's CLI architecture."""

class BaseCommand:
    """
    Base class for all executable commands.

    Each command must define:
        - name (str)
        - help_message (str)

    The full command path (e.g., "/debug memory") is assigned
    during registration.
    """

    name = None
    help_message = "No description provided."

    def __init__(self, context):
        """Initialize `BaseCommand` with required dependencies and internal state."""
        self.context = context
        # Logger
        self.logger = None
        if context.logger:
            self.logger = context.logger.getChild("Commands")
        # Will be set by handler
        self.full_command = None
        if not self.name:
            raise ValueError(
                f"{self.__class__.__name__} must define a 'name' attribute."
            )


    # --------------------------------------------------
    # Execution
    # --------------------------------------------------
    def execute(self, args: list[str]) -> str:
        """Execute the command using parsed arguments and return a user-facing message."""
        raise NotImplementedError("Command must implement execute().")
