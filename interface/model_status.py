"""Helpers for displaying the active LLM model in interface shells."""

from __future__ import annotations


def get_current_model_name(context) -> str:
    """Return the active model name for a runtime context."""

    manager = getattr(context, "llmManager", None)
    if manager is None:
        return "Unavailable"

    if hasattr(manager, "getStatus"):
        status = manager.getStatus()
        model_name = str(status.get("activeModel") or status.get("activeProvider") or "Unknown")
        if status.get("offlineMode"):
            reason = str(status.get("offlineReason") or "").lower()
            if any(token in reason for token in ("429", "resource_exhausted", "quota", "rate limit", "rate-limit")):
                return f"{model_name} (Gemini quota fallback)"
            return f"{model_name} (offline fallback)"
        return model_name

    provider_name = getattr(manager, "activeProviderName", "")
    providers = getattr(manager, "providers", {}) or {}
    provider = providers.get(provider_name) if hasattr(providers, "get") else None
    model_name = getattr(provider, "model", "") if provider is not None else ""
    if not model_name:
        model_name = provider_name or "Unknown"
    return str(model_name)


def format_current_model_label(context) -> str:
    """Format the model label shown in UI headers."""

    return f"Currently Running: {get_current_model_name(context)}"
