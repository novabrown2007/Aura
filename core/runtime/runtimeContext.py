"""Core implementation for `runtimeContext` in the Aura assistant project."""

class RuntimeContext:
    """
    Central runtime container for the Aura assistant.

    The RuntimeContext acts as a dependency container for all major
    subsystems within Aura. It allows different components of the system
    (engine, modules, database, etc.) to access shared services
    without creating circular imports.

    The engine initializes the RuntimeContext and populates its attributes
    during startup. Once initialized, the context is passed to modules and
    other systems so they can access the services they require.

    Example:
        context = RuntimeContext()
        context.logger = Logger("Aura")
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

        self.dtUtil = None
        """Shared datetime formatting utility used across runtime modules."""

        self.system = None
        """System lifecycle module used for shutdown, restart, and reload actions."""

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

        self.autonomousTasks = None
        """Persistent autonomous task manager for scheduled/event-driven work."""

        self.contextAwareness = None
        """Current environment context and signal change detector."""

        self.observability = None
        """Runtime diagnostics and execution trace service."""

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

        self.moduleLoader = None
        """Dynamic module loader and plugin registry."""

        self.toolRegistry = None
        """Registry of deterministic tools exposed by loaded modules."""

        self.toolExecutor = None
        """Executor responsible for validating and running registered tools."""

        self.toolOrchestrator = None
        """Core tool schema, validation, and execution orchestration service."""

        self.bridgeClient = None
        """Aura Protocol client used to communicate with the home automation bridge."""

        self.auraBridgeClient = None
        """Alias for the Aura Protocol bridge client."""

        self.bridgeStateCache = None
        """Cached assistant-facing bridge state."""

        self.bridgeSessionManager = None
        """Assistant session manager for bridge context synchronization."""

        self.bridgeSubscriptionManager = None
        """Bridge subscription manager for assistant categories."""

        self.bridgeNotificationManager = None
        """Assistant notification manager for bridge events."""

        self.bridgeStreamManager = None
        """Stream metadata manager for assistant-facing stream lifecycle."""

        self.bridgeRouter = None
        """Message router for assistant-facing bridge events."""

        self.voiceManager = None
        """Local push-to-talk speech transcription manager."""

        self.pushToTalkManager = None
        """Held push-to-talk voice conversation loop manager."""

        self.wakeWordManager = None
        """Passive local wake word activation manager."""

        self.developerUI = None
        """Developer/operator UI interface manager."""

        self.textToSpeech = None
        """Local speech synthesis engine for assistant responses."""

        self.audioPlayer = None
        """Local audio playback backend for synthesized speech."""

        self.speechQueue = None
        """Serialized assistant speech queue."""

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

        self.llmManager = None
        """Provider-neutral manager responsible for all model access."""

        self.conversationHistory = None
        """Stores active conversation context."""

        self.memoryManager = None
        """Handles long-term memory and user information."""

        self.memoryStore = None
        """Persistent structured memory storage backend."""

        # ----------------------------
        # Router
        # ----------------------------

        self.intentRouter = None
        """Routes interpreted intents to the appropriate module."""

        self.interpreter = None
        """Processes raw user input into structured intents."""

        # ----------------------------
        # Config / Constants
        # ----------------------------

        self.config = None
        """Configuration dictionary loaded during startup."""

        self.should_exit = False
        """Signal used by modules to stop the active runtime loop."""

        self.restart_requested = False
        """Signal used to request a full runtime restart after shutdown completes."""

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
