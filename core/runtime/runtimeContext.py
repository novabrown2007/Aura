class RuntimeContext:
    """
    Central runtime container for the Aura assistant.

    The RuntimeContext acts as a dependency container for all major
    subsystems within Aura. It allows different components of the system
    (engine, modules, interfaces, database, etc.) to access shared services
    without creating circular imports.

    The engine initializes the RuntimeContext and populates its attributes
    during startup. Once initialized, the context is passed to modules and
    other systems so they can access the services they require.

    Example:
        context = RuntimeContext()
        context.logger = AuraLogger()
        context.database = MySQLDatabase()

        weather_module = WeatherModule(context)
    """

    def __init__(self):
        """
        Initialize an empty runtime context.

        All attributes start as None and are populated by the engine during
        system initialization.
        """

        # ----------------------------
        # Core Systems
        # ----------------------------

        self.engine = None
        """Reference to the main Aura Engine."""

        self.logger = None
        """Global logging system used across Aura."""

        # ----------------------------
        # Threading / Async Systems
        # ----------------------------

        self.threader = None
        """Main threading manager responsible for coordinating background systems."""

        self.eventManager = None
        """Event system used for pub/sub communication between modules."""

        self.scheduler = None
        """Scheduler responsible for timed or recurring tasks."""

        self.taskManager = None
        """Task manager responsible for running background jobs or async tasks."""

        # ----------------------------
        # Modules
        # ----------------------------

        self.modules: dict[str, object] = {}
        """
        Dictionary of loaded modules.

        Key:
            module name (str)

        Value:
            module instance
        """

        # ----------------------------
        # Database
        # ----------------------------

        self.database = None
        """Primary database interface used by Aura."""

        # ----------------------------
        # LLM System
        # ----------------------------

        self.llm = None
        """LLM handler responsible for model interaction."""

        self.conversationHistory = None
        """Stores active conversation context."""

        self.memoryManager = None
        """Handles long-term memory and user information."""

        # ----------------------------
        # Router
        # ----------------------------

        self.intentRouter = None
        """Routes interpreted intents to the appropriate module."""

        self.interpreter = None
        """Processes raw user input into structured intents."""

        # ----------------------------
        # Interfaces
        # ----------------------------

        self.inputManager = None
        """Handles input from user interfaces (text, speech, API, etc.)."""

        self.outputManager = None
        """Handles responses to user interfaces."""

        # ----------------------------
        # Config / Constants
        # ----------------------------

        self.config = None
        """Configuration dictionary loaded during startup."""

    # --------------------------------------------------
    # Module Management
    # --------------------------------------------------

    def registerModule(self, name: str, module):
        """
        Register a module with the runtime context.

        Modules should call this during initialization so the engine
        and other components can access them later.

        Args:
            name (str):
                Unique name of the module.

            module:
                The module instance being registered.
        """
        self.modules[name] = module

    def getModule(self, name: str):
        """
        Retrieve a module by name.

        Args:
            name (str):
                Name of the module.

        Returns:
            module or None:
                The module instance if it exists, otherwise None.
        """
        return self.modules.get(name)

    def require(self, name: str):
        """
        Retrieve a required runtime component.

        Raises an error if the component does not exist or has not
        been initialized.
        """

        if not hasattr(self, name):
            raise AttributeError(f"{name} is not a valid RuntimeContext attribute.")

        value = getattr(self, name)

        if value is None:
            raise RuntimeError(f"{name} has not been initialized.")

        return value

    # --------------------------------------------------
    # Debug Helpers
    # --------------------------------------------------

    def listModules(self):
        """
        List the names of all currently registered modules.

        Returns:
            list[str]: A list of module names.
        """
        return list(self.modules.keys())
