"""Test package bootstrap for Aura."""

from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from testing.debugging import AssistantConsole, EventTracer, IntentDebugger, SessionDebugger, TracedEvent
from testing.harnesses import IntegrationTester, IntentTester, VoiceTester, WorkflowTester
from testing.mock import MockNotifications, MockUser, MockVoiceInput
from testing.simulation import AssistantSimulator, WorkflowSimulator

__all__ = [
    "AssistantConsole",
    "AssistantSimulator",
    "EventTracer",
    "IntegrationTester",
    "IntentDebugger",
    "IntentTester",
    "MockNotifications",
    "MockUser",
    "MockVoiceInput",
    "SessionDebugger",
    "TracedEvent",
    "VoiceTester",
    "WorkflowSimulator",
    "WorkflowTester",
]
