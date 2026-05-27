"""System panel for the Aura Developer UI."""

from __future__ import annotations

from interface.developerUI.panels.basePanel import TextPanel


class SystemPanel(TextPanel):
    """Display subsystem status, modules, uptime, and event throughput."""

    title = "System"

    def refresh(self, snapshot):
        self.setText("\n".join(str(line) for line in self.buildLines(snapshot)))

    @staticmethod
    def buildLines(snapshot):
        """Build display lines for the system panel."""

        system = snapshot.system
        modules = system.get("modules", {})
        providers = snapshot.providers or {}
        activeProvider = providers.get("activeProvider") or "Unavailable"
        activeModel = providers.get("activeModel") or "Unavailable"
        voiceProviders = providers.get("voice", {}) or {}
        stt = voiceProviders.get("stt", {}) or {}
        tts = voiceProviders.get("tts", {}) or {}
        lines = [
            "[SYSTEM]",
            f"Uptime Seconds: {system.get('uptimeSeconds', 0)}",
            f"Event Count: {system.get('eventCount', 0)}",
            "",
            "Event Listeners:",
            str(system.get("events", {})),
            "",
            "Subsystems:",
            f"Voice: {'Online' if snapshot.voice else 'Unavailable'}",
            f"Memory: {'Online' if snapshot.memory else 'Unavailable'}",
            f"Bridge: {'Connected' if snapshot.bridge.get('connected') else 'Disconnected'}",
            f"Providers: {'Available' if snapshot.providers.get('available') else 'Unavailable'}",
            f"Active LLM: {activeProvider} ({activeModel})",
            f"Active STT: {stt.get('provider', 'Unavailable')} ({stt.get('model', 'Unavailable')})",
            f"Active TTS: {tts.get('provider', 'Unavailable')} ({tts.get('model', 'Unavailable')})",
            "",
            "Loaded Modules:",
        ]
        if isinstance(modules, dict):
            for name, module in sorted(modules.items()):
                lines.append(f"- {name}: loaded={module.get('loaded', True)} class={module.get('class')}")
        return lines
