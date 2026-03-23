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
        from modules.commands.historyCommands.historyCommandHandler import HistoryCommandHandler
        from modules.commands.memoryCommands.memoryCommandHandler import MemoryCommandHandler
        from modules.commands.systemCommands.systemCommandHandler import SystemCommandHandler

        context.debugCommandHandler = DebugCommandHandler(context)
        context.configCommandHandler = ConfigCommandHandler(context)
        context.historyCommandHandler = HistoryCommandHandler(context)
        context.memoryCommandHandler = MemoryCommandHandler(context)
        context.systemCommandHandler = SystemCommandHandler(context)


        # --------------------------------------------------
        # Commands
        # --------------------------------------------------
        from modules.commands.helpCommand import HelpCommand
        from modules.commands.statusCommand import StatusCommand
        from modules.commands.versionCommand import VersionCommand
        from modules.commands.configCommands.configReloadCommand import ConfigReloadCommand
        from modules.commands.configCommands.configGetCommand import ConfigGetCommand
        from modules.commands.configCommands.configSetCommand import ConfigSetCommand
        from modules.commands.configCommands.configValidateCommand import ConfigValidateCommand
        from modules.commands.debugCommands.databaseDebugCommands import DatabaseDebugCommand
        from modules.commands.debugCommands.llmDebugCommand import LLMDebugCommand
        from modules.commands.debugCommands.memoryDebugCommands import MemoryDebugCommand
        from modules.commands.debugCommands.runtimeDebugCommand import RuntimeDebugCommand
        from modules.commands.historyCommands.historyClearCommand import HistoryClearCommand
        from modules.commands.historyCommands.historyShowCommand import HistoryShowCommand
        from modules.commands.memoryCommands.memoryClearCommand import MemoryClearCommand
        from modules.commands.memoryCommands.memoryExportCommand import MemoryExportCommand
        from modules.commands.memoryCommands.memoryGetCommand import MemoryGetCommand
        from modules.commands.memoryCommands.memoryImportCommand import MemoryImportCommand
        from modules.commands.memoryCommands.memoryListCommand import MemoryListCommand
        from modules.commands.memoryCommands.memoryRemoveCommand import MemoryRemoveCommand
        from modules.commands.memoryCommands.memorySearchCommand import MemorySearchCommand
        from modules.commands.memoryCommands.memorySetCommand import MemorySetCommand
        from modules.commands.systemCommands.modulesCommand import ModulesCommand
        from modules.commands.systemCommands.restartCommand import RestartCommand
        from modules.commands.systemCommands.shutdownCommand import ShutdownCommand
        from modules.commands.systemCommands.tasksCommand import TasksCommand

        HelpCommand(context)
        StatusCommand(context)
        VersionCommand(context)
        ConfigGetCommand(context)
        ConfigReloadCommand(context)
        ConfigSetCommand(context)
        ConfigValidateCommand(context)
        DatabaseDebugCommand(context)
        LLMDebugCommand(context)
        MemoryDebugCommand(context)
        RuntimeDebugCommand(context)
        HistoryClearCommand(context)
        HistoryShowCommand(context)
        MemoryClearCommand(context)
        MemoryExportCommand(context)
        MemoryGetCommand(context)
        MemoryImportCommand(context)
        MemoryListCommand(context)
        MemoryRemoveCommand(context)
        MemorySearchCommand(context)
        MemorySetCommand(context)
        ModulesCommand(context)
        RestartCommand(context)
        ShutdownCommand(context)
        TasksCommand(context)


        # --------------------------------------------------
        # Complete
        # --------------------------------------------------
        if self.logger:
            self.logger.info("Command registry initialized successfully.")
