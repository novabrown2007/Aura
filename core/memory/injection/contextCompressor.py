"""Memory context compression for prompt-safe injection."""

from __future__ import annotations


class ContextCompressor:
    """Compress verbose memories while preserving their practical meaning."""

    def __init__(self, maxLineCharacters: int = 220, context=None):
        self.maxLineCharacters = int(maxLineCharacters)
        self.context = context
        logger = getattr(context, "logger", None)
        self.logger = logger.getChild("Memory.Compressor") if logger else None

    def compress(self, text: str, maxCharacters: int | None = None) -> str:
        """Return a compact one-line memory string."""

        limit = int(maxCharacters or self.maxLineCharacters)
        cleaned = " ".join(str(text or "").split())
        if len(cleaned) <= limit:
            return cleaned
        sentences = self._splitSentences(cleaned)
        if sentences and len(sentences[0]) <= limit:
            return sentences[0]
        return cleaned[: max(limit - 3, 0)].rstrip() + "..."

    @staticmethod
    def _splitSentences(text: str) -> list[str]:
        sentences = []
        current = []
        for character in text:
            current.append(character)
            if character in ".!?":
                sentence = "".join(current).strip()
                if sentence:
                    sentences.append(sentence)
                current = []
        tail = "".join(current).strip()
        if tail:
            sentences.append(tail)
        return sentences

