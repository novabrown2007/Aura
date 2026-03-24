"""System lifecycle facade for Aura."""

from modules.system.reload import Reload
from modules.system.restart import Restart
from modules.system.shutdown import Shutdown


class System:
    """
    Expose system lifecycle actions through one runtime module.

    The facade keeps the public API simple for interface branches while still
    separating each lifecycle action into its own class.
    """

    def __init__(self, context):
        """
        Initialize the system lifecycle facade.

        Args:
            context:
                Runtime context shared by the lifecycle actions.
        """

        self.context = context
        self.logger = context.logger.getChild("System") if context.logger else None

        self.shutdownAction = Shutdown(context)
        self.restartAction = Restart(context)
        self.reloadAction = Reload(context)

        if self.logger:
            self.logger.info("Initialized.")

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
