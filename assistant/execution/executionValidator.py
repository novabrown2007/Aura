"""Validation entry point for Aura actions."""

from __future__ import annotations

from assistant.execution.validation import ExecutionConstraintValidator, ParameterValidator


class ExecutionValidator:
    """Validate action requests before execution."""

    def __init__(self, context=None, registry=None):
        self.context = context
        self.registry = registry
        self.parameterValidator = ParameterValidator()
        self.constraintValidator = ExecutionConstraintValidator(context)

    def validate(self, request, actionDefinition=None):
        actionDefinition = actionDefinition or (self.registry.getAction(getattr(request, "action", "")) if self.registry is not None else None)
        valid, error = self.constraintValidator.validate(request, actionDefinition=actionDefinition)
        if not valid:
            return False, error
        if actionDefinition is not None:
            schema = getattr(actionDefinition, "parameterSchema", {}) or {}
            valid, error = self.parameterValidator.validate(getattr(request, "parameters", {}) or {}, schema)
            if not valid:
                return False, error
        return True, None
