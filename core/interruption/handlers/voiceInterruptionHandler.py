"""Voice subsystem interruption handler."""

from __future__ import annotations


class VoiceInterruptionHandler:
    """Cancel active local voice capture, TTS playback, and queued speech."""

    systemName = "voice"

    def __init__(self, context=None):
        self.context = context
        logger = getattr(context, "logger", None)
        self.logger = logger.getChild("Interruption.Voice") if logger else None

    def cancel(self, interruptionContext) -> list[str]:
        """Cancel voice-related operations cooperatively."""

        cancelled = []
        voice = getattr(self.context, "voiceManager", None)
        if voice is None:
            return cancelled

        try:
            speechQueue = getattr(voice, "speechQueue", None)
            if speechQueue is not None and hasattr(speechQueue, "cancel"):
                speechQueue.cancel()
                cancelled.append("voice.speechQueue")
            elif speechQueue is not None and hasattr(speechQueue, "clearQueue"):
                speechQueue.clearQueue()
                cancelled.append("voice.speechQueue")
        except Exception as error:
            interruptionContext.markFailed("voice.speechQueue", str(error))

        try:
            textToSpeech = getattr(voice, "textToSpeech", None)
            if textToSpeech is not None and hasattr(textToSpeech, "cancel"):
                textToSpeech.cancel()
                cancelled.append("voice.tts")
        except Exception as error:
            interruptionContext.markFailed("voice.tts", str(error))

        try:
            audioPlayer = getattr(voice, "audioPlayer", None)
            if audioPlayer is not None and hasattr(audioPlayer, "stopAudio"):
                audioPlayer.stopAudio()
                cancelled.append("voice.playback")
        except Exception as error:
            interruptionContext.markFailed("voice.playback", str(error))

        try:
            pushToTalk = getattr(voice, "pushToTalkManager", None)
            if pushToTalk is not None and hasattr(pushToTalk, "cancelActiveCapture"):
                if pushToTalk.cancelActiveCapture():
                    cancelled.append("voice.capture")
        except Exception as error:
            interruptionContext.markFailed("voice.capture", str(error))

        return cancelled
