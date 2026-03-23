"""Windows runtime bootstrap for Aura desktop execution.

This module builds and tears down a fully initialized RuntimeContext for
the Windows desktop interface. It mirrors the CLI startup sequence but is
resilient to partial configuration/runtime failures so the GUI can still
open in degraded mode.
"""

import os
from types import SimpleNamespace
from pathlib import Path

from config.configLoader import ConfigLoader
from core.interface.io.inputManager import InputManager
from core.interface.io.outputManager import OutputManager
from core.router.intentRouter import IntentRouter
from core.router.interpreter import Interpreter
from core.runtime.logger import AuraLogger
from core.runtime.moduleLoader import ModuleLoader
from core.runtime.runtimeContext import RuntimeContext
from core.threading.events.eventManager import EventManager
from core.threading.scheduler.scheduler import Scheduler
from core.threading.tasks.taskManager import TaskManager
from core.threading.threadingManager import ThreadingManager
from modules.database.mysql.mysqlDatabase import MySQLDatabase
from modules.llm.conversationHistory import ConversationHistory
from modules.llm.llmHandler import LLMHandler
from modules.llm.memoryManager import MemoryManager

REQUIRED_CONFIG_KEYS = (
    "llm.endpoint",
    "llm.model",
    "database.host",
    "database.port",
    "database.name",
    "database.user",
    "database.password",
)

ENV_KEY_MAP = {
    "database.host": "DB_HOST",
    "database.port": "DB_PORT",
    "database.name": "DB_NAME",
    "database.user": "DB_USER",
    "database.password": "DB_PASSWORD",
    "llm.endpoint": "LLM_ENDPOINT",
    "llm.model": "LLM_MODEL",
}

DEFAULT_CONFIG_TEMPLATE = """llm:
  model: llama3.1:8b
  endpoint: http://localhost:11434/api/generate

  history:
    enabled: true
    limit: 25

  memory:
    enabled: true

database:
  host: localhost
  port: 3306
  name: change_me
  user: change_me
  password: change_me

threading:
  max_threads: 10
"""


class SafeFallbackConfig:
    """Minimal config backend used when `config.yml` cannot be loaded."""

    def __init__(self):
        """Initialize fallback config from environment variables and defaults."""

        self._data = {
            "database": {
                "host": os.getenv("DB_HOST", "127.0.0.1"),
                "port": int(os.getenv("DB_PORT", "3306")),
                "name": os.getenv("DB_NAME", "aura"),
                "user": os.getenv("DB_USER", "root"),
                "password": os.getenv("DB_PASSWORD", ""),
            },
            "llm": {
                "endpoint": os.getenv("LLM_ENDPOINT", "http://127.0.0.1:11434/api/generate"),
                "model": os.getenv("LLM_MODEL", "llama3.1:8b"),
                "history": {
                    "enabled": True,
                    "limit": 25,
                },
                "memory": {
                    "enabled": True,
                },
            },
        }

    def get(self, key: str, default=None):
        """Return a config value using dot-notation lookup."""

        value = self._data
        for part in key.split("."):
            if not isinstance(value, dict) or part not in value:
                return default
            value = value[part]
        return value

    def require(self, key: str):
        """Return a required config value and raise if missing."""

        value = self.get(key)
        if value is None:
            raise KeyError(f"Missing required config value: {key}")
        return value

    def reload(self):
        """Reload fallback config.

        This is a no-op because fallback config is synthesized in memory.
        """

    def asDict(self):
        """Return the in-memory config dictionary."""

        return self._data


class UnavailableDatabase:
    """Database adapter used when MySQL startup fails.

    This adapter preserves the expected database interface so command and
    runtime layers can continue running without hard failures.
    """

    def __init__(self, reason: str):
        """Initialize unavailable database metadata and disconnected state.

        Args:
            reason (str):
                Human-readable reason why MySQL startup failed.
        """

        self.reason = reason
        self.database_name = os.getenv("DB_NAME", "aura")
        self.connection = SimpleNamespace(is_connected=lambda: False)

    def connect(self):
        """No-op connection method for unavailable database mode."""

    def initialize(self):
        """No-op schema initialization method for unavailable database mode."""

    def close(self):
        """No-op close method for unavailable database mode."""

    def execute(self, _query: str, _params=()):
        """Ignore writes while database is unavailable."""

        return None

    def fetchOne(self, query: str, _params=()):
        """Return minimal safe responses for health checks.

        Args:
            query (str):
                SQL query text.
        """

        normalized = " ".join((query or "").lower().split())
        if normalized.startswith("select 1 as ok"):
            return {"ok": 0}
        return None

    def fetchAll(self, _query: str, _params=()):
        """Return no rows while database is unavailable."""

        return []


class InMemoryConversationHistory:
    """Conversation history fallback used when DB-backed history is unavailable."""

    def __init__(self):
        """Initialize in-memory message storage."""

        self._messages = []

    def logMessage(self, author: str, content: str):
        """Append a message to in-memory history storage."""

        self._messages.append((author, content))

    def add(self, role: str, content: str):
        """Append a message using role/content naming from primary history API."""

        self._messages.append((role, content))

    def getRecentMessages(self, limit: int = 15):
        """Return recent messages in chronological order."""

        return self._messages[-limit:]

    def clear(self):
        """Clear all in-memory conversation messages."""

        self._messages.clear()


class InMemoryMemoryManager:
    """Long-term memory fallback used when DB-backed memory is unavailable."""

    def __init__(self):
        """Initialize in-memory memory dictionary."""

        self._memory = {}

    def setMemory(self, key: str, value: str, importance: int = 1):
        """Store a memory key/value pair in process memory.

        Args:
            key (str):
                Memory key.
            value (str):
                Memory value.
            importance (int):
                Stored for interface compatibility.
        """

        self._memory[key] = str(value)

    def getMemory(self):
        """Return all in-memory memory values."""

        return dict(self._memory)

    def get(self, key: str):
        """Return one in-memory memory value by key."""

        return self._memory.get(key)

    def delete(self, key: str):
        """Delete one memory key if it exists."""

        self._memory.pop(key, None)

    def clear(self):
        """Clear all memory keys from process memory."""

        self._memory.clear()

    def learnFromMessage(self, _text: str):
        """No-op learning method for compatibility with LLM handler."""


class DegradedLLMHandler:
    """LLM fallback used when live LLM handler cannot be initialized."""

    def __init__(self, context, reason: str):
        """Initialize degraded handler with explicit failure reason.

        Args:
            context (RuntimeContext):
                Runtime context containing config and logger references.
            reason (str):
                Failure reason used for diagnostics and status messaging.
        """

        self.context = context
        self.reason = reason
        self.endpoint = context.config.get("llm.endpoint", "unavailable")
        self.model = context.config.get("llm.model", "unavailable")
        self.logger = context.logger.getChild("LLM") if context.logger else None

    def generateResponse(self, _userInput: str) -> str:
        """Return a consistent response while LLM services are unavailable."""

        return (
            "LLM is currently unavailable. "
            f"Startup fallback is active: {self.reason}"
        )


def _setConfigValue(config, key: str, value):
    """Set a dot-path config value when underlying config backend is mutable."""

    if hasattr(config, "asDict"):
        data = config.asDict()
    elif hasattr(config, "data"):
        data = config.data
    elif hasattr(config, "_data"):
        data = config._data
    else:
        return False

    parts = key.split(".")
    node = data
    for part in parts[:-1]:
        if part not in node or not isinstance(node[part], dict):
            node[part] = {}
        node = node[part]
    node[parts[-1]] = value
    return True


def _findMissingRequiredConfigKeys(config):
    """Return required config keys that are missing or empty."""

    missing = []
    for key in REQUIRED_CONFIG_KEYS:
        value = config.get(key, None)
        if value is None:
            missing.append(key)
            continue
        if isinstance(value, str) and value.strip().lower() == "change_me":
            missing.append(key)
            continue
        if key == "database.password":
            # Empty passwords can be valid in local/dev environments.
            continue
        if isinstance(value, str) and value.strip() == "":
            missing.append(key)
    return missing


def _overlayMissingConfigFromEnv(config):
    """Populate missing required config keys from environment overrides."""

    applied = []
    missing = _findMissingRequiredConfigKeys(config)
    for key in missing:
        env_key = ENV_KEY_MAP.get(key)
        if not env_key:
            continue
        env_value = os.getenv(env_key)
        if env_value is None or env_value.strip() == "":
            continue

        cast_value = env_value
        if key == "database.port":
            try:
                cast_value = int(env_value)
            except ValueError:
                continue

        if _setConfigValue(config, key, cast_value):
            applied.append(key)

    return applied


def _getLogger(context: RuntimeContext):
    """Return the windows runtime logger if logging is available."""

    if context.logger:
        return context.logger.getChild("WindowsRuntime")
    return None


def ensureConfigFileExists(config_path: str = "config.yml"):
    """Create or migrate the primary config file when it is missing.

    Args:
        config_path (str):
            Path to Aura's primary YAML config file.

    Returns:
        bool:
            `True` if a new file was created, otherwise `False`.
    """

    path = Path(config_path)
    if path.exists():
        return False

    legacy_path = Path("config") / "config.yml"
    if legacy_path.exists():
        path.write_text(legacy_path.read_text(encoding="utf-8"), encoding="utf-8")
        return True

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(DEFAULT_CONFIG_TEMPLATE, encoding="utf-8")
    return True


def _createConfig(context: RuntimeContext):
    """Create runtime config, falling back to synthesized defaults on failure."""

    logger = _getLogger(context)
    try:
        created = ensureConfigFileExists()
        if created:
            if logger:
                logger.warning("config.yml was missing. Created or migrated the active config file.")
            warnings = getattr(context, "bootstrapWarnings", [])
            warnings.append("Generated or migrated root config.yml.")
            context.bootstrapWarnings = warnings
    except Exception as error:
        if logger:
            logger.error(f"Failed to create config.yml: {error}")
        warnings = getattr(context, "bootstrapWarnings", [])
        warnings.append(f"Config creation failed: {error}")
        context.bootstrapWarnings = warnings

    try:
        return ConfigLoader(context)
    except Exception as error:
        if logger:
            logger.error(f"Config load failed. Using fallback config: {error}")
        warnings = getattr(context, "bootstrapWarnings", [])
        warnings.append(f"Config fallback active: {error}")
        context.bootstrapWarnings = warnings
        return SafeFallbackConfig()


def _createDatabase(context: RuntimeContext):
    """Create database service, falling back to unavailable adapter on failure."""

    logger = _getLogger(context)
    try:
        database = MySQLDatabase(context)
        database.connect()
        database.initialize()
        return database
    except Exception as error:
        if logger:
            logger.error(f"MySQL startup failed. Using degraded database mode: {error}")
        warnings = getattr(context, "bootstrapWarnings", [])
        warnings.append(f"Database unavailable: {error}")
        context.bootstrapWarnings = warnings
        return UnavailableDatabase(str(error))


def _createMemoryManager(context: RuntimeContext):
    """Create memory manager with fallback when primary manager cannot start."""

    logger = _getLogger(context)
    if isinstance(context.database, UnavailableDatabase):
        if logger:
            logger.warning("Using in-memory memory manager because database is unavailable.")
        return InMemoryMemoryManager()

    try:
        return MemoryManager(context)
    except Exception as error:
        if logger:
            logger.error(f"Memory manager startup failed. Using in-memory fallback: {error}")
        warnings = getattr(context, "bootstrapWarnings", [])
        warnings.append(f"Memory manager fallback active: {error}")
        context.bootstrapWarnings = warnings
        return InMemoryMemoryManager()


def _createConversationHistory(context: RuntimeContext):
    """Create conversation history with fallback when DB-backed history fails."""

    logger = _getLogger(context)
    if isinstance(context.database, UnavailableDatabase):
        if logger:
            logger.warning("Using in-memory conversation history because database is unavailable.")
        return InMemoryConversationHistory()

    try:
        return ConversationHistory(context)
    except Exception as error:
        if logger:
            logger.error(
                f"Conversation history startup failed. Using in-memory fallback: {error}"
            )
        warnings = getattr(context, "bootstrapWarnings", [])
        warnings.append(f"Conversation history fallback active: {error}")
        context.bootstrapWarnings = warnings
        return InMemoryConversationHistory()


def _createLLMHandler(context: RuntimeContext):
    """Create LLM handler with degraded fallback when live handler fails."""

    logger = _getLogger(context)
    try:
        return LLMHandler(context)
    except Exception as error:
        if logger:
            logger.error(f"LLM startup failed. Using degraded LLM handler: {error}")
        warnings = getattr(context, "bootstrapWarnings", [])
        warnings.append(f"LLM fallback active: {error}")
        context.bootstrapWarnings = warnings
        return DegradedLLMHandler(context, str(error))


def createRuntimeContext() -> RuntimeContext:
    """Create and initialize the runtime context for the Windows GUI.

    Returns:
        RuntimeContext:
            Initialized runtime context. On partial startup failures, degraded
            fallback components are injected so the GUI remains usable.
    """

    context = RuntimeContext()

    # Logger
    context.logger = AuraLogger()

    # Bootstrap warnings are shown only in logs for now and can be surfaced in GUI later.
    context.bootstrapWarnings = []

    # Config
    context.config = _createConfig(context)
    applied_from_env = _overlayMissingConfigFromEnv(context.config)
    if applied_from_env:
        context.bootstrapWarnings.append(
            "Config overrides applied from environment: "
            + ", ".join(applied_from_env)
        )

    missing_config_keys = _findMissingRequiredConfigKeys(context.config)
    if missing_config_keys:
        logger = _getLogger(context)
        if logger:
            logger.warning(
                "Missing required config keys detected. "
                "Startup will pause for interactive recovery."
            )
        context.missingConfigKeys = missing_config_keys
        context.should_exit = False
        return context

    # Threading
    context.threader = ThreadingManager(context)
    context.eventManager = EventManager(context)
    context.taskManager = TaskManager(context)
    context.scheduler = Scheduler(context)

    # Database
    context.database = _createDatabase(context)

    # LLM Subsystems
    context.memoryManager = _createMemoryManager(context)
    context.conversationHistory = _createConversationHistory(context)
    context.llm = _createLLMHandler(context)

    # Router
    context.interpreter = Interpreter(context)
    context.intentRouter = IntentRouter(context)

    # IO
    context.inputManager = InputManager(context)
    context.outputManager = OutputManager(context)

    # Module Loader
    try:
        loader = ModuleLoader(context)
        loader.loadModules()
    except Exception as error:
        logger = _getLogger(context)
        if logger:
            logger.error(f"Module loading failed. Continuing in reduced mode: {error}")
        context.bootstrapWarnings.append(f"Module loading failed: {error}")

    # Runtime flags
    context.should_exit = False
    context.missingConfigKeys = []

    return context


def startup(context: RuntimeContext):
    """Run startup actions required before opening the GUI.

    Args:
        context (RuntimeContext):
            Runtime context created for desktop execution.
    """

    logger = _getLogger(context)
    if logger:
        logger.info("Starting Aura Windows runtime.")

    if context.scheduler:
        context.scheduler.start()


def shutdown(context: RuntimeContext):
    """Run shutdown actions required after closing the GUI.

    Args:
        context (RuntimeContext):
            Runtime context used during desktop execution.
    """

    logger = _getLogger(context)
    if logger:
        logger.info("Stopping Aura Windows runtime.")

    if context.scheduler:
        context.scheduler.stop()

    if context.database:
        context.database.close()
