"""Account registry for Aura's unified email system."""

from __future__ import annotations

from typing import Any

from modules.email.models import EmailAccount, EmailConnectionState, EmailProviderType


class EmailAccountManager:
    """Manage multiple connected email accounts."""

    def __init__(self, context=None, store=None):
        self.context = context
        self.store = store
        logger = getattr(context, "logger", None)
        self.logger = logger.getChild("Email.Accounts") if logger else None
        self.accounts: dict[str, EmailAccount] = {}

    def initialize(self, context=None):
        if context is not None:
            self.context = context
        self._loadConfiguredAccounts()
        self._loadPersistedAccounts()
        return self

    def createAccount(self, emailAddress: str, displayName: str = "", providerType: str = EmailProviderType.UNKNOWN, isDefault: bool = False, syncEnabled: bool = True, metadata: dict[str, Any] | None = None):
        accountId = self._accountIdFor(emailAddress, providerType)
        account = EmailAccount(
            accountId=accountId,
            emailAddress=str(emailAddress or ""),
            displayName=str(displayName or emailAddress or ""),
            providerType=EmailProviderType.normalize(providerType),
            connectionState=EmailConnectionState.DISCONNECTED,
            isDefault=bool(isDefault or not self.getDefaultAccount()),
            syncEnabled=bool(syncEnabled),
            metadata=dict(metadata or {}),
        )
        self.accounts[account.accountId] = account
        if self.store is not None:
            self.store.upsertAccount(account.asDict())
        if account.isDefault:
            self.setDefaultAccount(account.accountId)
        elif not self.getDefaultAccount():
            account.isDefault = True
            if self.store is not None:
                self.store.upsertAccount(account.asDict())
        return account

    def registerAccount(self, account):
        account = EmailAccount.fromDict(account.asDict() if hasattr(account, "asDict") else dict(account or {}))
        if not self.getDefaultAccount() and not account.isDefault:
            account.isDefault = True
        self.accounts[account.accountId] = account
        if self.store is not None:
            self.store.upsertAccount(account.asDict())
        if account.isDefault:
            self.setDefaultAccount(account.accountId)
        return account

    def listAccounts(self):
        return [account.asDict() for account in self.accounts.values()]

    def listConnectedAccounts(self):
        return [account.asDict() for account in self.accounts.values() if account.connectionState == EmailConnectionState.CONNECTED]

    def getAccount(self, accountId: str):
        return self.accounts.get(str(accountId))

    def getDefaultAccount(self):
        for account in self.accounts.values():
            if account.isDefault:
                return account
        return next(iter(self.accounts.values()), None)

    def setDefaultAccount(self, accountId: str):
        accountId = str(accountId or "")
        selected = None
        for account in self.accounts.values():
            account.isDefault = account.accountId == accountId
            if account.isDefault:
                selected = account
        if self.store is not None:
            for account in self.accounts.values():
                self.store.upsertAccount(account.asDict())
        return selected.asDict() if selected is not None else None

    def removeAccount(self, accountId: str):
        account = self.accounts.pop(str(accountId), None)
        if account is not None and account.isDefault and self.accounts:
            next(iter(self.accounts.values())).isDefault = True
        return account.asDict() if account is not None else None

    def connectConfiguredAccounts(self):
        accounts = []
        configAccounts = self._configValue("email.accounts", [])
        if isinstance(configAccounts, list):
            for entry in configAccounts:
                if isinstance(entry, dict) and entry.get("emailAddress"):
                    account = self.createAccount(
                        entry.get("emailAddress", ""),
                        displayName=entry.get("displayName", ""),
                        providerType=entry.get("providerType", EmailProviderType.UNKNOWN),
                        isDefault=bool(entry.get("isDefault", False)),
                        syncEnabled=bool(entry.get("syncEnabled", True)),
                        metadata=dict(entry.get("metadata") or {}),
                    )
                    accounts.append(account)
        return accounts

    def _loadPersistedAccounts(self):
        if self.store is None:
            return
        for entry in self.store.listAccounts():
            account = EmailAccount.fromDict(entry)
            self.accounts[account.accountId] = account

    def _loadConfiguredAccounts(self):
        self.connectConfiguredAccounts()

    def _accountIdFor(self, emailAddress: str, providerType: str):
        base = f"{EmailProviderType.normalize(providerType).lower()}-{str(emailAddress or '').split('@')[0].lower()}"
        candidate = base or f"email-{len(self.accounts) + 1}"
        suffix = 1
        while candidate in self.accounts:
            suffix += 1
            candidate = f"{base}-{suffix}"
        return candidate

    def _configValue(self, key: str, default=None):
        config = getattr(self.context, "config", None)
        if config is None or not hasattr(config, "get"):
            return default
        return config.get(key, default)
