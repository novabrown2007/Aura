"""Tool model used by Aura's deterministic execution layer."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


class ToolCategory:
    """Execution policy categories for deterministic Aura tools."""

    SAFE = "SAFE"
    CONFIRM_REQUIRED = "CONFIRM_REQUIRED"
    ADMIN_ONLY = "ADMIN_ONLY"


@dataclass(frozen=True)
class Tool:
    """Description of a deterministic Aura capability.

    LLMs may select tools by name, but only Aura validates and executes them.
    """

    name: str
    description: str
    parameters: dict[str, dict[str, Any]] = field(default_factory=dict)
    requiredParameters: tuple[str, ...] = field(default_factory=tuple)
    module: str = ""
    method: str = ""
    safe: bool = True
    offlineAllowed: bool = False
    confirmRequired: bool = False
    category: str = ToolCategory.SAFE

    def validateArguments(self, arguments: dict[str, Any] | None) -> tuple[bool, str | None]:
        """Validate required arguments and simple parameter types."""

        if arguments is None:
            arguments = {}
        if not isinstance(arguments, dict):
            return False, "Tool arguments must be a JSON object."

        for parameterName in self.requiredParameters:
            if parameterName not in arguments or arguments[parameterName] is None:
                return False, f"Missing required parameter: {parameterName}"

        for parameterName, value in arguments.items():
            parameterSchema = self.parameters.get(parameterName)
            if not parameterSchema:
                continue
            valid, error = self._validateType(value, parameterSchema.get("type"))
            if not valid:
                return False, f"{parameterName}: {error}"

        return True, None

    def toSchema(self) -> dict[str, Any]:
        """Export a JSON-schema-like representation for structured prompting."""

        return {
            "name": self.name,
            "description": self.description,
            "module": self.module,
            "safe": self.safe,
            "offlineAllowed": self.offlineAllowed,
            "confirmRequired": self.confirmRequired,
            "category": self.category,
            "parameters": {
                "type": "object",
                "properties": self.parameters,
                "required": list(self.requiredParameters),
            },
        }

    def asDict(self) -> dict[str, Any]:
        """Return a clean serializable dictionary."""

        return {
            "name": self.name,
            "description": self.description,
            "parameters": self.parameters,
            "requiredParameters": list(self.requiredParameters),
            "module": self.module,
            "method": self.method,
            "safe": self.safe,
            "offlineAllowed": self.offlineAllowed,
            "confirmRequired": self.confirmRequired,
            "category": self.category,
        }

    @staticmethod
    def _validateType(value: Any, expectedType: str | None) -> tuple[bool, str | None]:
        """Validate a basic JSON-compatible type."""

        if expectedType is None:
            return True, None

        typeMap = {
            "string": str,
            "integer": int,
            "number": (int, float),
            "boolean": bool,
            "object": dict,
            "array": list,
        }
        expectedPythonType = typeMap.get(expectedType)
        if expectedPythonType is None:
            return True, None
        if expectedType == "integer" and isinstance(value, bool):
            return False, "Expected integer."
        if expectedType == "number" and isinstance(value, bool):
            return False, "Expected number."
        if not isinstance(value, expectedPythonType):
            return False, f"Expected {expectedType}."
        return True, None
