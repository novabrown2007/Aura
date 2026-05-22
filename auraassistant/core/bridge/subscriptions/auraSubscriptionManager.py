"""Subscription routing for Aura Protocol message categories."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
from uuid import uuid4


@dataclass(slots=True, frozen=True)
class AuraSubscription:
    """One category or wildcard subscription."""

    subscriptionId: str
    categories: tuple[str, ...] = field(default_factory=tuple)
    interface: str = ""
    sessionId: str = ""
    wildcard: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)


class AuraSubscriptionManager:
    """Track subscriptions for assistant-facing bridge messages."""

    def __init__(self, context=None):
        self.context = context
        self.subscriptions: dict[str, AuraSubscription] = {}

    def subscribe(
        self,
        categories: str | list[str] | tuple[str, ...] | None = None,
        interface: str = "",
        sessionId: str = "",
        wildcard: bool = False,
        metadata: dict[str, Any] | None = None,
    ) -> AuraSubscription:
        """Register one subscription."""

        if categories is None:
            normalized_categories: tuple[str, ...] = ()
        elif isinstance(categories, str):
            normalized_categories = (categories,)
        else:
            normalized_categories = tuple(str(category) for category in categories)

        subscription = AuraSubscription(
            subscriptionId=uuid4().hex,
            categories=normalized_categories,
            interface=str(interface or ""),
            sessionId=str(sessionId or ""),
            wildcard=bool(wildcard),
            metadata=dict(metadata or {}),
        )
        self.subscriptions[subscription.subscriptionId] = subscription
        return subscription

    def unsubscribe(self, subscriptionId: str) -> bool:
        """Remove one subscription."""

        return self.subscriptions.pop(subscriptionId, None) is not None

    def listSubscriptions(self) -> list[AuraSubscription]:
        """Return all subscriptions."""

        return list(self.subscriptions.values())

    def matchingSubscriptions(self, category: str, interface: str = "", sessionId: str = "") -> list[AuraSubscription]:
        """Return subscriptions that match one category and optional routing scope."""

        matched = []
        for subscription in self.subscriptions.values():
            if subscription.interface and interface and subscription.interface != interface:
                continue
            if subscription.sessionId and sessionId and subscription.sessionId != sessionId:
                continue
            if subscription.wildcard:
                matched.append(subscription)
                continue
            if not subscription.categories:
                continue
            if category in subscription.categories:
                matched.append(subscription)
                continue
            if any(
                registered.endswith(".*") and category.startswith(registered[:-2])
                for registered in subscription.categories
            ):
                matched.append(subscription)
        return matched

