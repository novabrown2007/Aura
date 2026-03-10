class Engine:
    """
    Core runtime controller for Aura.

    The Engine operates on an already-initialized RuntimeContext
    and handles assistant runtime behavior. It does not manage
    application startup or shutdown.
    """

    def __init__(self, context):
        """
        Initialize the engine.

        Args:
            context (RuntimeContext):
                Fully initialized runtime context.
        """

        self.context = context
        self.logger = context.logger.getChild("Engine") if context.logger else None

        if self.logger:
            self.logger.info("Initialized")

    # --------------------------------------------------
    # Runtime Loop
    # --------------------------------------------------

    def run(self):
        """
        Run the assistant runtime loop.
        """

        # Temporary CLI interface for testing
        while True:

            try:

                user_input = input("You: ")

                if user_input.lower() in ["exit", "quit"]:
                    break

                input_manager = self.context.require("inputManager")
                output_manager = self.context.require("outputManager")

                response = input_manager.process(user_input)
                output_manager.send(response)

            except KeyboardInterrupt:
                break
