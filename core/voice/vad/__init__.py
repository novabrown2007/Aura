"""Voice activity detection support for Aura."""

from .configuration import VADConfig
from .events import VADEvents
from .models import SpeechSegment, VADResult, VADState
from .silenceTracker import SilenceTracker
from .speechStateManager import SpeechStateManager
from .vadDetector import VADDetector
from .vadManager import VADManager
from .vadSession import VADSession

__all__ = [
    "SilenceTracker",
    "SpeechSegment",
    "SpeechStateManager",
    "VADConfig",
    "VADDetector",
    "VADEvents",
    "VADManager",
    "VADResult",
    "VADSession",
    "VADState",
]

