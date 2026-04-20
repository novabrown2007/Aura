"""
Aura Assistant - Main Entry Point

This file bootstraps the Aura system by creating the RuntimeContext,
initializing all core subsystems, and managing the application lifecycle.

Lifecycle Flow:

    main()
        ↓
    RuntimeContext created
        ↓
    Core systems initialized
        ↓
    Modules loaded
        ↓
    startup()
        ↓
    Engine.run()
        ↓
    shutdown()
"""

from core.runtime.runtimeContext import RuntimeContext
from core.runtime.datetimeUtils import DateTimeUtils
from core.runtime.logger import AuraLogger
from core.runtime.moduleLoader import ModuleLoader

from core.threading.threadingManager import ThreadingManager
from core.threading.events.eventManager import EventManager
from core.threading.tasks.taskManager import TaskManager
from core.threading.scheduler.scheduler import Scheduler

from core.router.intentRouter import IntentRouter
from core.router.interpreter import Interpreter

from core.interface.io.inputManager import InputManager
from core.interface.io.outputManager import OutputManager

from modules.database.databaseFactory import createDatabaseWithFallback

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

    if context.database:
        context.database.close()


# --------------------------------------------------
# Main Entry Point
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

    # Threading
    context.threader = ThreadingManager(context)
    context.eventManager = EventManager(context)
    context.taskManager = TaskManager(context)
    context.scheduler = Scheduler(context)

    # Database
    context.database = createDatabaseWithFallback(context)

    # LLM
    context.memoryManager = MemoryManager(context)
    context.conversationHistory = ConversationHistory(context)
    context.llm = LLMHandler(context)

    # Router
    context.interpreter = Interpreter(context)
    context.intentRouter = IntentRouter(context)

    # IO
    context.inputManager = InputManager(context)
    context.outputManager = OutputManager(context)

    # Module Loader
    loader = ModuleLoader(context)
    loader.loadModules()

    # Engine
    context.engine = Engine(context)
    return context


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
