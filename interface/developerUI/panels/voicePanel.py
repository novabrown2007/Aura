"""Voice panel for the Aura Developer UI."""

from __future__ import annotations

from interface.developerUI.panels.basePanel import TextPanel


class VoicePanel(TextPanel):
    """Display microphone, STT, TTS, and playback state."""

    title = "Voice"

    def refresh(self, snapshot):
        voice = snapshot.voice
        lines = [
            "[VOICE]",
            f"Mic: {voice.get('mic', 'Unknown')}",
            f"Recording: {voice.get('recording', False)}",
            f"STT: {voice.get('stt', 'Unknown')}",
            f"TTS: {voice.get('tts', 'Unknown')}",
            f"Playback: {voice.get('playback', 'Unknown')}",
            "",
            "[STT]",
            voice.get("transcription", "") or "No transcription yet.",
            "",
            f"Timing: {voice.get('lastTiming', {})}",
        ]
        self.setText("\n".join(str(line) for line in lines))
