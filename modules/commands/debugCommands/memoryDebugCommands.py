from modules.commands.baseCommand import BaseCommand


class MemoryDebugCommand(BaseCommand):
    """
    Debug command for interacting with Aura's long-term memory.

    Supported commands:
        /debug memory list
        /debug memory clear
        /debug memory add <key> "<value>"
        /debug memory remove <key>
    """

    name = "memory"
    help_message = "Manage memory (list, clear, add, remove)."

    def __init__(self, context):
        """
        Initialize the MemoryDebugCommand.

        Args:
            context (RuntimeContext):
                Global runtime context.
        """
        super().__init__(context)
        # Logger
        if context.logger:
            self.logger = context.logger.getChild("Commands.Debug.Memory")
        # Register with DebugCommandHandler
        context.debugCommandHandler.registerCommand(self)
        if self.logger:
            self.logger.info("Initialized.")


    # --------------------------------------------------
    # Execution
    # --------------------------------------------------
    def execute(self, args: list[str]) -> str:
        """
        Execute memory debug command.

        Args:
            args (list[str]):
                Command arguments.

        Returns:
            str:
                Result message.
        """
        memory = self.context.require("memoryManager")


        # --------------------------------
        # No args → usage
        # --------------------------------
        if not args:
            return self._usage()
        action = args[0].lower()


        # --------------------------------
        # LIST
        # --------------------------------
        if action == "list":
            data = memory.getMemory()
            if not data:
                return "Memory is empty."
            lines = ["------ MEMORY ------"]
            for key, value in data.items():
                lines.append(f"{key} = {value}")
            return "\n".join(lines)


        # --------------------------------
        # CLEAR
        # --------------------------------
        if action == "clear":
            memory.clear()
            if self.logger:
                self.logger.warning("Memory cleared via debug command")
            return "Memory cleared."


        # --------------------------------
        # ADD
        # --------------------------------
        if action == "add":
            if len(args) < 3:
                return 'Usage: /debug memory add <key> "<value>"'
            key = args[1]
            # Join remaining args for value (supports spaces)
            raw_value = " ".join(args[2:]).strip()
            # Remove quotes if present
            if raw_value.startswith('"') and raw_value.endswith('"'):
                value = raw_value[1:-1]
            else:
                value = raw_value
            memory.setMemory(key, value)
            if self.logger:
                self.logger.info(f"Memory added manually: {key} = {value}")
            return f'Memory added: {key} = "{value}"'


        # --------------------------------
        # REMOVE
        # --------------------------------
        if action == "remove":
            if len(args) < 2:
                return "Usage: /debug memory remove <key>"
            key = args[1]
            existing = memory.get(key)
            if existing is None:
                return f'Memory key "{key}" does not exist.'
            memory.delete(key)
            if self.logger:
                self.logger.info(f"Memory removed manually: {key}")
            return f'Memory removed: {key}'


        # --------------------------------
        # UNKNOWN ACTION
        # --------------------------------
        return self._usage()


    # --------------------------------------------------
    # Utility
    # --------------------------------------------------
    def _usage(self) -> str:
        """
        Return usage instructions.

        Returns:
            str
        """
        return (
            "Usage:\n"
            "/debug memory list\n"
            "/debug memory clear\n"
            '/debug memory add <key> "<value>"\n'
            "/debug memory remove <key>"
        )
