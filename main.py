"""
Aura Assistant - Main Entry Point

This file bootstraps the headless Aura runtime by creating the
RuntimeContext, initializing all core subsystems, loading backend modules,
and managing the application lifecycle.
"""

from core.runtime.runtimeContext import RuntimeContext
from core.runtime.datetimeUtils import DateTimeUtils
from core.runtime.logger import AuraLogger
from core.runtime.moduleLoader import ModuleLoader

from core.threading.threadingManager import ThreadingManager
from core.threading.events.eventManager import EventManager
from core.threading.tasks.taskManager import TaskManager
from core.threading.scheduler.scheduler import Scheduler
from core.autonomy import AutonomousTaskManager
from core.contextAwareness import ContextAwarenessManager
from core.observability import ObservabilityManager

from core.router.intentRouter import IntentRouter
from core.router.interpreter import Interpreter
from core.tools.toolExecutor import ToolExecutor
from core.tools.toolOrchestrator import ToolOrchestrator
from core.tools.toolRegistry import ToolRegistry

from modules.database.databaseFactory import createDatabaseWithFallback
from modules.home_automation.config import buildHomeAutomationConfig
from auraassistant.core.bridge import AuraBridgeClient

from modules.llm.manager.llmManager import LLMManager
from modules.llm.llmHandler import LLMHandler
from modules.llm.conversationHistory import ConversationHistory
from modules.llm.memoryManager import MemoryManager

from core.engine.engine import Engine

from config.configLoader import ConfigLoader


# --------------------------------------------------
# Startup
# --------------------------------------------------

def startup(context):
    """
    Perform system startup procedures.
    """

    logger = context.logger.getChild("Main")

    logger.info("Starting Aura.")

    if context.scheduler:
        context.scheduler.start()


# --------------------------------------------------
# Shutdown
# --------------------------------------------------

def shutdown(context):
    """
    Perform system shutdown procedures.
    """

    logger = context.logger.getChild("Main")

    logger.info("Shutting down Aura.")

    if context.scheduler:
        context.scheduler.stop()

    if context.moduleLoader:
        context.moduleLoader.shutdownModules()

    if context.llmManager:
        context.llmManager.shutdown()

    if context.database:
        context.database.close()


# --------------------------------------------------
# Runtime Builder
# --------------------------------------------------

def buildRuntimeContext():
    """
    Build and return a fully initialized Aura runtime context.
    """

    context = RuntimeContext()

    # Logger
    context.logger = AuraLogger()

    # Shared Utilities
    context.dtUtil = DateTimeUtils

    # Config
    context.config = ConfigLoader(context)
    context.homeAutomationConfig = buildHomeAutomationConfig(context)

    # Threading
    context.threader = ThreadingManager(context)
    context.eventManager = EventManager(context)
    context.taskManager = TaskManager(context)
    context.scheduler = Scheduler(context)
    context.observability = ObservabilityManager(context)
    context.autonomousTasks = AutonomousTaskManager(context)
    context.contextAwareness = ContextAwarenessManager(context)

    # Bridge Protocol
    context.bridgeClient = AuraBridgeClient(context)
    context.auraBridgeClient = context.bridgeClient
    try:
        context.bridgeClient.connect()
    except Exception as error:
        if context.logger:
            context.logger.warning(f"Bridge protocol client could not connect: {error}")

    # Tools
    context.toolRegistry = ToolRegistry(context)
    context.toolExecutor = ToolExecutor(context)
    context.toolOrchestrator = ToolOrchestrator(context)

    # Database
    context.database = createDatabaseWithFallback(context)

    # LLM
    context.llmManager = LLMManager(context)
    context.memoryManager = MemoryManager(context)
    context.conversationHistory = ConversationHistory(context)
    context.llm = LLMHandler(context)

    # Router
    context.interpreter = Interpreter(context)
    context.intentRouter = IntentRouter(context)

    # Module Loader
    loader = ModuleLoader(context)
    loader.loadModules()

    # Engine
    context.engine = Engine(context)
    return context


# --------------------------------------------------
# Main Entry Point
# --------------------------------------------------

def main():
    """
    Initialize Aura and keep running until no restart is requested.
    """

    while True:
        context = buildRuntimeContext()
        startup(context)

        try:
            context.engine.run()
        finally:
            shutdown(context)
            if context.logger:
                context.logger.close()

        if not getattr(context, "restart_requested", False):
            break


if __name__ == "__main__":
    main()
