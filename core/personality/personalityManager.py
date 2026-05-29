"""Controlled personality coordination layer for Aura."""

from __future__ import annotations

import re

from core.personality.behaviorGovernor import BehaviorGovernor
from core.personality.humorEngine import HumorEngine
from core.personality.initiativeManager import InitiativeManager
from core.personality.interactionPolicy import InteractionPolicy
from core.personality.models import AssistantMood, InteractionContext, PersonalityProfile
from core.personality.suggestionEngine import SuggestionEngine
from core.personality.toneManager import ToneManager


class PersonalityManager:
    """Coordinate tone, humor, suggestions, and behavioral boundaries."""

    def __init__(self, context=None, profile: PersonalityProfile | None = None):
        self.context = context
        self.profile = profile or PersonalityProfile.fromContext(context)
        logger = getattr(context, "logger", None)
        self.logger = logger.getChild("Personality") if logger else None
        self.interactionContext = InteractionContext()
        self.mood = AssistantMood()
        self.policy = InteractionPolicy()
        self.governor = BehaviorGovernor(context)
        self.toneManager = ToneManager(self.profile, self.logger)
        self.humorEngine = HumorEngine(self.profile, self.logger)
        self.suggestionEngine = SuggestionEngine(context, self.profile, self.logger)
        self.initiativeManager = InitiativeManager(self.profile, self.logger)
        self.lastHumor = {}
        self.lastSuggestion = {}

        if context is not None:
            context.personalityManager = self

        if self.logger:
            self.logger.info(
                "Personality manager started "
                f"(enabled={self.profile.personalityEnabled}, tone={self.profile.tone}, "
                f"humor={self.profile.humorEnabled}, suggestions={self.profile.suggestionsEnabled})."
            )

    def buildPromptGuidance(self, interactionContext: InteractionContext | None = None) -> str:
        """Return provider-facing style and safety guidance."""

        if not self.profile.personalityEnabled:
            return self.policy.policyText()
        context = interactionContext or self.interactionContext
        return "\n".join(
            [
                self.policy.policyText(),
                f"Tone: {self.toneManager.promptInstructions(context)}",
                (
                    "Personality: light, grounded, helpful. "
                    "Occasional subtle humor is allowed only when it does not distract."
                ),
                "Suggestions must be optional, concise, and never framed as commands.",
            ]
        )

    def handleUserCommand(self, userInput: str) -> str | None:
        """Apply user-controlled personality settings and return an acknowledgement."""

        text = str(userInput or "").lower().strip()
        if not text:
            return None

        if re.search(r"\b(turn off|disable|stop)\b.*\b(jokes?|humou?r)\b", text):
            self.profile.humorEnabled = False
            self._log("policy_update", {"humorEnabled": False})
            return "Understood."
        if re.search(r"\b(turn on|enable)\b.*\b(jokes?|humou?r)\b", text):
            self.profile.humorEnabled = True
            self._log("policy_update", {"humorEnabled": True})
            return "Understood."
        if re.search(r"\b(turn off|disable|stop)\b.*\bsuggestions?\b", text):
            self.profile.suggestionsEnabled = False
            self._log("policy_update", {"suggestionsEnabled": False})
            return "Understood."
        if re.search(r"\b(turn on|enable)\b.*\bsuggestions?\b", text):
            self.profile.suggestionsEnabled = True
            self._log("policy_update", {"suggestionsEnabled": True})
            return "Understood."
        toneMatch = re.search(r"\b(?:set tone to|make (?:your )?tone|be|stay)\s+(casual|professional|concise|brief|developer|voice)\b", text)
        if toneMatch:
            self.toneManager.setTone(toneMatch.group(1))
            self._log("policy_update", {"tone": self.profile.tone})
            return "Understood."
        return None

    def applyToResponse(self, userInput: str, responseText: str, source: str = "llm") -> str:
        """Apply controlled personality after command execution has completed."""

        if not self.profile.personalityEnabled:
            return self.governor.enforce(responseText, self.policy.classifyUserInput(userInput))

        policyDecision = self.policy.classifyUserInput(userInput)
        self._updateInteractionContext(userInput, responseText, source, policyDecision)
        governed = self.governor.enforce(responseText, policyDecision)

        additions: list[str] = []
        if self.governor.canAugment(policyDecision, "humor"):
            humor = self.humorEngine.maybeGenerate(userInput, governed, self.interactionContext)
            self.lastHumor = humor.asDict()
            if humor.applied and humor.text:
                additions.append(humor.text)
                self._log("humor_injected", humor.asDict())

        if (
            self.governor.canAugment(policyDecision, "suggestion")
            and self.initiativeManager.shouldOffer(self.interactionContext, policyDecision)
        ):
            suggestion = self.suggestionEngine.maybeSuggest(userInput, governed, self.interactionContext)
            if suggestion is not None:
                self.lastSuggestion = suggestion.asDict()
                additions.append(suggestion.text)
                self._emit("personality.suggestion.generated", suggestion.asDict())

        finalText = self._combine(governed, additions)
        return self.governor.enforce(finalText, policyDecision)

    def snapshot(self) -> dict:
        """Return personality diagnostics."""

        return {
            "available": True,
            "profile": self.profile.asDict(),
            "mood": self.mood.asDict(),
            "interactionContext": self.interactionContext.asDict(),
            "governor": self.governor.snapshot(),
            "initiative": self.initiativeManager.snapshot(),
            "lastHumor": dict(self.lastHumor),
            "lastSuggestion": dict(self.lastSuggestion),
        }

    def _updateInteractionContext(self, userInput: str, responseText: str, source: str, policyDecision: dict):
        text = str(userInput or "")
        self.interactionContext.lastUserInput = text
        self.interactionContext.lastResponse = str(responseText or "")
        self.interactionContext.interfaceType = "voice" if source in {"voice", "always_active", "push_to_talk"} else "text"
        self.interactionContext.conversationIntensity = min(1.0, max(0.0, len(text.split()) / 80.0))
        self.interactionContext.currentTask = "command" if policyDecision.get("isCommand") else "conversation"
        self.interactionContext.recordActivity("response", {"source": source, "priority": policyDecision.get("priority")})

    @staticmethod
    def _combine(responseText: str, additions: list[str]) -> str:
        if not additions:
            return str(responseText or "").strip()
        base = str(responseText or "").strip()
        extra = " ".join(str(item).strip() for item in additions if str(item).strip())
        if not base:
            return extra
        return f"{base}\n\n{extra}"

    def _emit(self, eventName: str, data: dict):
        eventManager = getattr(self.context, "eventManager", None)
        if eventManager is None:
            return
        try:
            eventManager.emit(eventName, data)
        except Exception as error:
            if self.logger:
                self.logger.warning(f"Personality event emission failed for {eventName}: {error}")

    def _log(self, action: str, details: dict):
        if self.logger:
            self.logger.info(f"Personality {action}: {details}")

