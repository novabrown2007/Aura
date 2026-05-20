"""System lifecycle facade for Aura."""

from datetime import datetime
from zoneinfo import ZoneInfo

from core.tools.tool import Tool, ToolCategory
from modules.base import AuraModule, ModuleMetadata
from modules.system.reload import Reload
from modules.system.restart import Restart
from modules.system.shutdown import Shutdown


class System(AuraModule):
    """
    Expose system lifecycle actions through one runtime module.

    The facade keeps the public API simple while still separating each
    lifecycle action into its own class.
    """

    metadata = ModuleMetadata(
        name="system",
        version="1.0.0",
        description="System lifecycle controls for reload, restart, and shutdown.",
        permissions=("system:lifecycle", "config:reload"),
        capabilities=("shutdown", "restart", "reload"),
    )

    def __init__(self, context=None):
        """
        Initialize the system lifecycle facade.

        Args:
            context:
                Runtime context shared by the lifecycle actions.
        """

        super().__init__()
        self.logger = None
        self.shutdownAction = None
        self.restartAction = None
        self.reloadAction = None
        if context is not None:
            self.initialize(context)

    def initialize(self, context):
        """Initialize the system module."""

        super().initialize(context)
        self.context = context
        self.logger = context.logger.getChild("System") if context.logger else None

        self.shutdownAction = Shutdown(context)
        self.restartAction = Restart(context)
        self.reloadAction = Reload(context)

        if self.logger:
            self.logger.info("Initialized.")

    def getIntents(self):
        """Return intents handled by system."""

        return []

    def getTools(self):
        """Return deterministic system tools exposed to Aura."""

        return [
            Tool(
                name="system.getTime",
                description="Get the current date and time.",
                parameters={"timezone": {"type": "string"}},
                module="system",
                method="getTime",
                safe=True,
                offlineAllowed=True,
                category=ToolCategory.SAFE,
            ),
            Tool(
                name="system.reload",
                description="Reload Aura configuration.",
                module="system",
                method="reload",
                safe=False,
                confirmRequired=True,
                category=ToolCategory.CONFIRM_REQUIRED,
            ),
        ]

    def getTime(self, timezone: str = "America/Toronto") -> dict[str, str]:
        """Return the current local time for the requested timezone."""

        try:
            zone = ZoneInfo(timezone)
        except Exception:
            zone = ZoneInfo("America/Toronto")
        now = datetime.now(zone)
        return {
            "timezone": str(zone),
            "iso": now.isoformat(),
            "date": now.strftime("%Y-%m-%d"),
            "time": now.strftime("%H:%M:%S"),
        }

    def shutdown(self) -> bool:
        """
        Request runtime shutdown.
        """

        return self.shutdownAction.execute()

    def restart(self) -> bool:
        """
        Request a full runtime restart.
        """

        return self.restartAction.execute()

    def reload(self) -> dict:
        """
        Reload the active configuration from disk.
        """

        return self.reloadAction.execute()
