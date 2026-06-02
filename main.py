"""
Aura Assistant - Main Entry Point

This file bootstraps the headless Aura runtime by creating the
RuntimeContext, initializing all core subsystems, loading backend modules,
and managing the application lifecycle.
"""

import time

from core.runtime.runtimeContext import RuntimeContext
from core.runtime.datetimeUtils import DateTimeUtils
from core.modules.moduleManager import ModuleManager

from core.threading.threadingManager import ThreadingManager
from core.threading.events.eventManager import EventManager
from core.tasks.taskManager import TaskManager
from core.threading.scheduler.scheduler import Scheduler
from core.eventBus.autonomy import AutonomousTaskManager
from modules.llm.contextAwareness import ContextAwarenessManager
from core.runtime.observability import ObservabilityManager
from core.interruption import InterruptionManager
from assistant.personality import PersonalityManager
from assistant.personality.handlers import PersonalityEventHandler
from assistant.notifications import NotificationManager
from assistant.responses import ResponseManager
from assistant.safety import SafetyManager
from assistant.conversation import ConversationManager
from assistant.execution import ExecutionManager
from core.voice import VoiceManager

from core.router.intentRouter import IntentRouter
from core.router.interpreter import Interpreter
from core.tools.toolExecutor import ToolExecutor
from core.tools.toolOrchestrator import ToolOrchestrator
from core.tools.toolRegistry import ToolRegistry

from modules.database.databaseFactory import createDatabaseWithFallback
from modules.home_automation.config import buildHomeAutomationConfig
from modules.home_automation.managerConnection import HomeAutomationManagerConnection
from bridge import AuraBridgeClient

from modules.llm.manager.llmManager import LLMManager
from modules.llm.llmHandler import LLMHandler
from assistant.conversation import ConversationHistory
from assistant.memory import MemoryManager

from core.engine import Engine

from config.configLoader import ConfigLoader
from modules.logger.logger import Logger


# --------------------------------------------------
# Startup
# --------------------------------------------------

def startup(context):
    """
    Perform system startup procedures.
    """

    logger = context.logger.getChild("Main")

    logger.info("Starting Aura.")

    if getattr(context, "taskManager", None):
        context.taskManager.start()

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

    if getattr(context, "taskManager", None):
        context.taskManager.shutdown()

    if context.scheduler:
        context.scheduler.stop()

    if context.moduleLoader:
        context.moduleLoader.shutdownModules()

    if context.llmManager:
        context.llmManager.shutdown()

    if context.memoryManager and hasattr(context.memoryManager, "shutdown"):
        context.memoryManager.shutdown()

    if getattr(context, "responseManager", None) and hasattr(context.responseManager, "shutdown"):
        context.responseManager.shutdown()

    if getattr(context, "safetyManager", None) and hasattr(context.safetyManager, "shutdown"):
        context.safetyManager.shutdown()

    if getattr(context, "executionManager", None) and hasattr(context.executionManager, "shutdown"):
        context.executionManager.shutdown()

    if getattr(context, "voiceManager", None) and hasattr(context.voiceManager, "shutdown"):
        context.voiceManager.shutdown()

    if getattr(context, "notificationManager", None):
        context.notificationManager.shutdown()

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

    # Shared Utilities
    context.dtUtil = DateTimeUtils

    # Config
    context.config = ConfigLoader(context)
    context.logger = Logger("Aura", config=context.config)
    context.config.logger = context.logger.getChild("Config")
    context.config.logger.info("Configuration loaded.")
    context.homeAutomationConfig = buildHomeAutomationConfig(context)
    context.homeAutomationManagerClient = HomeAutomationManagerConnection(
        context.homeAutomationConfig.manager,
        logger=context.logger.getChild("HomeAutomationManager"),
    )

    manager_config = context.homeAutomationConfig.manager
    if manager_config.auto_start:
        try:
            context.homeAutomationManagerClient.ensureRunning()
        except Exception as error:
            context.logger.warning(f"Home Automation Manager could not be started automatically: {error}")

    if manager_config.auto_start_bridge:
        try:
            context.homeAutomationManagerClient.ensureRunning()
            context.homeAutomationManagerClient.start(manager_config.bridge_target)
        except Exception as error:
            context.logger.warning(f"Home Automation bridge could not be started through the manager: {error}")

    # Threading
    context.threader = ThreadingManager(context)
    context.eventManager = EventManager(context)
    context.taskManager = TaskManager(context)
    context.scheduler = Scheduler(context)
    context.interruptionManager = InterruptionManager(context).initialize(context)
    context.observability = ObservabilityManager(context)
    context.autonomousTasks = AutonomousTaskManager(context)
    context.contextAwareness = ContextAwarenessManager(context)
    context.safetyManager = SafetyManager(context)

    # Bridge Protocol
    context.bridgeClient = AuraBridgeClient(context)
    context.auraBridgeClient = context.bridgeClient
    try:
        try:
            context.bridgeClient.connect()
        except Exception as error:
            if manager_config.auto_start_bridge:
                context.logger.info("Retrying bridge connection after manager start request.")
                time.sleep(max(0.0, float(manager_config.startup_wait_seconds)))
                context.bridgeClient.connect()
            else:
                raise error
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
    context.conversationManager = ConversationManager(context)
    context.personalityManager = PersonalityManager(context)
    context.personalityEventHandler = PersonalityEventHandler(context, context.personalityManager)
    context.personalityEventHandler.subscribe()
    context.responseManager = ResponseManager(context)
    context.conversationHistory = ConversationHistory(context)
    context.llm = LLMHandler(context)
    try:
        context.voiceManager = VoiceManager(context)
        context.pushToTalkManager = context.voiceManager.pushToTalkManager
        context.wakeWordManager = context.voiceManager.wakeWordManager
        context.vadManager = context.voiceManager.vadManager
        context.textToSpeech = context.voiceManager.textToSpeech
        context.audioPlayer = context.voiceManager.audioPlayer
        context.speechQueue = context.voiceManager.speechQueue
    except Exception as error:
        context.voiceManager = None
        context.pushToTalkManager = None
        context.wakeWordManager = None
        context.vadManager = None
        context.textToSpeech = None
        context.audioPlayer = None
        context.speechQueue = None
        if context.logger:
            context.logger.warning(f"Voice subsystem could not be initialized: {error}")
    # Router
    context.interpreter = Interpreter(context)
    context.intentRouter = IntentRouter(context)

    # Module Loader
    context.moduleManager = ModuleManager(context)
    context.moduleLoader = context.moduleManager
    context.moduleManager.loadModules()
    context.executionManager = ExecutionManager(context)
    context.notificationManager = NotificationManager(context)

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
