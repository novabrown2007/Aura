"""Voice panel for the Aura Developer UI."""

from __future__ import annotations

from PyQt6.QtWidgets import QPlainTextEdit, QVBoxLayout, QWidget


class VoicePanel(QWidget):
    """Display microphone, STT, TTS, and playback state."""

    title = "Voice"

    def __init__(self):
        super().__init__()
        self.text = QPlainTextEdit()
        self.text.setReadOnly(True)
        layout = QVBoxLayout()
        layout.addWidget(self.text)
        self.setLayout(layout)

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
        self.text.setPlainText("\n".join(str(line) for line in lines))

