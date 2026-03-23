class MemoryCommandHandler:
    """
    Handler for all /memory commands.
    """

    name = "memory"

    def __init__(self, context):
        self.context = context
        self.logger = None
        if context.logger:
            self.logger = context.logger.getChild("Commands.Memory")

        self.commands = {}

        if self.logger:
            self.logger.info("Initialized.")

        context.commandHandler.registerHandler(self.name, self)

    def _invalid(self, command: str) -> str:
        return (
            f'Command "{command}" is not a valid command. '
            f'For a list of valid commands, run "/help".'
        )

    def registerCommand(self, command):
        command.full_command = f"/{self.name} {command.name}"
        self.commands[command.name] = command
        if self.logger:
            self.logger.info(f"Registered memory command: {command.full_command}")

    def getCommands(self):
        return list(self.commands.values())

    def handle(self, parts: list[str], original: str = "") -> str:
        if not parts:
            return self._invalid(original)

        cmd_name = parts[0].lower()
        command = self.commands.get(cmd_name)
        if not command:
            if self.logger:
                self.logger.warning(f"Unknown memory command: {cmd_name}")
            return self._invalid(original)

        return command.execute(parts[1:])

