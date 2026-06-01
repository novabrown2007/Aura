"""Inbox operations for Aura's email module."""

from __future__ import annotations

from typing import Any

from modules.email.emailFilterEngine import EmailFilterEngine
from modules.email.emailSortEngine import EmailSortEngine
from modules.email.models import EmailConnectionState


class EmailInboxManager:
    """Fetch, cache, and filter inbox contents."""

    def __init__(self, context=None, connectionManager=None, store=None):
        self.context = context
        self.connectionManager = connectionManager
        self.store = store
        self.filterEngine = EmailFilterEngine()
        self.sortEngine = EmailSortEngine()
        self.logger = getattr(getattr(context, "logger", None), "getChild", lambda *_: None)("Email.Inbox") if getattr(context, "logger", None) else None
        self.cache: dict[str, list[dict[str, Any]]] = {}

    def initialize(self, context=None):
        if context is not None:
            self.context = context
        return self

    def syncAccount(self, accountId: str, limit: int = 50):
        provider = self.connectionManager.getProvider(accountId) if self.connectionManager is not None else None
        if provider is None:
            return []
        messages = [dict(item) for item in provider.listInbox(accountId, limit=limit)]
        self.cache[str(accountId)] = messages
        if self.store is not None:
            for message in messages:
                self.store.upsertMessage(message)
        self._emit("email.inbox.updated", {"accountId": accountId, "count": len(messages)})
        return messages

    def listInbox(self, accountId: str | None = None, limit: int = 25, filters: dict[str, Any] | None = None, sortMode: str | None = None):
        accountIds = [str(accountId)] if accountId else self._accountIds()
        messages = []
        for currentAccountId in accountIds:
            cached = self.cache.get(currentAccountId)
            if cached is None:
                cached = self.syncAccount(currentAccountId, limit=max(limit, 50))
            messages.extend(cached)
        if filters:
            messages = self.filterEngine.apply(messages, filters)
        messages = self.sortEngine.sort(messages, sortMode)
        return messages[: max(0, int(limit or 25))]

    def listUnread(self, accountId: str | None = None, limit: int = 25):
        return self.listInbox(accountId=accountId, limit=limit, filters={"unreadOnly": True}, sortMode="UNREAD_FIRST")

    def readEmail(self, accountId: str, messageId: str):
        provider = self.connectionManager.getProvider(accountId) if self.connectionManager is not None else None
        if provider is None:
            return None
        message = provider.readEmail(accountId, messageId)
        if message is not None:
            self._refreshCache(accountId, message)
            if self.store is not None:
                self.store.upsertMessage(message)
            self._emit("email.read", message)
        return message

    def markRead(self, accountId: str, messageId: str):
        return self.readEmail(accountId, messageId)

    def deleteEmail(self, accountId: str, messageId: str):
        provider = self.connectionManager.getProvider(accountId) if self.connectionManager is not None else None
        if provider is None:
            return None
        message = provider.deleteEmail(accountId, messageId)
        self.cache[str(accountId)] = [item for item in self.cache.get(str(accountId), []) if item.get("messageId") != str(messageId)]
        return message

    def archiveEmail(self, accountId: str, messageId: str):
        provider = self.connectionManager.getProvider(accountId) if self.connectionManager is not None else None
        if provider is None:
            return None
        message = provider.archiveEmail(accountId, messageId)
        self._refreshCache(accountId, message)
        return message

    def getMessage(self, accountId: str, messageId: str):
        for message in self.listInbox(accountId=accountId, limit=500):
            if str(message.get("messageId")) == str(messageId):
                return message
        return None

    def snapshot(self):
        return {
            "available": True,
            "accounts": {accountId: len(messages) for accountId, messages in self.cache.items()},
        }

    def _refreshCache(self, accountId: str, message: dict[str, Any] | None):
        if message is None:
            return
        accountId = str(accountId)
        current = self.cache.get(accountId, [])
        for index, item in enumerate(current):
            if str(item.get("messageId")) == str(message.get("messageId")):
                current[index] = dict(message)
                break
        else:
            current.append(dict(message))
        self.cache[accountId] = current

    def _accountIds(self):
        if self.connectionManager is None or self.connectionManager.accountManager is None:
            return []
        return [account.accountId for account in self.connectionManager.accountManager.accounts.values() if account.connectionState != EmailConnectionState.DISCONNECTED]

    def _emit(self, name: str, payload: dict[str, Any]):
        eventBus = getattr(self.context, "eventManager", None)
        if eventBus is None:
            return None
        try:
            return eventBus.emit(name, payload or {})
        except Exception:
            return None
