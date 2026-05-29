"""Voice panel for the Aura Developer UI."""

from __future__ import annotations

from interface.developerUI.panels.basePanel import TextPanel


class VoicePanel(TextPanel):
    """Display microphone, STT, TTS, and playback state."""

    title = "Voice"

    def refresh(self, snapshot):
        voice = snapshot.voice
        wakeWord = voice.get("alwaysActive", {}) or {}
        vad = voice.get("vad", {}) or {}
        lines = [
            "[VOICE]",
            f"Mic: {voice.get('mic', 'Unknown')}",
            f"Recording: {voice.get('recording', False)}",
            f"STT: {voice.get('stt', 'Unknown')}",
            f"TTS: {voice.get('tts', 'Unknown')}",
            f"Playback: {voice.get('playback', 'Unknown')}",
            "",
            "[WAKE WORD]",
            f"State: {wakeWord.get('state', 'Unknown')}",
            f"Listening: {wakeWord.get('listening', False)}",
            f"Phrases: {', '.join(wakeWord.get('phrases') or []) or 'None'}",
            f"Confidence: {float(wakeWord.get('confidence') or 0.0):.2f}",
            f"Last Detection: {wakeWord.get('lastDetection', '') or 'Never'}",
            f"Cooldown: {wakeWord.get('cooldown', False)} ({float(wakeWord.get('cooldownRemainingSeconds') or 0.0):.1f}s)",
            f"Microphone: {wakeWord.get('microphone', 'Unknown')}",
            f"Prediction: {float(wakeWord.get('predictionTimeMs') or 0.0):.2f} ms",
            f"Activations: {wakeWord.get('activationCount', 0)}",
            "",
            "[VAD]",
            f"Enabled: {vad.get('enabled', False)}",
            f"State: {vad.get('state', 'Unknown')}",
            f"Backend: {vad.get('backend', '') or vad.get('detector', {}).get('backend', 'Unknown')}",
            f"Confidence: {float(vad.get('confidence') or 0.0):.2f}",
            f"Speech: {vad.get('speechDetected', False)}",
            f"Silence: {vad.get('silenceDetected', False)} ({float(vad.get('silenceDuration') or 0.0):.1f}s)",
            f"Recording: {float(vad.get('recordingDuration') or 0.0):.1f}s",
            f"Speech Duration: {float(vad.get('speechDuration') or 0.0):.1f}s",
            "",
            "[STT]",
            voice.get("transcription", "") or "No transcription yet.",
            "",
            f"Timing: {voice.get('lastTiming', {})}",
        ]
        self.setText("\n".join(str(line) for line in lines))
