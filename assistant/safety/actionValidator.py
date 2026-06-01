"""Action validation for Aura execution governance."""

from __future__ import annotations


class ActionValidator:
    """Validate action arguments and parameter ranges."""

    def __init__(self, context=None):
        self.context = context
        logger = getattr(context, "logger", None)
        self.logger = logger.getChild("Safety.ActionValidator") if logger else None

    def validate(self, request, tool=None):
        """Validate a proposed action request."""

        if tool is not None and hasattr(tool, "validateArguments"):
            valid, error = tool.validateArguments(getattr(request, "parameters", {}) or {})
            if not valid:
                return False, error or "Invalid action arguments."
        parameters = dict(getattr(request, "parameters", {}) or {})
        for key in ("brightness", "volume", "percent", "percentage"):
            if key in parameters:
                try:
                    value = float(parameters[key])
                except Exception:
                    return False, f"{key}: Expected numeric value."
                if not 0 <= value <= 100:
                    return False, f"{key}: Value must be between 0 and 100."
        if "kelvin" in parameters:
            try:
                value = int(parameters["kelvin"])
            except Exception:
                return False, "kelvin: Expected integer value."
            if not 1000 <= value <= 10000:
                return False, "kelvin: Value must be between 1000 and 10000."
        return True, None

