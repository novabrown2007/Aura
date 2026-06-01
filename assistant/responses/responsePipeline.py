"""Structured response orchestration pipeline for Aura."""

from __future__ import annotations


class ResponsePipeline:
    """Coordinate response building, validation, routing, and events."""

    def __init__(self, context=None, builder=None, validator=None, router=None, contextManager=None):
        self.context = context
        self.builder = builder
        self.validator = validator
        self.router = router
        self.contextManager = contextManager
        logger = getattr(context, "logger", None)
        self.logger = logger.getChild("Responses.Pipeline") if logger else None

    def process(self, userInput: str, providerResponse=None, spokenText: str = "", uiText: str = "", metadata: dict | None = None):
        """Build, validate, and route one structured response."""

        response = self.builder.build(userInput, providerResponse=providerResponse, spokenText=spokenText, uiText=uiText, metadata=metadata)
        self._emit("response.created", response.asDict())
        if self._configEnabled("responses.responseValidationEnabled", True):
            valid, errors = self.validator.validate(response)
        else:
            valid, errors = True, []
        if not valid:
            payload = response.asDict()
            payload["validationErrors"] = errors
            self._emit("response.failed", payload)
            return response, {"success": False, "errors": errors}

        self._emit("response.validated", response.asDict())
        delivery = self.router.route(response)
        self._emit("response.routed", response.asDict())
        self._emit("response.delivered", response.asDict())
        self._emit("response.generated", {"text": response.spokenText or response.uiText or ""})
        return response, {"success": True, "delivery": delivery}

    def _emit(self, eventName: str, payload: dict):
        eventManager = getattr(self.context, "eventManager", None)
        if eventManager is None:
            return None
        try:
            return eventManager.emit(eventName, payload)
        except Exception as error:
            if self.logger:
                self.logger.warning(f"Response event emission failed for {eventName}: {error}")
        return None

    def _configEnabled(self, key: str, default: bool = True) -> bool:
        config = getattr(self.context, "config", None)
        if config is None or not hasattr(config, "get"):
            return default
        value = config.get(key, default)
        if isinstance(value, bool):
            return value
        return str(value).strip().lower() in {"1", "true", "yes", "on"}
