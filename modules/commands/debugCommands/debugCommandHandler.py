"""Command-system implementation for `debugCommandHandler` within Aura's CLI architecture."""

class DebugCommandHandler:
    """
    Handler for all /debug commands.

    This class routes debug-related commands such as:
        /debug memory
        /debug llm
        /debug database

    Individual debug commands register themselves using registerCommand().
    """

    name = "debug"

    def __init__(self, context):
        """
        Initialize the debug command handler.

        Args:
            context (RuntimeContext):
                Global runtime context.
        """

        self.context = context
        # Logger
        self.logger = None
        if context.logger:
            self.logger = context.logger.getChild("Commands.Debug")
        # Registered debug commands
        self.commands = {}
        if self.logger:
            self.logger.info("Initialized.")
        # Register with root handler
        context.commandHandler.registerHandler(self.name, self)


    # --------------------------------------------------
    # Utility
    # --------------------------------------------------
    def _invalid(self, command: str) -> str:
        """
        Generate standardized invalid command message.

        Args:
            command (str):
                Full command string.

        Returns:
            str:
                Error message.
        """

        return (
            f'Command "{command}" is not a valid command. '
            f'For a list of valid commands, run "/help".'
        )


    # --------------------------------------------------
    # Registration
    # --------------------------------------------------
    def registerCommand(self, command):
        """
        Register a debug command.

        Args:
            command (BaseCommand):
                Command instance.
        """
        command.full_command = f"/{self.name} {command.name}"
        self.commands[command.name] = command
        if self.logger:
            self.logger.info(f"Registered debug command: {command.full_command}")


    # --------------------------------------------------
    # Access
    # --------------------------------------------------
    def getCommands(self):
        """
        Return all registered debug commands.

        Returns:
            list[BaseCommand]
        """
        return list(self.commands.values())


    # --------------------------------------------------
    # Routing
    # --------------------------------------------------
    def handle(self, parts: list[str], original: str = "") -> str:
        """
        Route a debug command to its implementation.

        Args:
            parts (list[str]):
                Command arguments (excluding "/debug").

            original (str):
                Full original command string.

        Returns:
            str:
                Command output.
        """

        # No subcommand provided
        if not parts:
            return self._invalid(original)
        cmd_name = parts[0].lower()
        command = self.commands.get(cmd_name)
        # Unknown debug command
        if not command:
            if self.logger:
                self.logger.warning(f"Unknown debug command: {cmd_name}")
            return self._invalid(original)
        # Execute command
        return command.execute(parts[1:])
