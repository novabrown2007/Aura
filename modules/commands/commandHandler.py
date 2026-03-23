"""Command-system implementation for `commandHandler` within Aura's CLI architecture."""

import time


class CommandHandler:
    """
    Root command handler for Aura.

    Responsibilities:
    - Register top-level command namespaces (e.g., /debug, /system)
    - Register root-level commands (e.g., /help)
    - Route incoming command strings to the correct handler or command
    - Provide access to all registered commands for help generation
    - Persist command execution logs to the database
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

        self.handlers = {}
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

    def _logCommand(
        self,
        command_text: str,
        command_root: str,
        status: str,
        duration_ms: int,
        response_text: str = None,
        error_text: str = None,
    ):
        """
        Persist command execution metadata to the command_logs table.

        Logging failures are ignored so command execution remains uninterrupted.
        """

        database = getattr(self.context, "database", None)
        if not database:
            return

        try:
            database.execute(
                """
                INSERT INTO command_logs (
                    command_text,
                    command_root,
                    status,
                    response_text,
                    error_text,
                    duration_ms
                )
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (command_text, command_root, status, response_text, error_text, duration_ms),
            )
        except Exception as log_error:
            if self.logger:
                self.logger.warning(f"Failed to write command log: {log_error}")

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
        for _, handler in self.handlers.items():
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

        started = time.perf_counter()
        raw = (text or "").strip()
        parts = raw.split()

        if not parts:
            response = self._invalid("")
            duration_ms = int((time.perf_counter() - started) * 1000)
            self._logCommand(raw, "", "invalid", duration_ms, response_text=response)
            return response

        root = parts[0].lstrip("/").lower()

        try:
            command = self.commands.get(root)
            if command:
                response = command.execute(parts[1:])
                duration_ms = int((time.perf_counter() - started) * 1000)
                self._logCommand(raw, root, "success", duration_ms, response_text=response)
                return response

            handler = self.handlers.get(root)
            if handler:
                response = handler.handle(parts[1:], original=text)
                duration_ms = int((time.perf_counter() - started) * 1000)
                self._logCommand(raw, root, "success", duration_ms, response_text=response)
                return response

            if self.logger:
                self.logger.warning(f"Unknown command: {root}")

            response = self._invalid(text)
            duration_ms = int((time.perf_counter() - started) * 1000)
            self._logCommand(raw, root, "invalid", duration_ms, response_text=response)
            return response

        except Exception as error:
            duration_ms = int((time.perf_counter() - started) * 1000)
            self._logCommand(raw, root, "error", duration_ms, error_text=str(error))
            raise

