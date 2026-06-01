"""Input routing helpers for Aura's Windows overlay."""

from __future__ import annotations


class OverlayInputHandler:
    """Translate key and button input into overlay actions."""

    def __init__(self, context=None, overlayManager=None):
        self.context = context
        self.overlayManager = overlayManager

    def bindEntry(self, entry):
        entry.bind("<Return>", self._onSubmit)
        entry.bind("<Escape>", self._onEscape)
        return entry

    def _onSubmit(self, _event=None):
        if self.overlayManager is not None:
            self.overlayManager.submitQuickInteraction()
        return "break"

    def _onEscape(self, _event=None):
        if self.overlayManager is not None:
            self.overlayManager.hideQuickInteraction()
        return "break"

