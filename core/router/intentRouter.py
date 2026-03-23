"""Core implementation for `intentRouter` in the Aura assistant project."""

class IntentRouter:
    """
    Routes interpreted intents to the appropriate module.

    Handles:
    - Command routing
    - Module routing
    - LLM fallback
    """

    def __init__(self, context):
        """Initialize `IntentRouter` with required dependencies and internal state."""
        self.context = context
        self.logger = context.logger.getChild("Router") if context.logger else None
        if self.logger:
            self.logger.info("Initialized.")


    # --------------------------------------------------
    # Routing
    # --------------------------------------------------
    def route(self, intent):
        """
        Route an intent to the correct module.

        Args:
            intent (Intent)

        Returns:
            str
        """
        intent_name = intent.name
        if self.logger:
            self.logger.debug(f"Routing intent: {intent_name}")


        # --------------------------------------------------
        # Command Handling (NEW)
        # --------------------------------------------------
        if intent_name == "command":
            if self.logger:
                self.logger.debug("Routing to CommandHandler")
            commandHandler = self.context.require("commandHandler")
            return commandHandler.handle(intent.raw)


        # --------------------------------------------------
        # Module Routing
        # --------------------------------------------------
        for module in self.context.modules.values():
            if hasattr(module, "canHandle") and module.canHandle(intent):
                if self.logger:
                    self.logger.debug(
                        f"Intent '{intent_name}' handled by {module.__class__.__name__}"
                    )
                return module.handle(intent)


        # --------------------------------------------------
        # LLM Fallback
        # --------------------------------------------------
        if self.logger:
            self.logger.debug(
                f"No module handled intent '{intent_name}', using LLM fallback"
            )
        llm = self.context.require("llm")
        return llm.generateResponse(intent.raw)
