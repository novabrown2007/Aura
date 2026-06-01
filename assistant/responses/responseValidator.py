"""Validation for structured assistant responses."""

from __future__ import annotations

from assistant.responses.models import AssistantResponse


class ResponseValidator:
    """Validate response packets before delivery."""

    def __init__(self, context=None):
        self.context = context
        logger = getattr(context, "logger", None)
        self.logger = logger.getChild("Responses.Validator") if logger else None

    def validate(self, response: AssistantResponse):
        """Validate one structured response."""

        errors = []
        if not isinstance(response, AssistantResponse):
            errors.append("Response must be an AssistantResponse.")
            return False, errors
        if not response.spokenText and not response.uiText and not response.actions and not response.notifications:
            errors.append("Response must contain at least one delivery surface.")
        for action in response.actions:
            if not getattr(action, "actionName", "") and not getattr(action, "target", ""):
                errors.append("Response actions require an actionName or target.")
                break
        return not errors, errors
