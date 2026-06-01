"""Account selector payload for the Windows interface."""

from __future__ import annotations


class EmailAccountView:
    """Render email accounts for the desktop layer."""

    def __init__(self, accounts=None):
        self.accounts = list(accounts or [])

    def render(self):
        return {
            "title": "Email Accounts",
            "count": len(self.accounts),
            "accounts": [
                {
                    "accountId": account.get("accountId"),
                    "emailAddress": account.get("emailAddress"),
                    "displayName": account.get("displayName"),
                    "providerType": account.get("providerType"),
                    "connectionState": account.get("connectionState"),
                    "isDefault": bool(account.get("isDefault", False)),
                }
                for account in self.accounts
            ],
        }
