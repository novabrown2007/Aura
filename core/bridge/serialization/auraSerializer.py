"""Serialization helpers for Aura Protocol messages."""

from __future__ import annotations

import json
from typing import Any

from ..protocol.auraMessage import AuraMessage


class AuraSerializer:
    """Serialize and deserialize Aura Protocol envelopes."""

    @staticmethod
    def serializeMessage(message: AuraMessage | dict[str, Any]) -> str:
        """Return a compact JSON representation of one message."""

        payload = message.toDict() if isinstance(message, AuraMessage) else dict(message)
        return json.dumps(payload, ensure_ascii=True, separators=(",", ":"))

    @staticmethod
    def deserializeMessage(payload: str | bytes | dict[str, Any]) -> AuraMessage:
        """Return one AuraMessage from a JSON string or dictionary."""

        if isinstance(payload, AuraMessage):
            return payload
        if isinstance(payload, dict):
            return AuraMessage.fromDict(payload)
        if isinstance(payload, bytes):
            payload = payload.decode("utf-8")
        parsed = json.loads(str(payload))
        if not isinstance(parsed, dict):
            raise ValueError("Aura Protocol message must be a JSON object.")
        return AuraMessage.fromDict(parsed)

    @staticmethod
    def serializeEnvelope(messages: list[AuraMessage | dict[str, Any]]) -> str:
        """Serialize a batch of messages."""

        payload = [message.toDict() if isinstance(message, AuraMessage) else dict(message) for message in messages]
        return json.dumps(payload, ensure_ascii=True, separators=(",", ":"))

    @staticmethod
    def deserializeEnvelope(payload: str | bytes | list[dict[str, Any]]) -> list[AuraMessage]:
        """Deserialize a batch of messages."""

        if isinstance(payload, list):
            return [AuraMessage.fromDict(item) for item in payload]
        if isinstance(payload, bytes):
            payload = payload.decode("utf-8")
        parsed = json.loads(str(payload))
        if isinstance(parsed, dict):
            return [AuraMessage.fromDict(parsed)]
        if not isinstance(parsed, list):
            raise ValueError("Aura Protocol envelope must be a JSON object or array.")
        return [AuraMessage.fromDict(item) for item in parsed if isinstance(item, dict)]

