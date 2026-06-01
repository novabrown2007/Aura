"""Inbox monitoring for email change detection."""

from __future__ import annotations


class InboxMonitor:
    """Keep the inbox cache synchronized."""

    def __init__(self, context=None, inboxManager=None):
        self.context = context
        self.inboxManager = inboxManager

    def poll(self):
        results = []
        if self.inboxManager is None or self.inboxManager.connectionManager is None or self.inboxManager.connectionManager.accountManager is None:
            return results
        for account in self.inboxManager.connectionManager.accountManager.accounts.values():
            results.extend(self.inboxManager.syncAccount(account.accountId))
        return results
