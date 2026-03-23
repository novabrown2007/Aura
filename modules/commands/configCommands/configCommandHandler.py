"""Command-system implementation for `configCommandHandler` within Aura's CLI architecture."""

class ConfigCommandHandler:
    """
    Handler for all /config commands.

    Routes config-related subcommands such as:
        /config reload
    """

    name = "config"

    def __init__(self, context):
        """Initialize `ConfigCommandHandler` with required dependencies and internal state."""
        self.context = context
        self.logger = None
        if context.logger:
            self.logger = context.logger.getChild("Commands.Config")

        self.commands = {}

        if self.logger:
            self.logger.info("Initialized.")

        context.commandHandler.registerHandler(self.name, self)

    def _invalid(self, command: str) -> str:
        """Return the standardized invalid-command response message."""
        return (
            f'Command "{command}" is not a valid command. '
            f'For a list of valid commands, run "/help".'
        )

    def registerCommand(self, command):
        """Register a command instance and expose it through this handler namespace."""
        command.full_command = f"/{self.name} {command.name}"
        self.commands[command.name] = command
        if self.logger:
            self.logger.info(f"Registered config command: {command.full_command}")

    def getCommands(self):
        """Return the list of commands currently registered on this handler."""
        return list(self.commands.values())

    def handle(self, parts: list[str], original: str = "") -> str:
        """Route parsed command input to the matching command implementation."""
        if not parts:
            return self._invalid(original)

        cmd_name = parts[0].lower()
        command = self.commands.get(cmd_name)

        if not command:
            if self.logger:
                self.logger.warning(f"Unknown config command: {cmd_name}")
            return self._invalid(original)

        return command.execute(parts[1:])

