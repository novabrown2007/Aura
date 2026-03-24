"""Headless runtime engine for Aura."""

from time import sleep
from typing import Optional


class Engine:
    """
    Run Aura as a headless service and expose request-processing helpers.

    The engine no longer owns a terminal loop. Interfaces can attach in other
    branches and submit input through the InputManager or through the engine's
    `handleInput()` convenience wrapper.
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
        Keep the runtime alive until an attached interface requests shutdown.

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

    def handleInput(self, text: str, source: str = "api", metadata: Optional[dict] = None) -> dict:
        """
        Process one interface request through the runtime pipeline.
        """

        input_manager = self.context.require("inputManager")
        return input_manager.submit(text=text, source=source, metadata=metadata)
