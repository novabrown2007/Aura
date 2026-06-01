"""Central structured response orchestrator for Aura."""

from __future__ import annotations

from assistant.responses.handlers.responseEventHandler import ResponseEventHandler
from assistant.responses.responseBuilder import ResponseBuilder
from assistant.responses.responseContextManager import ResponseContextManager
from assistant.responses.responseFormatter import ResponseFormatter
from assistant.responses.responsePipeline import ResponsePipeline
from assistant.responses.responseRouter import ResponseRouter
from assistant.responses.responseValidator import ResponseValidator


class ResponseManager:
    """Coordinate response construction, validation, and delivery."""

    def __init__(self, context=None):
        self.context = context
        logger = getattr(context, "logger", None)
        self.logger = logger.getChild("Responses") if logger else None

        self.contextManager = ResponseContextManager(context)
        self.formatter = ResponseFormatter(context)
        self.builder = ResponseBuilder(context, self.contextManager)
        self.validator = ResponseValidator(context)
        self.router = ResponseRouter(context, self.formatter)
        self.pipeline = ResponsePipeline(context, self.builder, self.validator, self.router, self.contextManager)
        self.eventHandler = ResponseEventHandler(context, self)
        self.lastResponse = None
        self.lastDelivery = {}

        if self.context is not None:
            self.context.responseManager = self
            self.eventHandler.subscribe()

    def createResponse(self, userInput: str, providerResponse=None, spokenText: str = "", uiText: str = "", metadata: dict | None = None):
        """Create, validate, route, and return one structured response."""

        response, delivery = self.pipeline.process(
            userInput,
            providerResponse=providerResponse,
            spokenText=spokenText,
            uiText=uiText,
            metadata=metadata,
        )
        self.lastResponse = response
        self.lastDelivery = delivery
        return response

    def snapshot(self) -> dict:
        """Return a read-only state snapshot for observability and UI use."""

        return {
            "available": True,
            "lastResponse": self.lastResponse.asDict() if self.lastResponse is not None and hasattr(self.lastResponse, "asDict") else None,
            "lastDelivery": dict(self.lastDelivery or {}),
            "context": self.contextManager.snapshot(),
        }

    def shutdown(self):
        """Unsubscribe from response-adjacent events."""

        self.eventHandler.unsubscribe()
