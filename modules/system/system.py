"""System lifecycle facade for Aura."""

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
