"""Dispatch email module actions."""

from __future__ import annotations


class EmailActionExecutor:
    """Resolve high-level email actions to manager methods."""

    def __init__(self, manager):
        self.manager = manager

    def execute(self, actionName: str, **arguments):
        actionName = str(actionName or "")
        if actionName == "email.listAccounts":
            return self.manager.listAccounts()
        if actionName == "email.connectAccount":
            return self.manager.connectAccount(**arguments)
        if actionName == "email.setDefaultAccount":
            return self.manager.setDefaultAccount(arguments.get("accountId", ""))
        if actionName == "email.listInbox":
            return self.manager.listInbox(**arguments)
        if actionName == "email.readEmail":
            return self.manager.readEmail(arguments.get("accountId", ""), arguments.get("messageId", ""))
        if actionName == "email.searchEmails":
            return self.manager.searchEmails(arguments.get("query", ""), accountId=arguments.get("accountId"), limit=int(arguments.get("limit", 25) or 25))
        if actionName == "email.listDrafts":
            return self.manager.listDrafts(arguments.get("accountId"))
        if actionName == "email.createDraft":
            return self.manager.createDraft(**arguments)
        if actionName == "email.updateDraft":
            return self.manager.updateDraft(arguments.get("draftId", ""), **{k: v for k, v in arguments.items() if k != "draftId"})
        if actionName == "email.sendEmail":
            return self.manager.sendEmail(**arguments)
        if actionName == "email.scheduleEmail":
            return self.manager.scheduleEmail(**arguments)
        if actionName == "email.listLabels":
            return self.manager.listLabels(arguments.get("accountId", ""))
        if actionName == "email.applyLabel":
            return self.manager.applyLabel(arguments.get("accountId", ""), arguments.get("messageId", ""), arguments.get("label", ""))
        if actionName == "email.filterEmails":
            return self.manager.filterEmails(**arguments)
        if actionName == "email.sortEmails":
            return self.manager.sortEmails(**arguments)
        if actionName == "email.deleteEmail":
            return self.manager.deleteEmail(arguments.get("accountId", ""), arguments.get("messageId", ""))
        if actionName == "email.archiveEmail":
            return self.manager.archiveEmail(arguments.get("accountId", ""), arguments.get("messageId", ""))
        raise NotImplementedError(f"Unsupported email action: {actionName}")
