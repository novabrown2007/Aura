"""Config reload lifecycle action for Aura."""


class Reload:
    """
    Reload Aura configuration from disk.

    Reloading is intentionally lightweight on `master`: it refreshes the
    in-memory configuration values without tearing down or rebuilding the
    runtime.
    """

    def __init__(self, context):
        """
        Initialize the reload action.

        Args:
            context:
                Runtime context providing access to the config loader.
        """

        self.context = context
        self.logger = context.logger.getChild("System.Reload") if context.logger else None

    def execute(self) -> dict:
        """
        Reload the active configuration object.

        Returns:
            dict:
                The updated configuration dictionary after reload completes.
        """

        config = self.context.require("config")
        config.reload()

        if self.logger:
            self.logger.info("Configuration reload requested.")

        if hasattr(config, "asDict"):
            return dict(config.asDict())
        if hasattr(config, "_data"):
            return dict(config._data)
        return {}
