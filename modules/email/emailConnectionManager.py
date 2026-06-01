"""Email provider connection lifecycle manager."""

from __future__ import annotations

from modules.email.models import EmailConnectionState, EmailProviderType
from modules.email.providers import GmailProvider, ImapSmtpProvider, OutlookProvider


class EmailConnectionManager:
    """Coordinate provider sessions for multiple accounts."""

    def __init__(self, context=None, accountManager=None, store=None):
        self.context = context
        self.accountManager = accountManager
        self.store = store
        logger = getattr(context, "logger", None)
        self.logger = logger.getChild("Email.Connections") if logger else None
        self.providers = {}
        self.providerFactories = {
            EmailProviderType.GMAIL: GmailProvider,
            EmailProviderType.OUTLOOK: OutlookProvider,
            EmailProviderType.IMAP_SMTP: ImapSmtpProvider,
            EmailProviderType.UNKNOWN: ImapSmtpProvider,
        }

    def initialize(self, context=None):
        if context is not None:
            self.context = context
        return self

    def connectAccount(self, account):
        account = self.accountManager.registerAccount(account) if self.accountManager is not None else account
        provider = self._providerFor(account.providerType)
        provider.initialize(self.context)
        connectedAccount = provider.connectAccount(account)
        account.connectionState = EmailConnectionState.CONNECTED
        account.lastSyncTime = connectedAccount.lastSyncTime
        if self.accountManager is not None:
            self.accountManager.accounts[account.accountId] = account
            if self.store is not None:
                self.store.upsertAccount(account.asDict())
        self._emit("email.account.connected", account.asDict())
        return account

    def disconnectAccount(self, accountId: str):
        account = self.accountManager.getAccount(accountId) if self.accountManager is not None else None
        if account is None:
            return None
        account.connectionState = EmailConnectionState.DISCONNECTED
        if self.store is not None:
            self.store.upsertAccount(account.asDict())
        self._emit("email.account.disconnected", account.asDict())
        return account.asDict()

    def refreshToken(self, accountId: str):
        account = self.accountManager.getAccount(accountId) if self.accountManager is not None else None
        if account is None:
            return None
        provider = self._providerFor(account.providerType)
        if not provider.isAvailable():
            account.connectionState = EmailConnectionState.AUTH_EXPIRED
            return account
        return self.connectAccount(account)

    def connectAll(self):
        results = []
        if self.accountManager is None:
            return results
        for account in self.accountManager.accounts.values():
            try:
                results.append(self.connectAccount(account))
            except Exception as error:
                account.connectionState = EmailConnectionState.ERROR
                if self.logger:
                    self.logger.warning(f"Failed to connect email account {account.accountId}: {error}")
        return results

    def getProvider(self, accountId: str):
        account = self.accountManager.getAccount(accountId) if self.accountManager is not None else None
        if account is None:
            return None
        return self._providerFor(account.providerType)

    def snapshot(self):
        return {
            "providers": {
                providerType: provider.snapshot() if hasattr(provider, "snapshot") else {"providerType": providerType}
                for providerType, provider in self.providers.items()
            },
            "accounts": self.accountManager.listAccounts() if self.accountManager is not None else [],
        }

    def _providerFor(self, providerType: str):
        providerType = EmailProviderType.normalize(providerType)
        provider = self.providers.get(providerType)
        if provider is not None:
            return provider
        factory = self.providerFactories.get(providerType, ImapSmtpProvider)
        provider = factory(self.context)
        self.providers[providerType] = provider
        return provider

    def _emit(self, name: str, payload: dict):
        eventBus = getattr(self.context, "eventManager", None)
        if eventBus is None:
            return None
        try:
            return eventBus.emit(name, payload or {})
        except Exception:
            return None
