"""Provider panel for the Aura Developer UI."""

from __future__ import annotations

from interface.developerUI.panels.basePanel import TextPanel


class ProviderPanel(TextPanel):
    """Display LLM provider state, fallback state, and timing."""

    title = "Providers"

    def refresh(self, snapshot):
        providers = snapshot.providers
        activeProvider = providers.get("activeProvider", "Unavailable")
        activeModel = providers.get("activeModel", "Unavailable")
        lines = [
            "[PROVIDER]",
            f"Active LLM: {activeProvider} ({activeModel})",
            f"Fallback Provider: {providers.get('fallbackProvider', '')}",
            f"Offline Mode: {providers.get('offlineMode', '')}",
            f"Active STT: {self._formatVoiceProvider(providers, 'stt')}",
            f"Active TTS: {self._formatVoiceProvider(providers, 'tts')}",
            "",
            "Configured Providers:",
        ]
        for name, provider in (providers.get("providers") or {}).items():
            marker = " [ACTIVE]" if provider.get("active") else ""
            lines.append("")
            lines.append(f"Provider: {name}{marker}")
            lines.append(f"Model: {provider.get('model')}")
            lines.append(f"Initialized: {provider.get('initialized')}")
            lines.append(f"Fallback: {provider.get('fallback')}")
        lines.append("")
        lines.append(f"Performance: {snapshot.performance.get('aggregates', {})}")
        self.setText("\n".join(str(line) for line in lines))

    @staticmethod
    def _formatVoiceProvider(providers: dict, key: str) -> str:
        voice = providers.get("voice", {}) or {}
        provider = voice.get(key, {}) or {}
        if not provider:
            return "Unavailable"
        name = provider.get("provider") or "Unavailable"
        model = provider.get("model") or "Unknown"
        enabled = "enabled" if provider.get("enabled") else "disabled"
        initialized = "initialized" if provider.get("initialized") else "idle"
        return f"{name} ({model}, {enabled}, {initialized})"
