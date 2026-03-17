class Engine:
    """
    Core runtime controller for Aura.

    The Engine operates on an already-initialized RuntimeContext
    and handles assistant runtime behavior. It does not manage
    application startup or shutdown.

    Responsibilities:
    - Run the main input/output loop
    - Coordinate input processing and output delivery
    - Respect shutdown signals from system commands
    """

    def __init__(self, context):
        """
        Initialize the engine.

        Args:
            context (RuntimeContext):
                Fully initialized runtime context.
        """
        self.context = context
        # Logger
        self.logger = context.logger.getChild("Engine") if context.logger else None
        if self.logger:
            self.logger.info("Initialized.")
        # Ensure shutdown flag exists
        if not hasattr(self.context, "should_exit"):
            self.context.should_exit = False


    # --------------------------------------------------
    # Runtime Loop
    # --------------------------------------------------
    def run(self):
        """
        Run the assistant runtime loop.

        This loop:
        - Continuously reads user input
        - Passes input through the processing pipeline
        - Outputs responses
        - Terminates cleanly when a shutdown signal is received
        """
        if self.logger:
            self.logger.info("Engine runtime started")


        # Temporary CLI interface for testing
        while True:
            try:
                # --------------------------------
                # Shutdown Check (system command)
                # --------------------------------
                if getattr(self.context, "should_exit", False):
                    if self.logger:
                        self.logger.info("Shutdown signal received, stopping engine")
                    break


                # --------------------------------
                # Input
                # --------------------------------
                user_input = input("You: ")
                # Manual exit fallback (CLI convenience)
                if user_input.lower() in ["exit", "quit"]:
                    if self.logger:
                        self.logger.info("Manual exit triggered")
                    break


                # --------------------------------
                # Processing Pipeline
                # --------------------------------
                input_manager = self.context.require("inputManager")
                output_manager = self.context.require("outputManager")
                response = input_manager.process(user_input)


                # --------------------------------
                # Output
                # --------------------------------
                output_manager.send(response)


            except KeyboardInterrupt:
                if self.logger:
                    self.logger.info("KeyboardInterrupt received, stopping engine")
                break
            except Exception as error:
                # Catch-all to prevent full crash during runtime
                if self.logger:
                    self.logger.error(f"Runtime error: {error}")
                print("An unexpected error occurred. Check logs for details.")


        # --------------------------------
        # Shutdown Complete
        # --------------------------------
        if self.logger:
            self.logger.info("Engine stopped")
