"""General email intents."""

from __future__ import annotations

from core.modules.base.moduleIntent import ModuleIntent


EMAIL_INTENTS = (
    ModuleIntent(name="email.listAccounts", description="List connected email accounts.", target="listAccounts"),
    ModuleIntent(name="email.connectAccount", description="Connect a new email account.", target="connectAccount"),
    ModuleIntent(name="email.setDefaultAccount", description="Select the default email account.", target="setDefaultAccount"),
    ModuleIntent(name="email.searchEmails", description="Search email across accounts.", target="searchEmails"),
)
