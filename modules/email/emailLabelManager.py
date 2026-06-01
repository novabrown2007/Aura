"""Label and tag management for email."""

from __future__ import annotations

from typing import Any

from modules.email.models import EmailLabel, EmailTag


class EmailLabelManager:
    """Normalize provider labels and Aura-local tags."""

    def __init__(self, context=None, connectionManager=None, store=None):
        self.context = context
        self.connectionManager = connectionManager
        self.store = store
        self.tags: dict[str, list[EmailTag]] = {}
        self.logger = getattr(getattr(context, "logger", None), "getChild", lambda *_: None)("Email.Labels") if getattr(context, "logger", None) else None

    def listLabels(self, accountId: str):
        provider = self.connectionManager.getProvider(accountId) if self.connectionManager is not None else None
        labels = []
        if provider is not None:
            labels.extend(provider.listLabels(accountId))
        labels.extend([tag.asDict() for tag in self.tags.get(str(accountId), [])])
        if self.store is not None:
            for row in self.store.listLabels(accountId):
                if row not in labels:
                    labels.append(row)
        return labels

    def applyLabel(self, accountId: str, messageId: str, label: str):
        provider = self.connectionManager.getProvider(accountId) if self.connectionManager is not None else None
        if provider is None:
            return None
        message = provider.applyLabel(accountId, messageId, label)
        if message is not None:
            self._persistLabel(accountId, label)
            self._emit("email.label.applied", {"accountId": accountId, "messageId": messageId, "label": label})
        return message

    def removeLabel(self, accountId: str, messageId: str, label: str):
        provider = self.connectionManager.getProvider(accountId) if self.connectionManager is not None else None
        if provider is None:
            return None
        message = provider.removeLabel(accountId, messageId, label)
        return message

    def createTag(self, accountId: str, name: str):
        tag = EmailTag(tagId=self._slug(name), name=str(name or ""))
        self.tags.setdefault(str(accountId), []).append(tag)
        return tag.asDict()

    def listTags(self, accountId: str):
        return [tag.asDict() for tag in self.tags.get(str(accountId), [])]

    def snapshot(self):
        return {"available": True, "tags": {accountId: [tag.asDict() for tag in tags] for accountId, tags in self.tags.items()}}

    def _persistLabel(self, accountId: str, label: str):
        if self.store is not None:
            self.store.upsertLabel(accountId, EmailLabel(labelId=self._slug(label), name=label, system=False).asDict())

    def _emit(self, name: str, payload: dict[str, Any]):
        eventBus = getattr(self.context, "eventManager", None)
        if eventBus is None:
            return None
        try:
            return eventBus.emit(name, payload or {})
        except Exception:
            return None

    @staticmethod
    def _slug(value: str):
        return str(value or "").strip().lower().replace(" ", "-")
