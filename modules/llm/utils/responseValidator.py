"""Validation helpers for structured LLM output."""

from __future__ import annotations

import json
import re
from typing import Any


class ResponseValidator:
    """Validate and lightly repair structured model responses.

    The validator intentionally avoids external JSON-schema dependencies. It
    supports the small schema subset Aura needs now and can be replaced with a
    stricter validator later without changing provider code.
    """

    @staticmethod
    def extractJsonObject(text: str) -> str:
        """Extract the first JSON object-like block from a model response."""

        cleaned = (text or "").strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.strip("`").strip()
            if cleaned.lower().startswith("json"):
                cleaned = cleaned[4:].strip()

        startIndex = cleaned.find("{")
        endIndex = cleaned.rfind("}")
        if startIndex == -1 or endIndex == -1 or endIndex < startIndex:
            return cleaned
        return cleaned[startIndex : endIndex + 1]

    @classmethod
    def parseJson(cls, text: str) -> tuple[bool, dict[str, Any] | list[Any] | None, str | None]:
        """Parse JSON text and return a success flag, parsed value, and error."""

        candidate = cls.extractJsonObject(text)
        try:
            parsed = json.loads(candidate)
        except json.JSONDecodeError as error:
            return False, None, str(error)
        if not isinstance(parsed, (dict, list)):
            return False, None, "Structured response must be a JSON object or array."
        return True, parsed, None

    @staticmethod
    def validateSchema(value: Any, schema: dict[str, Any]) -> tuple[bool, str | None]:
        """Validate a parsed JSON value against Aura's minimal schema format."""

        expectedType = schema.get("type")
        if expectedType == "object" and not isinstance(value, dict):
            return False, "Expected a JSON object."
        if expectedType == "array" and not isinstance(value, list):
            return False, "Expected a JSON array."

        if isinstance(value, dict):
            requiredFields = schema.get("required", [])
            for fieldName in requiredFields:
                if fieldName not in value:
                    return False, f"Missing required field: {fieldName}"

            properties = schema.get("properties", {})
            for fieldName, fieldSchema in properties.items():
                if fieldName in value:
                    valid, error = ResponseValidator._validateValue(value[fieldName], fieldSchema)
                    if not valid:
                        return False, f"{fieldName}: {error}"

        return True, None

    @classmethod
    def _validateValue(cls, value: Any, schema: dict[str, Any]) -> tuple[bool, str | None]:
        """Validate nested JSON values for the subset Aura uses."""

        valid, error = cls._validateSimpleType(value, schema.get("type"))
        if not valid:
            return valid, error

        if schema.get("type") == "array" and isinstance(value, list):
            itemSchema = schema.get("items")
            if isinstance(itemSchema, dict):
                for index, item in enumerate(value):
                    itemValid, itemError = cls.validateSchema(item, itemSchema)
                    if not itemValid:
                        return False, f"Item {index}: {itemError}"

        if schema.get("type") == "object" and isinstance(value, dict):
            return cls.validateSchema(value, schema)

        return True, None

    @staticmethod
    def repairJsonText(text: str) -> str:
        """Apply conservative JSON repair for common model formatting mistakes."""

        repaired = ResponseValidator.extractJsonObject(text)
        repaired = repaired.replace("```json", "").replace("```", "").strip()
        repaired = re.sub(r",\s*([}\]])", r"\1", repaired)
        repaired = repaired.replace("\u201c", '"').replace("\u201d", '"')
        repaired = repaired.replace("\u2018", "'").replace("\u2019", "'")
        return repaired

    @staticmethod
    def _validateSimpleType(value: Any, expectedType: str | None) -> tuple[bool, str | None]:
        """Validate primitive JSON types used by Aura structured responses."""

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
        if not isinstance(value, expectedPythonType):
            return False, f"Expected {expectedType}."
        return True, None
