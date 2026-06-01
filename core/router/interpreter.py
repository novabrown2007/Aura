"""Convert raw input text into runtime intents."""

from core.router.intent import Intent


class Interpreter:
    """
    Convert raw user input into coarse runtime intents.

    Without a command layer, the interpreter focuses only on normal assistant
    intents and otherwise falls back to the LLM route.
    """

    def __init__(self, context):
        """Initialize the interpreter with runtime context and optional logging."""

        self.context = context
        self.logger = context.logger.getChild("Interpreter") if context.logger else None
        if self.logger:
            self.logger.info("Interpreter initialized.")

    def interpret(self, text: str):
        """
        Interpret raw user input and convert it into an Intent object.
        """

        if self.logger:
            self.logger.debug(f"Interpreting input: {text}")

        normalized = text.strip().lower()

        if self._isSpotifyCommand(normalized):
            intent_name = self._resolveSpotifyIntent(normalized)
            return Intent(name=intent_name, raw=text, data=self._extractSpotifyData(text, intent_name))
        if "weather" in normalized:
            intent_name = "weather.current"
            if any(term in normalized for term in ("forecast", "tomorrow", "today", "week", "hour", "rain", "snow", "will it", "chance")):
                intent_name = "weather.forecast"
            if any(term in normalized for term in ("alert", "warning", "storm", "severe", "tornado", "flood", "heat", "cold")):
                intent_name = "weather.alerts"
            return Intent(name=intent_name, raw=text, data={"location": self._extractLocation(text)})
        if "remind" in normalized:
            return Intent(name="reminder", raw=text)
        if "time" in normalized:
            return Intent(name="time", raw=text)

        return Intent(name="llm", raw=text)

    @staticmethod
    def _extractLocation(text: str) -> str:
        lowered = str(text or "").strip()
        for marker in (" in ", " for ", " at ", " near "):
            if marker in lowered.lower():
                tail = lowered.lower().split(marker, 1)[1].strip(" ?.!")
                return tail.title() if tail else ""
        return ""

    @staticmethod
    def _isSpotifyCommand(normalized: str) -> bool:
        return any(
            term in normalized
            for term in (
                "spotify",
                "music",
                "song",
                "playlist",
                "now playing",
                "what song",
                "what's playing",
                "what is playing",
                "pause",
                "resume",
                "skip ahead",
                "skip back",
                "seek",
                "rewind",
                "volume",
                "speed",
                "next track",
                "previous track",
                "transfer playback",
                "device",
            )
        )

    @staticmethod
    def _resolveSpotifyIntent(normalized: str) -> str:
        if any(term in normalized for term in ("pause", "stop music", "pause music")):
            return "spotify.pause"
        if any(term in normalized for term in ("next", "skip to next", "next track")):
            return "spotify.next"
        if any(term in normalized for term in ("previous", "go back", "previous track", "back")):
            return "spotify.previous"
        if any(term in normalized for term in ("seek", "skip ahead", "skip back", "rewind", "forward", "back 10", "back 30")):
            return "spotify.seek"
        if any(term in normalized for term in ("speed", "1.5x", "2x", "0.5x")):
            return "spotify.speed"
        if "volume" in normalized or "louder" in normalized or "quieter" in normalized:
            return "spotify.volume"
        if "playlist" in normalized:
            return "spotify.playPlaylist"
        if any(term in normalized for term in ("what song", "what's playing", "what is playing", "now playing")):
            return "spotify.nowPlaying"
        if any(term in normalized for term in ("devices", "device", "phone", "desktop", "web player", "transfer")):
            return "spotify.listDevices" if "transfer" not in normalized else "spotify.transferDevice"
        if "search" in normalized:
            return "spotify.search"
        return "spotify.play"

    @staticmethod
    def _extractSpotifyData(text: str, intentName: str) -> dict:
        lowered = str(text or "").strip()
        data: dict[str, object] = {}
        if intentName in {"spotify.play", "spotify.playPlaylist", "spotify.search"}:
            data["query"] = lowered.replace("play ", "", 1).strip() if lowered.lower().startswith("play ") else lowered
        if intentName == "spotify.playPlaylist":
            data["playlist"] = data.get("query", lowered)
        if intentName == "spotify.seek":
            if "minute" in lowered or "minute" in lowered.lower():
                data["offsetMs"] = 60_000
            if "second" in lowered or "seconds" in lowered.lower():
                import re

                match = re.search(r"(\d+)", lowered)
                amount = int(match.group(1)) if match else 0
                offset = amount * 1000
                if any(term in lowered.lower() for term in ("back", "rewind", "previous")):
                    offset = -offset
                data["offsetMs"] = offset
        if intentName == "spotify.speed":
            import re

            match = re.search(r"(\d+(?:\.\d+)?)\s*x", lowered)
            if match:
                data["speed"] = float(match.group(1))
        if intentName == "spotify.volume":
            import re

            match = re.search(r"(\d{1,3})", lowered)
            if match:
                data["volume"] = min(100, max(0, int(match.group(1))))
        if intentName == "spotify.transferDevice":
            if "phone" in lowered:
                data["deviceId"] = "device-phone"
            elif "web" in lowered:
                data["deviceId"] = "device-web"
            else:
                data["deviceId"] = "device-desktop"
        return data
