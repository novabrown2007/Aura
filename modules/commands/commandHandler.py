"""Command-system implementation for `commandHandler` within Aura's CLI architecture."""

class CommandHandler:
    """
    Root command handler for Aura.

    Responsibilities:
    - Register top-level command namespaces (e.g., /debug, /system)
    - Register root-level commands (e.g., /help)
    - Route incoming command strings to the correct handler or command
    - Provide access to all registered commands for help generation
    """

    def __init__(self, context):
        """
        Initialize the CommandHandler.

        Args:
            context (RuntimeContext):
                Global runtime context.
        """
        self.context = context
        self.logger = None
        if context.logger:
            self.logger = context.logger.getChild("Commands")
        # Dictionary of namespace handlers (e.g., "debug" → DebugCommandHandler)
        self.handlers = {}
        # Dictionary of root-level commands (e.g., "help" → HelpCommand)
        self.commands = {}
        if self.logger:
            self.logger.info("Initialized.")


    # --------------------------------------------------
    # Utility
    # --------------------------------------------------
    def _invalid(self, command: str) -> str:
        """
        Generate a standardized invalid command message.

        Args:
            command (str):
                The full command string entered by the user.

        Returns:
            str:
                Formatted error message.
        """
        return (
            f'Command "{command}" is not a valid command. '
            f'For a list of valid commands, run "/help".'
        )


    # --------------------------------------------------
    # Registration
    # --------------------------------------------------
    def registerHandler(self, name: str, handler):
        """
        Register a namespace handler.

        Args:
            name (str):
                Command namespace (e.g., "debug").

            handler:
                Handler instance responsible for routing subcommands.
        """
        self.handlers[name] = handler
        if self.logger:
            self.logger.info(f"Registered handler: /{name}")

    def registerCommand(self, command):
        """
        Register a root-level command.

        This assigns the command its full command path and stores it
        for later routing and help generation.

        Args:
            command (BaseCommand):
                Command instance.
        """
        command.full_command = f"/{command.name}"
        self.commands[command.name] = command
        if self.logger:
            self.logger.info(f"Registered command: {command.full_command}")


    # --------------------------------------------------
    # Access
    # --------------------------------------------------
    def getAllCommands(self):
        """
        Retrieve all registered commands.

        Includes:
        - Root-level commands (e.g., /help)
        - Nested commands from all registered handlers

        Returns:
            list[BaseCommand]:
                List of all command instances.
        """
        all_commands = list(self.commands.values())
        for handler_name, handler in self.handlers.items():
            if hasattr(handler, "getCommands"):
                all_commands.extend(handler.getCommands())
        return all_commands


    # --------------------------------------------------
    # Routing
    # --------------------------------------------------
    def handle(self, text: str) -> str:
        """
        Route a command string to the appropriate handler or command.

        Args:
            text (str):
                Raw command input (must start with '/').

        Returns:
            str:
                Response from the executed command.
        """

        parts = text.strip().split()
        # Safety check for empty input
        if not parts:
            return self._invalid("")
        # Extract root command (e.g., "/debug" → "debug")
        root = parts[0].lstrip("/").lower()
        # Direct command
        command = self.commands.get(root)
        if command:
            return command.execute(parts[1:])
        # Namespace handler
        handler = self.handlers.get(root)
        if handler:
            return handler.handle(parts[1:], original=text)
        # Unknown command
        if self.logger:
            self.logger.warning(f"Unknown command: {root}")
        return self._invalid(text)
