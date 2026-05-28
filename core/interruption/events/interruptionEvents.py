"""Canonical event names emitted by Aura's interruption system."""


class InterruptionEvents:
    """Interruption and cancellation event constants."""

    REQUESTED = "interruption.requested"
    STARTED = "interruption.started"
    COMPLETED = "interruption.completed"
    FAILED = "interruption.failed"
    OPERATION_CANCELLED = "operation.cancelled"
    TTS_CANCELLED = "tts.cancelled"
    PROVIDER_CANCELLED = "provider.cancelled"
    CONVERSATION_CANCELLED = "conversation.cancelled"

