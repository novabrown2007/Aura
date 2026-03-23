class CommandRegistry:
    """
    Initializes and registers all command handlers and commands.

    This class acts as the central wiring point for the command system.
    It is loaded once during startup and is responsible for:

    - Creating the root CommandHandler
    - Registering all sub-handlers (debug, system, etc.)
    - Instantiating commands so they self-register

    This ensures main.py never needs to be modified when adding commands.
    """

    def __init__(self, context):
        """
        Initialize the command registry.

        Args:
            context (RuntimeContext):
                Global runtime context.
        """
        self.context = context
        # Logger
        self.logger = None
        if context.logger:
            self.logger = context.logger.getChild("Commands.Registry")
        if self.logger:
            self.logger.info("Initializing command registry...")


        # --------------------------------------------------
        # Root Command Handler
        # --------------------------------------------------
        from modules.commands.commandHandler import CommandHandler
        context.commandHandler = CommandHandler(context)


        # --------------------------------------------------
        # Sub-Handlers
        # --------------------------------------------------
        from modules.commands.debugCommands.debugCommandHandler import DebugCommandHandler
        from modules.commands.configCommands.configCommandHandler import ConfigCommandHandler
        from modules.commands.systemCommands.systemCommandHandler import SystemCommandHandler

        context.debugCommandHandler = DebugCommandHandler(context)
        context.configCommandHandler = ConfigCommandHandler(context)
        context.systemCommandHandler = SystemCommandHandler(context)


        # --------------------------------------------------
        # Commands
        # --------------------------------------------------
        from modules.commands.helpCommand import HelpCommand
        from modules.commands.configCommands.configReloadCommand import ConfigReloadCommand
        from modules.commands.debugCommands.databaseDebugCommands import DatabaseDebugCommand
        from modules.commands.debugCommands.memoryDebugCommands import MemoryDebugCommand
        from modules.commands.systemCommands.shutdownCommand import ShutdownCommand

        HelpCommand(context)
        ConfigReloadCommand(context)
        DatabaseDebugCommand(context)
        MemoryDebugCommand(context)
        ShutdownCommand(context)


        # --------------------------------------------------
        # Complete
        # --------------------------------------------------
        if self.logger:
            self.logger.info("Command registry initialized successfully.")
