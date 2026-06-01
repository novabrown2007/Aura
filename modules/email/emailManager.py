"""Central orchestration for Aura's unified email system."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from assistant.responses.models import ResponseFollowup
from modules.email.emailAccountManager import EmailAccountManager
from modules.email.emailActionExecutor import EmailActionExecutor
from modules.email.emailConnectionManager import EmailConnectionManager
from modules.email.emailDraftManager import EmailDraftManager
from modules.email.emailFilterEngine import EmailFilterEngine
from modules.email.emailInboxManager import EmailInboxManager
from modules.email.emailLabelManager import EmailLabelManager
from modules.email.emailNotificationManager import EmailNotificationManager
from modules.email.emailScheduleManager import EmailScheduleManager
from modules.email.emailSearchEngine import EmailSearchEngine
from modules.email.emailSendManager import EmailSendManager
from modules.email.emailSortEngine import EmailSortEngine
from modules.email.monitoring import InboxMonitor, NewEmailMonitor
from modules.email.handlers import EmailEventHandler
from modules.email.models import EmailAccount, EmailConnectionState, EmailDraft, EmailFilter, EmailMessage, EmailProviderType, EmailSortMode
from modules.email.storage import SQLiteEmailStore


class EmailManager:
    """Coordinate providers, accounts, inboxes, drafts, scheduling, and notifications."""

    def __init__(self, context=None):
        self.context = context
        self.logger = context.logger.getChild("Email") if context and getattr(context, "logger", None) else None
        self.enabled = bool(self._configBool("email.emailEnabled", True))
        self.monitoringEnabled = bool(self._configBool("email.emailMonitoringEnabled", True))
        self.syncIntervalSeconds = int(self._configValue("email.emailSyncIntervalSeconds", 60))
        self.notificationsEnabled = bool(self._configBool("email.emailNotificationsEnabled", True))
        self.cacheEnabled = bool(self._configBool("email.emailCacheEnabled", True))
        self.requireConfirmationToSend = bool(self._configBool("email.emailRequireConfirmationToSend", True))
        self.requireConfirmationToDelete = bool(self._configBool("email.emailRequireConfirmationToDelete", True))
        self.defaultAccountId = str(self._configValue("email.emailDefaultAccount", "") or "")
        self.store = SQLiteEmailStore(self._storagePath()).initialize() if self.cacheEnabled else None
        self.accountManager = EmailAccountManager(context, store=self.store)
        self.connectionManager = EmailConnectionManager(context, accountManager=self.accountManager, store=self.store)
        self.inboxManager = EmailInboxManager(context, connectionManager=self.connectionManager, store=self.store)
        self.draftManager = EmailDraftManager(context, store=self.store)
        self.sendManager = EmailSendManager(context, connectionManager=self.connectionManager, draftManager=self.draftManager)
        self.scheduleManager = EmailScheduleManager(context, sendManager=self.sendManager, store=self.store)
        self.labelManager = EmailLabelManager(context, connectionManager=self.connectionManager, store=self.store)
        self.notificationManager = EmailNotificationManager(context)
        self.filterEngine = EmailFilterEngine()
        self.sortEngine = EmailSortEngine()
        self.searchEngine = EmailSearchEngine(context, connectionManager=self.connectionManager, inboxManager=self.inboxManager)
        self.actionExecutor = EmailActionExecutor(self)
        self.eventHandler = EmailEventHandler(context, self)
        self.monitor = InboxMonitor(context, self.inboxManager)
        self.newEmailMonitor = NewEmailMonitor(context, self.inboxManager, self.notificationManager)
        self.initialized = False

    def initialize(self, context=None):
        if context is not None:
            self.context = context
        if self.context is None:
            return self
        self.logger = self.context.logger.getChild("Email") if getattr(self.context, "logger", None) else None
        self.accountManager.initialize(self.context)
        self.connectionManager.initialize(self.context)
        self.inboxManager.initialize(self.context)
        self.draftManager.initialize(self.context)
        self.scheduleManager.initialize(self.context)
        self.connectAllAccounts()
        self.syncAll()
        self.eventHandler.subscribe()
        self.initialized = True
        self._log("Email manager initialized.")
        return self

    def shutdown(self):
        self.eventHandler.unsubscribe()
        if self.store is not None:
            self.store.close()
            self.store = None
        tempdir = getattr(self.context, "_emailTempdir", None)
        if tempdir is not None:
            try:
                tempdir.cleanup()
            except Exception:
                pass
            try:
                self.context._emailTempdir = None
            except Exception:
                pass
        self._log("Email manager shut down.")

    def __del__(self):
        try:
            self.shutdown()
        except Exception:
            pass

    def handleEvent(self, event):
        return self.eventHandler.handleEvent(event)

    def connectAccount(self, emailAddress: str, displayName: str = "", providerType: str = EmailProviderType.UNKNOWN, isDefault: bool = False, syncEnabled: bool = True, metadata: dict[str, Any] | None = None):
        account = self.accountManager.createAccount(emailAddress, displayName=displayName, providerType=providerType, isDefault=isDefault, syncEnabled=syncEnabled, metadata=metadata)
        return self.connectionManager.connectAccount(account).asDict()

    def registerAccount(self, account):
        return self.connectionManager.connectAccount(account).asDict()

    def setDefaultAccount(self, accountId: str):
        selected = self.accountManager.setDefaultAccount(accountId)
        return selected

    def removeAccount(self, accountId: str):
        return self.accountManager.removeAccount(accountId)

    def listAccounts(self):
        return self.accountManager.listAccounts()

    def connectAllAccounts(self):
        return [account.asDict() for account in self.connectionManager.connectAll()]

    def sync(self, accountId: str | None = None):
        if accountId:
            return self.inboxManager.syncAccount(str(accountId))
        return self.syncAll()

    def syncAll(self):
        results = []
        for account in self.accountManager.accounts.values():
            results.extend(self.inboxManager.syncAccount(account.accountId))
        return results

    def listInbox(self, accountId: str | None = None, limit: int = 25, unreadOnly: bool = False, query: str = "", sortMode: str = "NEWEST_FIRST", filters: dict[str, Any] | None = None):
        filters = dict(filters or {})
        if unreadOnly:
            filters["unreadOnly"] = True
        if query:
            filters.setdefault("keywords", [query])
        if accountId and not filters.get("accountId"):
            filters["accountId"] = accountId
        messages = self.inboxManager.listInbox(accountId=accountId, limit=limit, filters=filters if filters else None, sortMode=sortMode)
        return messages

    def listUnread(self, accountId: str | None = None, limit: int = 25):
        return self.inboxManager.listUnread(accountId=accountId, limit=limit)

    def readEmail(self, accountId: str, messageId: str):
        message = self.inboxManager.readEmail(accountId, messageId)
        return message

    def searchEmails(self, query: str, accountId: str | None = None, limit: int = 25):
        return self.searchEngine.searchEmails(query, accountId=accountId, limit=limit)

    def createDraft(self, accountId: str = "", **fields):
        draft = self.draftManager.createDraft(accountId, **fields)
        return draft.asDict()

    def updateDraft(self, draftId: str, **fields):
        draft = self.draftManager.updateDraft(draftId, **fields)
        return draft.asDict() if draft is not None else None

    def listDrafts(self, accountId: str | None = None):
        return self.draftManager.listDrafts(accountId)

    def sendEmail(self, accountId: str = "", draftId: str = "", **fields):
        payload = self.sendManager.sendEmail(accountId=accountId, draftId=draftId, **fields)
        return payload

    def scheduleEmail(self, accountId: str = "", draftId: str = "", sendAt: str = "", **fields):
        scheduled = self.scheduleManager.scheduleEmail(accountId=accountId, draftId=draftId, sendAt=sendAt, **fields)
        return scheduled.asDict()

    def processScheduledEmails(self):
        return self.scheduleManager.processDueEmails()

    def listScheduledEmails(self):
        return self.scheduleManager.listScheduledEmails()

    def listLabels(self, accountId: str):
        return self.labelManager.listLabels(accountId)

    def applyLabel(self, accountId: str, messageId: str, label: str):
        return self.labelManager.applyLabel(accountId, messageId, label)

    def removeLabel(self, accountId: str, messageId: str, label: str):
        return self.labelManager.removeLabel(accountId, messageId, label)

    def deleteEmail(self, accountId: str, messageId: str):
        return self.inboxManager.deleteEmail(accountId, messageId)

    def archiveEmail(self, accountId: str, messageId: str):
        return self.inboxManager.archiveEmail(accountId, messageId)

    def filterEmails(self, **criteria):
        messages = self.listInbox(accountId=criteria.get("accountId"), limit=int(criteria.get("limit", 100) or 100))
        return self.filterEngine.apply(messages, criteria)

    def sortEmails(self, accountId: str | None = None, sortMode: str = "NEWEST_FIRST", limit: int = 25):
        return self.listInbox(accountId=accountId, limit=limit, sortMode=sortMode)

    def pollNewMail(self):
        return self.newEmailMonitor.poll() if self.newEmailMonitor is not None else []

    def markNotificationAcknowledged(self, payload: dict[str, Any]):
        return payload

    def handleConfirmation(self, payload: dict[str, Any]):
        return payload

    def snapshot(self):
        accounts = self.listAccounts()
        inboxCounts = {account.get("accountId"): len(self.listInbox(account.get("accountId"), limit=200)) for account in accounts}
        return {
            "available": True,
            "enabled": self.enabled,
            "accounts": accounts,
            "inboxCounts": inboxCounts,
            "drafts": self.listDrafts(),
            "scheduledEmails": self.listScheduledEmails(),
            "labels": {account.get("accountId"): self.listLabels(account.get("accountId")) for account in accounts},
            "notifications": self.notificationManager.snapshot(),
            "connections": self.connectionManager.snapshot(),
            "monitoringEnabled": self.monitoringEnabled,
            "syncIntervalSeconds": self.syncIntervalSeconds,
        }

    def buildResponse(self, action: str = "", payload: dict[str, Any] | None = None):
        payload = dict(payload or {})
        accounts = payload.get("accounts") or self.listAccounts()
        inbox = payload.get("messages") or payload.get("inbox") or []
        draft = payload.get("draft") or {}
        scheduled = payload.get("scheduled") or {}
        if action == "email.listAccounts":
            spoken = f"You have {len(accounts)} connected email account{'' if len(accounts) == 1 else 's'}."
            uiText = self._formatAccounts(accounts)
        elif action == "email.listInbox":
            spoken = f"You have {len(inbox)} email{'' if len(inbox) == 1 else 's'} in view."
            uiText = self._formatInbox(inbox)
        elif action == "email.readEmail":
            spoken = f"Reading {payload.get('subject') or 'email'}."
            uiText = self._formatMessage(payload)
        elif action == "email.searchEmails":
            spoken = f"I found {len(payload.get('results') or [])} matching email{'' if len((payload.get('results') or [])) == 1 else 's'}."
            uiText = self._formatInbox(payload.get("results") or [])
        elif action == "email.createDraft":
            spoken = "Draft created."
            uiText = self._formatDraft(draft)
        elif action == "email.sendEmail":
            spoken = "Email sent."
            uiText = self._formatMessage(payload)
        elif action == "email.scheduleEmail":
            spoken = "Email scheduled."
            uiText = self._formatSchedule(scheduled or payload)
        else:
            spoken = "Email updated."
            uiText = self._formatInbox(inbox) if inbox else self._formatAccounts(accounts)
        notifications = payload.get("notifications") or []
        actions = [action] if action else []
        metadata = {
            "provider": "email",
            "action": action,
            "timestamp": self._now(),
            "accounts": len(accounts),
        }
        followups = []
        if action == "email.createDraft" and not draft.get("to"):
            followups.append(ResponseFollowup(prompt="Who should I send it to?").asDict())
        return {
            "spokenText": spoken,
            "uiText": uiText,
            "notifications": notifications,
            "actions": actions,
            "metadata": metadata,
            "followups": followups,
        }

    def getInboxView(self, accountId: str | None = None, limit: int = 25):
        from interface.desktop.windows.email.emailInboxView import EmailInboxView

        return EmailInboxView(self.listInbox(accountId=accountId, limit=limit), self.listAccounts()).render()

    def getMessageView(self, accountId: str, messageId: str):
        from interface.desktop.windows.email.emailMessageView import EmailMessageView

        return EmailMessageView(self.readEmail(accountId, messageId)).render()

    def getDraftView(self, accountId: str | None = None):
        from interface.desktop.windows.email.emailDraftView import EmailDraftView

        return EmailDraftView(self.listDrafts(accountId)).render()

    def getAccountView(self):
        from interface.desktop.windows.email.emailAccountView import EmailAccountView

        return EmailAccountView(self.listAccounts()).render()

    def getFilterView(self):
        from interface.desktop.windows.email.emailFilterView import EmailFilterView

        return EmailFilterView().render()

    def getScheduleView(self):
        from interface.desktop.windows.email.emailScheduleView import EmailScheduleView

        return EmailScheduleView(self.listScheduledEmails()).render()

    def _loadConfiguredAccounts(self):
        configured = self._configValue("email.accounts", [])
        if not isinstance(configured, list):
            return
        for entry in configured:
            if isinstance(entry, dict) and entry.get("emailAddress"):
                self.accountManager.createAccount(
                    entry.get("emailAddress", ""),
                    displayName=entry.get("displayName", ""),
                    providerType=entry.get("providerType", EmailProviderType.UNKNOWN),
                    isDefault=bool(entry.get("isDefault", False)),
                    syncEnabled=bool(entry.get("syncEnabled", True)),
                    metadata=dict(entry.get("metadata") or {}),
                )

    def _storagePath(self):
        configured = self._configValue("email.databasePath", None)
        if configured:
            return str(configured)
        return str(Path.home() / ".aura" / "email.sqlite3")

    def _formatAccounts(self, accounts):
        lines = ["Email Accounts:"]
        for account in accounts[:10]:
            lines.append(
                f"- {account.get('displayName') or account.get('emailAddress') or account.get('accountId')}"
                f" [{account.get('providerType')}] {account.get('connectionState')}"
            )
        return "\n".join(lines)

    def _formatInbox(self, messages):
        lines = ["Inbox:"]
        for message in messages[:10]:
            lines.append(
                f"- {message.get('sender') or 'Unknown'}: {message.get('subject') or 'No subject'}"
            )
        return "\n".join(lines)

    def _formatMessage(self, message):
        if not message:
            return "No email selected."
        return "\n".join(
            [
                f"From: {message.get('sender') or 'Unknown'}",
                f"Subject: {message.get('subject') or 'No subject'}",
                f"Body: {message.get('body') or message.get('snippet') or ''}",
            ]
        )

    def _formatDraft(self, draft):
        return "\n".join(
            [
                f"To: {', '.join(draft.get('to') or [])}",
                f"Subject: {draft.get('subject') or 'No subject'}",
                f"Body: {draft.get('body') or ''}",
            ]
        )

    def _formatSchedule(self, scheduled):
        draft = scheduled.get("draft") if isinstance(scheduled, dict) else {}
        return "\n".join(
            [
                f"Send at: {scheduled.get('sendAt') or ''}",
                f"Subject: {(draft or {}).get('subject') or ''}",
            ]
        )

    def _log(self, message: str):
        if self.logger:
            self.logger.info(message)

    def _configValue(self, key: str, default=None):
        config = getattr(self.context, "config", None)
        if config is None or not hasattr(config, "get"):
            return default
        for path in (f"email.{key}", key):
            try:
                value = config.get(path, None)
            except Exception:
                value = None
            if value is not None:
                return value
        return default

    def _configBool(self, key: str, default: bool = False) -> bool:
        value = self._configValue(key, default)
        if isinstance(value, bool):
            return value
        return str(value).strip().lower() in {"1", "true", "yes", "on"}

    @staticmethod
    def _now():
        return datetime.now(timezone.utc).isoformat()
