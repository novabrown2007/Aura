"""Aura unified email capability module."""

from __future__ import annotations

from core.modules.base.auraModule import AuraModule
from core.modules.base.moduleAction import ModuleAction
from core.modules.base.moduleIntent import ModuleIntent
from core.modules.base.moduleMetadata import ModuleMetadata
from core.modules.base.moduleSubscription import ModuleSubscription
from core.modules.modulePermissions import ModulePermissions
from core.tools.tool import Tool
from assistant.responses.models import ResponseFollowup
from modules.email.actions import DRAFT_ACTIONS, EMAIL_ACTIONS, INBOX_ACTIONS, LABEL_ACTIONS, SCHEDULE_EMAIL_ACTIONS
from modules.email.emailManager import EmailManager
from modules.email.handlers import EmailEventHandler
from modules.email.intents import DRAFT_INTENTS, EMAIL_INTENTS, INBOX_INTENTS


EMAIL_PERMISSIONS = ModulePermissions(
    capabilityPermissions=(
        "email.read",
        "email.readSensitive",
        "email.draft",
        "email.send",
        "email.schedule",
        "email.label",
        "email.delete",
        "email.archive",
        "email.account.manage",
    ),
    externalApiPermissions=("network:https",),
)


class EmailModule(AuraModule):
    """Unified email management module for multiple providers and accounts."""

    metadata = ModuleMetadata(
        name="email",
        version="1.0.0",
        author="Aura",
        description="Unified multi-account email management system for Gmail, Outlook, IMAP, drafts, labels, search, scheduling, and notifications.",
        permissions=tuple(EMAIL_PERMISSIONS.asList()),
        capabilities=(
            "email.read",
            "email.search",
            "email.draft",
            "email.send",
            "email.schedule",
            "email.labels",
            "email.notifications",
            "email.filter",
            "email.sort",
            "email.multipleAccounts",
        ),
    )

    def __init__(self, context=None):
        super().__init__()
        self.manager: EmailManager | None = None
        self.eventHandler: EmailEventHandler | None = None
        self.permissions = EMAIL_PERMISSIONS
        if context is not None:
            self.initialize(context)

    def initialize(self, context):
        super().initialize(context)
        self.manager = EmailManager(context).initialize(context)
        self.eventHandler = self.manager.eventHandler
        self.permissions = EMAIL_PERMISSIONS
        self._logStartup("email module started.")
        return self

    def startup(self):
        if self.manager is not None:
            self.manager.connectAllAccounts()
            self.manager.syncAll()
        return self

    def shutdown(self):
        if self.manager is not None:
            self.manager.shutdown()

    def __del__(self):
        try:
            self.shutdown()
        except Exception:
            pass

    def getIntents(self):
        return list((*EMAIL_INTENTS, *INBOX_INTENTS, *DRAFT_INTENTS))

    def getActions(self):
        return list((*EMAIL_ACTIONS, *INBOX_ACTIONS, *DRAFT_ACTIONS, *LABEL_ACTIONS, *SCHEDULE_EMAIL_ACTIONS))

    def getSubscriptions(self):
        return [
            ModuleSubscription(eventName="system.started", handler="handleEvent"),
            ModuleSubscription(eventName="schedule.tick", handler="handleEvent"),
            ModuleSubscription(eventName="email.sync.requested", handler="handleEvent"),
            ModuleSubscription(eventName="notification.acknowledged", handler="handleEvent"),
            ModuleSubscription(eventName="conversation.confirmation.received", handler="handleEvent"),
        ]

    def getPermissions(self):
        return self.permissions

    def getTools(self):
        return [
            Tool(
                name="email.listAccounts",
                description="List connected email accounts.",
                parameters={},
                module="email",
                method="listAccounts",
                safe=True,
                offlineAllowed=True,
                requiredPermissions=("email.read",),
                riskLevel="LOW",
            ),
            Tool(
                name="email.connectAccount",
                description="Connect a new email account.",
                parameters={"emailAddress": {"type": "string"}, "displayName": {"type": "string"}, "providerType": {"type": "string"}, "isDefault": {"type": "boolean"}},
                requiredParameters=("emailAddress",),
                module="email",
                method="connectAccount",
                safe=False,
                offlineAllowed=True,
                confirmRequired=True,
                requiredPermissions=("email.account.manage",),
                riskLevel="MODERATE",
            ),
            Tool(
                name="email.setDefaultAccount",
                description="Select the default email account.",
                parameters={"accountId": {"type": "string"}},
                requiredParameters=("accountId",),
                module="email",
                method="setDefaultAccount",
                safe=True,
                offlineAllowed=True,
                requiredPermissions=("email.account.manage",),
                riskLevel="LOW",
            ),
            Tool(
                name="email.listInbox",
                description="List inbox messages.",
                parameters={"accountId": {"type": "string"}, "limit": {"type": "integer"}, "unreadOnly": {"type": "boolean"}, "query": {"type": "string"}, "sortMode": {"type": "string"}},
                module="email",
                method="listInbox",
                safe=True,
                offlineAllowed=True,
                requiredPermissions=("email.read",),
                riskLevel="LOW",
            ),
            Tool(
                name="email.readEmail",
                description="Read a single email.",
                parameters={"accountId": {"type": "string"}, "messageId": {"type": "string"}},
                requiredParameters=("messageId",),
                module="email",
                method="readEmail",
                safe=True,
                offlineAllowed=True,
                requiredPermissions=("email.read",),
                riskLevel="LOW",
            ),
            Tool(
                name="email.searchEmails",
                description="Search all connected email accounts.",
                parameters={"query": {"type": "string"}, "accountId": {"type": "string"}, "limit": {"type": "integer"}},
                requiredParameters=("query",),
                module="email",
                method="searchEmails",
                safe=True,
                offlineAllowed=True,
                requiredPermissions=("email.search",),
                riskLevel="LOW",
            ),
            Tool(
                name="email.listDrafts",
                description="List saved drafts.",
                parameters={"accountId": {"type": "string"}},
                module="email",
                method="listDrafts",
                safe=True,
                offlineAllowed=True,
                requiredPermissions=("email.draft",),
                riskLevel="LOW",
            ),
            Tool(
                name="email.createDraft",
                description="Create an email draft.",
                parameters={"accountId": {"type": "string"}, "to": {"type": "array"}, "cc": {"type": "array"}, "bcc": {"type": "array"}, "subject": {"type": "string"}, "body": {"type": "string"}},
                module="email",
                method="createDraft",
                safe=True,
                offlineAllowed=True,
                requiredPermissions=("email.draft",),
                riskLevel="MODERATE",
            ),
            Tool(
                name="email.updateDraft",
                description="Update a draft.",
                parameters={"draftId": {"type": "string"}},
                requiredParameters=("draftId",),
                module="email",
                method="updateDraft",
                safe=True,
                offlineAllowed=True,
                requiredPermissions=("email.draft",),
                riskLevel="MODERATE",
            ),
            Tool(
                name="email.sendEmail",
                description="Send an email or draft.",
                parameters={"accountId": {"type": "string"}, "draftId": {"type": "string"}, "to": {"type": "array"}, "cc": {"type": "array"}, "bcc": {"type": "array"}, "subject": {"type": "string"}, "body": {"type": "string"}},
                module="email",
                method="sendEmail",
                safe=False,
                offlineAllowed=True,
                confirmRequired=True,
                requiredPermissions=("email.send",),
                riskLevel="HIGH",
            ),
            Tool(
                name="email.scheduleEmail",
                description="Schedule an email to send later.",
                parameters={"accountId": {"type": "string"}, "draftId": {"type": "string"}, "sendAt": {"type": "string"}},
                requiredParameters=("sendAt",),
                module="email",
                method="scheduleEmail",
                safe=False,
                offlineAllowed=True,
                confirmRequired=True,
                requiredPermissions=("email.schedule",),
                riskLevel="HIGH",
            ),
            Tool(
                name="email.listLabels",
                description="List labels and tags for an account.",
                parameters={"accountId": {"type": "string"}},
                requiredParameters=("accountId",),
                module="email",
                method="listLabels",
                safe=True,
                offlineAllowed=True,
                requiredPermissions=("email.label",),
                riskLevel="LOW",
            ),
            Tool(
                name="email.applyLabel",
                description="Apply a label to an email.",
                parameters={"accountId": {"type": "string"}, "messageId": {"type": "string"}, "label": {"type": "string"}},
                requiredParameters=("messageId", "label"),
                module="email",
                method="applyLabel",
                safe=True,
                offlineAllowed=True,
                requiredPermissions=("email.label",),
                riskLevel="LOW",
            ),
            Tool(
                name="email.filterEmails",
                description="Filter inbox messages.",
                parameters={"accountId": {"type": "string"}, "sender": {"type": "string"}, "recipient": {"type": "string"}, "labels": {"type": "array"}, "tags": {"type": "array"}, "keywords": {"type": "array"}, "unreadOnly": {"type": "boolean"}},
                module="email",
                method="filterEmails",
                safe=True,
                offlineAllowed=True,
                requiredPermissions=("email.filter",),
                riskLevel="LOW",
            ),
            Tool(
                name="email.sortEmails",
                description="Sort inbox messages.",
                parameters={"accountId": {"type": "string"}, "sortMode": {"type": "string"}, "limit": {"type": "integer"}},
                module="email",
                method="sortEmails",
                safe=True,
                offlineAllowed=True,
                requiredPermissions=("email.sort",),
                riskLevel="LOW",
            ),
            Tool(
                name="email.deleteEmail",
                description="Delete an email message.",
                parameters={"accountId": {"type": "string"}, "messageId": {"type": "string"}},
                requiredParameters=("messageId",),
                module="email",
                method="deleteEmail",
                safe=False,
                offlineAllowed=True,
                confirmRequired=True,
                requiredPermissions=("email.delete",),
                riskLevel="HIGH",
            ),
            Tool(
                name="email.archiveEmail",
                description="Archive an email message.",
                parameters={"accountId": {"type": "string"}, "messageId": {"type": "string"}},
                requiredParameters=("messageId",),
                module="email",
                method="archiveEmail",
                safe=True,
                offlineAllowed=True,
                requiredPermissions=("email.archive",),
                riskLevel="MODERATE",
            ),
        ]

    def handleEvent(self, event):
        if self.manager is None:
            return None
        return self.manager.handleEvent(event)

    def handleIntent(self, intent):
        intentName = getattr(intent, "name", intent)
        data = dict(getattr(intent, "data", {}) or getattr(intent, "arguments", {}) or {})
        if self.manager is None:
            return self._fallback(intentName, data)
        if intentName in {"email.listAccounts", "email.accounts"}:
            payload = {"accounts": self.manager.listAccounts()}
        elif intentName in {"email.connectAccount", "email.account.connect"}:
            payload = self.manager.connectAccount(**data)
        elif intentName in {"email.setDefaultAccount"}:
            payload = self.manager.setDefaultAccount(data.get("accountId", ""))
        elif intentName in {"email.listInbox", "email.inbox"}:
            payload = {"messages": self.manager.listInbox(accountId=data.get("accountId"), limit=int(data.get("limit", 25) or 25), unreadOnly=bool(data.get("unreadOnly", False)), query=str(data.get("query") or ""), sortMode=str(data.get("sortMode") or "NEWEST_FIRST"))}
        elif intentName in {"email.readEmail", "email.read"}:
            payload = self.manager.readEmail(str(data.get("accountId") or ""), str(data.get("messageId") or ""))
        elif intentName in {"email.searchEmails", "email.search"}:
            payload = {"results": self.manager.searchEmails(str(data.get("query") or ""), accountId=data.get("accountId"), limit=int(data.get("limit", 25) or 25))}
        elif intentName in {"email.listDrafts"}:
            payload = {"drafts": self.manager.listDrafts(data.get("accountId"))}
        elif intentName in {"email.createDraft", "email.draft"}:
            fields = dict(data)
            payload = self.manager.createDraft(fields.pop("accountId", ""), **fields)
        elif intentName in {"email.updateDraft"}:
            fields = {k: v for k, v in data.items() if k != "draftId"}
            payload = self.manager.updateDraft(str(data.get("draftId") or ""), **fields)
        elif intentName in {"email.sendEmail", "email.send"}:
            fields = dict(data)
            payload = self.manager.sendEmail(accountId=str(fields.pop("accountId", "")), draftId=str(fields.pop("draftId", "")), **fields)
        elif intentName in {"email.scheduleEmail", "email.schedule"}:
            fields = dict(data)
            payload = self.manager.scheduleEmail(accountId=str(fields.pop("accountId", "")), draftId=str(fields.pop("draftId", "")), sendAt=str(fields.pop("sendAt", "")), **fields)
        elif intentName in {"email.listLabels"}:
            payload = {"labels": self.manager.listLabels(str(data.get("accountId") or ""))}
        elif intentName in {"email.applyLabel"}:
            payload = self.manager.applyLabel(str(data.get("accountId") or ""), str(data.get("messageId") or ""), str(data.get("label") or ""))
        elif intentName in {"email.filterEmails"}:
            payload = {"messages": self.manager.filterEmails(**data)}
        elif intentName in {"email.sortEmails"}:
            payload = {"messages": self.manager.sortEmails(accountId=data.get("accountId"), sortMode=str(data.get("sortMode") or "NEWEST_FIRST"), limit=int(data.get("limit", 25) or 25))}
        elif intentName in {"email.deleteEmail"}:
            payload = self.manager.deleteEmail(str(data.get("accountId") or ""), str(data.get("messageId") or ""))
        elif intentName in {"email.archiveEmail"}:
            payload = self.manager.archiveEmail(str(data.get("accountId") or ""), str(data.get("messageId") or ""))
        else:
            raise NotImplementedError(f"{self.metadata.name} does not handle intent {intentName}.")
        return self.manager.buildResponse(intentName, payload if isinstance(payload, dict) else {"result": payload})

    def snapshot(self):
        return self.manager.snapshot() if self.manager is not None else {"available": False, "enabled": False}

    def pollNewMail(self):
        return self.manager.pollNewMail() if self.manager is not None else []

    def processScheduledEmails(self):
        return self.manager.processScheduledEmails() if self.manager is not None else []

    def listAccounts(self):
        return self.manager.listAccounts() if self.manager is not None else []

    def connectAccount(self, **fields):
        return self.manager.connectAccount(**fields) if self.manager is not None else fields

    def setDefaultAccount(self, accountId: str):
        return self.manager.setDefaultAccount(accountId) if self.manager is not None else {"accountId": accountId}

    def removeAccount(self, accountId: str):
        return self.manager.removeAccount(accountId) if self.manager is not None else {"accountId": accountId}

    def listInbox(self, **fields):
        return self.manager.listInbox(**fields) if self.manager is not None else []

    def listUnread(self, accountId: str | None = None, limit: int = 25):
        return self.manager.listUnread(accountId=accountId, limit=limit) if self.manager is not None else []

    def readEmail(self, accountId: str, messageId: str):
        return self.manager.readEmail(accountId, messageId) if self.manager is not None else None

    def searchEmails(self, query: str, accountId: str | None = None, limit: int = 25):
        return self.manager.searchEmails(query, accountId=accountId, limit=limit) if self.manager is not None else []

    def createDraft(self, accountId: str = "", **fields):
        if self.manager is None:
            return fields
        payload = dict(fields)
        if not accountId:
            accountId = str(payload.pop("accountId", ""))
        else:
            payload.pop("accountId", None)
        return self.manager.createDraft(accountId, **payload)

    def updateDraft(self, draftId: str, **fields):
        if self.manager is None:
            return fields
        payload = dict(fields)
        payload.pop("draftId", None)
        return self.manager.updateDraft(draftId, **payload)

    def listDrafts(self, accountId: str | None = None):
        return self.manager.listDrafts(accountId) if self.manager is not None else []

    def sendEmail(self, accountId: str = "", draftId: str = "", **fields):
        if self.manager is None:
            return fields
        payload = dict(fields)
        if not accountId:
            accountId = str(payload.pop("accountId", ""))
        else:
            payload.pop("accountId", None)
        if not draftId:
            draftId = str(payload.pop("draftId", ""))
        else:
            payload.pop("draftId", None)
        return self.manager.sendEmail(accountId=accountId, draftId=draftId, **payload)

    def scheduleEmail(self, accountId: str = "", draftId: str = "", sendAt: str = "", **fields):
        if self.manager is None:
            return fields
        payload = dict(fields)
        if not accountId:
            accountId = str(payload.pop("accountId", ""))
        else:
            payload.pop("accountId", None)
        if not draftId:
            draftId = str(payload.pop("draftId", ""))
        else:
            payload.pop("draftId", None)
        if not sendAt:
            sendAt = str(payload.pop("sendAt", ""))
        else:
            payload.pop("sendAt", None)
        return self.manager.scheduleEmail(accountId=accountId, draftId=draftId, sendAt=sendAt, **payload)

    def listLabels(self, accountId: str):
        return self.manager.listLabels(accountId) if self.manager is not None else []

    def applyLabel(self, accountId: str, messageId: str, label: str):
        return self.manager.applyLabel(accountId, messageId, label) if self.manager is not None else None

    def filterEmails(self, **criteria):
        return self.manager.filterEmails(**criteria) if self.manager is not None else []

    def sortEmails(self, **criteria):
        return self.manager.sortEmails(**criteria) if self.manager is not None else []

    def deleteEmail(self, accountId: str, messageId: str):
        return self.manager.deleteEmail(accountId, messageId) if self.manager is not None else None

    def archiveEmail(self, accountId: str, messageId: str):
        return self.manager.archiveEmail(accountId, messageId) if self.manager is not None else None

    def getInboxView(self, accountId: str | None = None, limit: int = 25):
        return self.manager.getInboxView(accountId=accountId, limit=limit) if self.manager is not None else {}

    def getMessageView(self, accountId: str, messageId: str):
        return self.manager.getMessageView(accountId, messageId) if self.manager is not None else {}

    def getDraftView(self, accountId: str | None = None):
        return self.manager.getDraftView(accountId) if self.manager is not None else {}

    def getAccountView(self):
        return self.manager.getAccountView() if self.manager is not None else {}

    def getFilterView(self):
        return self.manager.getFilterView() if self.manager is not None else {}

    def getScheduleView(self):
        return self.manager.getScheduleView() if self.manager is not None else {}

    def _fallback(self, intentName: str, data: dict):
        if intentName in {"email.listAccounts", "email.accounts"}:
            return {"spokenText": "No email accounts are connected.", "uiText": "No accounts available.", "notifications": [], "actions": [], "metadata": {"provider": "email"}, "followups": []}
        if intentName in {"email.listInbox", "email.inbox"}:
            return {"spokenText": "Your inbox is empty.", "uiText": "Inbox is empty.", "notifications": [], "actions": [], "metadata": {"provider": "email"}, "followups": []}
        if intentName in {"email.createDraft", "email.draft"}:
            return {"spokenText": "Draft created.", "uiText": "Draft saved.", "notifications": [], "actions": [], "metadata": {"provider": "email"}, "followups": [ResponseFollowup(prompt="Who should I send it to?").asDict()]}
        return {"spokenText": "Email updated.", "uiText": "Email updated.", "notifications": [], "actions": [], "metadata": {"provider": "email"}, "followups": []}


def createModule(context=None):
    """Create the email module."""

    return EmailModule(context)
