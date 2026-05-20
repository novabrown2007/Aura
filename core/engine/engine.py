"""Headless runtime engine for Aura."""

from time import sleep


class Engine:
    """
    Run Aura as a backend service.
    """

    def __init__(self, context):
        """
        Initialize the engine with an already-bootstrapped runtime context.
        """

        self.context = context
        self.logger = context.logger.getChild("Engine") if context.logger else None
        if not hasattr(self.context, "should_exit"):
            self.context.should_exit = False

        if self.logger:
            self.logger.info("Initialized.")

    def run(self, poll_interval: float = 0.1):
        """
        Keep the runtime alive until shutdown is requested.

        Args:
            poll_interval:
                Idle wait interval for the headless service loop.
        """

        if self.logger:
            self.logger.info("Engine runtime started in headless mode")

        while not getattr(self.context, "should_exit", False):
            sleep(poll_interval)

        if self.logger:
            self.logger.info("Engine stopped")
