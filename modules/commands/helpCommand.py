from modules.commands.baseCommand import BaseCommand


class HelpCommand(BaseCommand):
    """
    Displays all available commands dynamically.

    Supports:
    - Full help listing: /help
    - Filtered help: /help <keyword>

    Filtering matches:
    - Full command path
    - Command name
    """

    name = "help"
    help_message = "Display this help message."

    def __init__(self, context):
        """
        Initialize the HelpCommand.

        Args:
            context (RuntimeContext):
                Global runtime context.
        """

        super().__init__(context)

        if context.logger:
            self.logger = context.logger.getChild("Commands.Help")

        # Register with root command handler
        context.commandHandler.registerCommand(self)

        if self.logger:
            self.logger.info("HelpCommand initialized")


    # --------------------------------------------------
    # Execution
    # --------------------------------------------------
    def execute(self, args: list[str]) -> str:
        """
        Generate dynamic help output.

        Args:
            args (list[str]):
                Optional filter argument.

        Returns:
            str:
                Formatted help message.
        """
        handler = self.context.require("commandHandler")
        commands = handler.getAllCommands()

        # Optional filtering
        filter_term = None
        if args:
            filter_term = args[0].lower()
            if self.logger:
                self.logger.debug(f"Filtering help with term: {filter_term}")
        lines = ["---------------HELP---------------"]
        for cmd in commands:
            full = cmd.full_command or f"/{cmd.name}"
            desc = cmd.help_message or "No description provided."

            # Apply filter if provided
            if filter_term:
                if filter_term not in full.lower() and filter_term not in cmd.name.lower():
                    continue
            lines.append(f"{full} --> {desc}")

        # Handle no matches
        if len(lines) == 1:
            return f'No commands found matching "{filter_term}".'
        return "\n".join(lines)
