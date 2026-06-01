"""General email actions."""

from __future__ import annotations

from core.modules.base.moduleAction import ModuleAction


EMAIL_ACTIONS = (
    ModuleAction(
        name="email.listAccounts",
        description="List connected email accounts.",
        method="listAccounts",
        permissions=("email.read",),
        capabilities=("email.multipleAccounts",),
        target="listAccounts",
    ),
    ModuleAction(
        name="email.connectAccount",
        description="Connect an email account.",
        method="connectAccount",
        parameters={"emailAddress": {"type": "string"}, "providerType": {"type": "string"}},
        requiredParameters=("emailAddress",),
        permissions=("email.account.manage",),
        capabilities=("email.multipleAccounts",),
        target="connectAccount",
    ),
    ModuleAction(
        name="email.setDefaultAccount",
        description="Select the default email account.",
        method="setDefaultAccount",
        parameters={"accountId": {"type": "string"}},
        requiredParameters=("accountId",),
        permissions=("email.account.manage",),
        capabilities=("email.multipleAccounts",),
        target="setDefaultAccount",
    ),
    ModuleAction(
        name="email.listInbox",
        description="List inbox messages.",
        method="listInbox",
        parameters={"accountId": {"type": "string"}, "limit": {"type": "integer"}},
        permissions=("email.read",),
        capabilities=("email.read",),
        target="listInbox",
    ),
    ModuleAction(
        name="email.readEmail",
        description="Read one email message.",
        method="readEmail",
        parameters={"accountId": {"type": "string"}, "messageId": {"type": "string"}},
        requiredParameters=("messageId",),
        permissions=("email.read",),
        capabilities=("email.read",),
        target="readEmail",
    ),
    ModuleAction(
        name="email.searchEmails",
        description="Search email across connected accounts.",
        method="searchEmails",
        parameters={"query": {"type": "string"}, "accountId": {"type": "string"}},
        requiredParameters=("query",),
        permissions=("email.search",),
        capabilities=("email.search",),
        target="searchEmails",
    ),
)
