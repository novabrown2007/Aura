"""Dispatch Aura Protocol messages to deterministic handlers."""

from __future__ import annotations

from ..protocol.auraCategories import AuraCategories


class AuraRouter:
    """Route assistant-facing bridge messages by category."""

    def __init__(self, context, handlers: dict[str, object] | None = None, validator=None):
        self.context = context
        self.validator = validator
        self.handlers = handlers or {}
        self.logger = context.logger.getChild("Bridge.Router") if getattr(context, "logger", None) else None

    def registerHandler(self, category: str, handler):
        """Register a handler for one category."""

        self.handlers[str(category)] = handler

    def route(self, message):
        """Validate and dispatch one message."""

        if not hasattr(message, "category"):
            from ..protocol.auraMessage import AuraMessage

            message = AuraMessage.fromDict(message)

        if self.validator is not None:
            valid, error = self.validator.validateMessage(message)
            if not valid:
                if self.logger:
                    self.logger.warning(f"Rejected protocol message: {error.code} - {error.message}")
                return {"success": False, "error": error.message, "code": error.code}

        handler = self.handlers.get(message.category)
        if handler is None:
            if self.logger:
                self.logger.debug(f"No handler registered for {message.category}")
            return {"success": True, "message": message.toDict()}

        try:
            result = handler.handle(message)
            return {"success": True, "result": result, "message": message.toDict()}
        except Exception as error:
            if self.logger:
                self.logger.error(f"Bridge handler failed for {message.category}: {error}")
            return {"success": False, "error": str(error), "message": message.toDict()}

    def registerDefaultHandlers(self):
        """Register handlers supplied on the runtime context."""

        for category, attribute in (
            (AuraCategories.ASSISTANT_CONTEXT, "contextHandler"),
            (AuraCategories.ASSISTANT_NOTIFICATION, "notificationHandler"),
            (AuraCategories.ASSISTANT_RESPONSE, "responseHandler"),
            (AuraCategories.ASSISTANT_ERROR, "errorHandler"),
            (AuraCategories.ASSISTANT_STREAM_AVAILABLE, "streamHandler"),
        ):
            handler = getattr(self.context, attribute, None)
            if handler is not None:
                self.registerHandler(category, handler)
        return self.handlers

