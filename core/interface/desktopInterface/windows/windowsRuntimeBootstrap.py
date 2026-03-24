"""Windows runtime bootstrap for Aura desktop execution."""

from config.configLoader import ConfigLoader
from core.engine.engine import Engine
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


def createRuntimeContext() -> RuntimeContext:
    """
    Build a full runtime context for the Windows interface branch.
    """

    context = RuntimeContext()

    context.logger = AuraLogger()
    context.config = ConfigLoader(context)

    context.threader = ThreadingManager(context)
    context.eventManager = EventManager(context)
    context.taskManager = TaskManager(context)
    context.scheduler = Scheduler(context)

    context.database = MySQLDatabase(context)
    context.database.connect()
    context.database.initialize()

    context.memoryManager = MemoryManager(context)
    context.conversationHistory = ConversationHistory(context)
    context.llm = LLMHandler(context)

    context.interpreter = Interpreter(context)
    context.intentRouter = IntentRouter(context)

    context.inputManager = InputManager(context)
    context.outputManager = OutputManager(context)

    loader = ModuleLoader(context)
    loader.loadModules()

    context.engine = Engine(context)
    context.should_exit = False
    return context


def startup(context: RuntimeContext):
    """
    Start runtime services required before opening the Windows app.
    """

    logger = context.logger.getChild("WindowsRuntime")
    logger.info("Starting Aura Windows runtime.")

    if context.scheduler:
        context.scheduler.start()


def shutdown(context: RuntimeContext):
    """
    Stop runtime services and release external resources.
    """

    logger = context.logger.getChild("WindowsRuntime")
    logger.info("Stopping Aura Windows runtime.")

    if context.scheduler:
        context.scheduler.stop()

    if context.database:
        context.database.close()

    if context.logger:
        context.logger.close()
