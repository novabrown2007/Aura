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
        overlay = snapshot.desktopOverlay or {}
        activeProvider = providers.get("activeProvider") or "Unavailable"
        activeModel = providers.get("activeModel") or "Unavailable"
        voiceProviders = providers.get("voice", {}) or {}
        stt = voiceProviders.get("stt", {}) or {}
        tts = voiceProviders.get("tts", {}) or {}
        interruptions = snapshot.interruptions or system.get("interruptions", {}) or {}
        interruptionState = interruptions.get("state", {}) if isinstance(interruptions.get("state"), dict) else {}
        cancelled = interruptions.get("cancelledOperations") or interruptionState.get("cancelledOperations") or []
        failed = interruptions.get("failedOperations") or interruptionState.get("failedOperations") or []
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
            f"Desktop Overlay: {'Online' if overlay.get('available') else 'Unavailable'}",
            f"Tray: {overlay.get('trayActive', False)} Bubble: {overlay.get('bubbleVisible', False)}",
            f"Bridge: {'Connected' if snapshot.bridge.get('connected') else 'Disconnected'}",
            f"Providers: {'Available' if snapshot.providers.get('available') else 'Unavailable'}",
            f"Active LLM: {activeProvider} ({activeModel})",
            f"Active STT: {stt.get('provider', 'Unavailable')} ({stt.get('model', 'Unavailable')})",
            f"Active TTS: {tts.get('provider', 'Unavailable')} ({tts.get('model', 'Unavailable')})",
            "",
            "Interruptions:",
            f"Enabled: {bool(interruptions.get('enabled', False))}",
            f"Active: {bool(interruptionState.get('active', interruptions.get('active', False)))}",
            f"Cancelled: {', '.join(str(item) for item in cancelled) if cancelled else 'None'}",
            f"Failed: {', '.join(str(item) for item in failed) if failed else 'None'}",
            "",
            "Loaded Modules:",
        ]
        if isinstance(modules, dict):
            for name, module in sorted(modules.items()):
                lines.append(
                    "- {name}: state={state} loaded={loaded} intents={intents} actions={actions} class={className}".format(
                        name=name,
                        state=module.get("state", "UNKNOWN"),
                        loaded=module.get("loaded", True),
                        intents=module.get("intents", 0),
                        actions=module.get("actions", 0),
                        className=module.get("class"),
                    )
                )
        return lines
