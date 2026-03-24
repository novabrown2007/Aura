"""Intent routing for Aura's headless runtime."""


class IntentRouter:
    """
    Route interpreted intents to modules or fall back to the LLM.
    """

    def __init__(self, context):
        """Initialize the intent router."""

        self.context = context
        self.logger = context.logger.getChild("Router") if context.logger else None
        if self.logger:
            self.logger.info("Initialized.")

    def route(self, intent):
        """
        Route an intent to the correct module or to the LLM fallback.
        """

        intent_name = intent.name
        if self.logger:
            self.logger.debug(f"Routing intent: {intent_name}")

        for module in self.context.modules.values():
            if hasattr(module, "canHandle") and module.canHandle(intent):
                if self.logger:
                    self.logger.debug(
                        f"Intent '{intent_name}' handled by {module.__class__.__name__}"
                    )
                return module.handle(intent)

        if self.logger:
            self.logger.debug(
                f"No module handled intent '{intent_name}', using LLM fallback"
            )
        llm = self.context.require("llm")
        return llm.generateResponse(intent.raw)
