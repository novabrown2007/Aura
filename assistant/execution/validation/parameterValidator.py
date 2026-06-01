"""Parameter validation for execution actions."""

from __future__ import annotations

from typing import Any


class ParameterValidator:
    """Validate execution parameters against a simple schema."""

    def validate(self, parameters: dict[str, Any] | None, schema: dict[str, Any] | None = None):
        parameters = dict(parameters or {})
        schema = dict(schema or {})

        required = list(schema.get("required") or [])
        for name in required:
            if name not in parameters or parameters.get(name) is None:
                return False, f"Missing required parameter: {name}"

        properties = dict(schema.get("properties") or {})
        for name, definition in properties.items():
            if name not in parameters:
                continue
            valid, error = self._validateValue(parameters.get(name), definition or {})
            if not valid:
                return False, f"{name}: {error}"

        return True, None

    def _validateValue(self, value: Any, definition: dict[str, Any]):
        expectedType = str(definition.get("type") or "").lower()
        if expectedType:
            typeMap = {
                "string": str,
                "integer": int,
                "number": (int, float),
                "boolean": bool,
                "array": list,
                "object": dict,
            }
            expected = typeMap.get(expectedType)
            if expected is not None:
                if expectedType in {"integer", "number"} and isinstance(value, bool):
                    return False, f"Expected {expectedType}."
                if not isinstance(value, expected):
                    return False, f"Expected {expectedType}."

        enumValues = definition.get("enum")
        if enumValues and value not in enumValues:
            return False, f"Expected one of {list(enumValues)}."

        minimum = definition.get("minimum")
        if minimum is not None:
            try:
                if float(value) < float(minimum):
                    return False, f"Must be greater than or equal to {minimum}."
            except Exception:
                return False, "Expected numeric value."

        maximum = definition.get("maximum")
        if maximum is not None:
            try:
                if float(value) > float(maximum):
                    return False, f"Must be less than or equal to {maximum}."
            except Exception:
                return False, "Expected numeric value."

        return True, None
