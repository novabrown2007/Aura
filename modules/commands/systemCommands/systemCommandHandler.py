"""Command-system implementation for `systemCommandHandler` within Aura's CLI architecture."""

class SystemCommandHandler:
    """
    Handler for all /system commands.

    This class routes system-level commands such as:
        /system shutdown
        /system config

    Individual system commands register themselves using registerCommand().
    """

    name = "system"

    def __init__(self, context):
        """
        Initialize the system command handler.

        Args:
            context (RuntimeContext):
                Global runtime context.
        """
        self.context = context
        # Logger
        self.logger = None
        if context.logger:
            self.logger = context.logger.getChild("Commands.System")
        # Registered system commands
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
        Register a system command.

        Args:
            command (BaseCommand):
                Command instance.
        """
        command.full_command = f"/{self.name} {command.name}"
        self.commands[command.name] = command
        if self.logger:
            self.logger.info(f"Registered system command: {command.full_command}")


    # --------------------------------------------------
    # Access
    # --------------------------------------------------
    def getCommands(self):
        """
        Return all registered system commands.

        Returns:
            list[BaseCommand]
        """
        return list(self.commands.values())


    # --------------------------------------------------
    # Routing
    # --------------------------------------------------
    def handle(self, parts: list[str], original: str = "") -> str:
        """
        Route a system command to its implementation.

        Args:
            parts (list[str]):
                Command arguments (excluding "/system").

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
        # Unknown system command
        if not command:
            if self.logger:
                self.logger.warning(f"Unknown system command: {cmd_name}")

            return self._invalid(original)
        # Execute command
        return command.execute(parts[1:])
