"""Tray actions for Aura's Windows desktop shell."""

from __future__ import annotations


class TrayActions:
    """Bindable callbacks triggered by tray menu commands."""

    def __init__(self, overlayManager=None):
        self.overlayManager = overlayManager

    def openAura(self):
        if self.overlayManager is not None:
            self.overlayManager.showWindow()

    def quickConversation(self):
        if self.overlayManager is not None:
            self.overlayManager.showQuickInteraction()

    def muteMicrophone(self):
        context = getattr(self.overlayManager, "context", None)
        voice = getattr(context, "voiceManager", None)
        if voice is not None and hasattr(voice, "setMuted"):
            try:
                voice.setMuted(True)
            except Exception:
                pass

    def pauseListening(self):
        context = getattr(self.overlayManager, "context", None)
        wakeWord = getattr(context, "wakeWordManager", None)
        if wakeWord is not None and hasattr(wakeWord, "shutdown"):
            try:
                wakeWord.shutdown()
            except Exception:
                pass

    def settings(self):
        context = getattr(self.overlayManager, "context", None)
        eventManager = getattr(context, "eventManager", None)
        if eventManager is not None:
            try:
                eventManager.emit("desktop.settings.opened", {})
            except Exception:
                pass

    def exitAura(self):
        if self.overlayManager is not None:
            self.overlayManager.requestExit(reason="tray")

