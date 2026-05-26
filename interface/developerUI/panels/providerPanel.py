"""Provider panel for the Aura Developer UI."""

from __future__ import annotations

from interface.developerUI.panels.basePanel import TextPanel


class ProviderPanel(TextPanel):
    """Display LLM provider state, fallback state, and timing."""

    title = "Providers"

    def refresh(self, snapshot):
        providers = snapshot.providers
        lines = [
            "[PROVIDER]",
            f"Active Provider: {providers.get('activeProvider', 'Unavailable')}",
            f"Active Model: {providers.get('activeModel', 'Unavailable')}",
            f"Fallback Provider: {providers.get('fallbackProvider', '')}",
            f"Offline Mode: {providers.get('offlineMode', '')}",
        ]
        for name, provider in (providers.get("providers") or {}).items():
            lines.append("")
            lines.append(f"Provider: {name}")
            lines.append(f"Model: {provider.get('model')}")
            lines.append(f"Initialized: {provider.get('initialized')}")
            lines.append(f"Active: {provider.get('active')}")
            lines.append(f"Fallback: {provider.get('fallback')}")
        lines.append("")
        lines.append(f"Performance: {snapshot.performance.get('aggregates', {})}")
        self.setText("\n".join(str(line) for line in lines))
