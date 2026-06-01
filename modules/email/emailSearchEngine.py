"""Email search across multiple accounts."""

from __future__ import annotations

from typing import Any


class EmailSearchEngine:
    """Search all connected accounts using provider or cached results."""

    def __init__(self, context=None, connectionManager=None, inboxManager=None):
        self.context = context
        self.connectionManager = connectionManager
        self.inboxManager = inboxManager
        self.logger = getattr(getattr(context, "logger", None), "getChild", lambda *_: None)("Email.Search") if getattr(context, "logger", None) else None

    def searchEmails(self, query: str, accountId: str | None = None, limit: int = 25):
        query = str(query or "").strip()
        results = []
        seen = set()
        accounts = []
        if self.inboxManager is not None and accountId is not None:
            accounts = [accountId]
        elif self.connectionManager is not None and self.connectionManager.accountManager is not None:
            accounts = [account.accountId for account in self.connectionManager.accountManager.accounts.values()]
        for currentAccountId in accounts:
            provider = self.connectionManager.getProvider(currentAccountId) if self.connectionManager is not None else None
            if provider is None:
                continue
            for item in provider.searchEmails(currentAccountId, query):
                key = (currentAccountId, item.get("messageId"))
                if key in seen:
                    continue
                seen.add(key)
                results.append(item)
        if not results and self.inboxManager is not None:
            results = self.inboxManager.listInbox(accountId=accountId, limit=limit, filters={"keywords": [query]} if query else None)
        return results[: max(0, int(limit or 25))]
