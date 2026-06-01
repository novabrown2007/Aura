"""SQLite persistence for Aura email state."""

from __future__ import annotations

import json
import atexit
import sqlite3
from pathlib import Path
from typing import Any


class SQLiteEmailStore:
    """Persist email accounts, messages, drafts, schedules, and labels."""

    def __init__(self, path: str | Path):
        self.path = Path(path)
        self.connection: sqlite3.Connection | None = None

    def initialize(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.connection = sqlite3.connect(str(self.path))
        self.connection.row_factory = sqlite3.Row
        self._ensureSchema()
        atexit.register(self.close)
        return self

    def close(self):
        if self.connection is not None:
            self.connection.close()
            self.connection = None

    def __del__(self):
        try:
            self.close()
        except Exception:
            pass

    def upsertAccount(self, account: dict[str, Any]):
        self._execute(
            """
            insert into email_accounts(account_id, payload, updated_at)
            values(?, ?, ?)
            on conflict(account_id) do update set payload=excluded.payload, updated_at=excluded.updated_at
            """,
            (account.get("accountId"), json.dumps(account), account.get("lastSyncTime") or ""),
        )

    def listAccounts(self):
        return [json.loads(row["payload"]) for row in self._fetchAll("select payload from email_accounts order by account_id")]

    def upsertMessage(self, message: dict[str, Any]):
        self._execute(
            """
            insert into email_messages(message_id, account_id, payload, updated_at)
            values(?, ?, ?, ?)
            on conflict(message_id) do update set payload=excluded.payload, updated_at=excluded.updated_at
            """,
            (message.get("messageId"), message.get("accountId"), json.dumps(message), message.get("receivedAt") or message.get("sentAt") or ""),
        )

    def listMessages(self, accountId: str | None = None):
        if accountId:
            rows = self._fetchAll("select payload from email_messages where account_id = ? order by updated_at desc", (accountId,))
        else:
            rows = self._fetchAll("select payload from email_messages order by updated_at desc")
        return [json.loads(row["payload"]) for row in rows]

    def upsertDraft(self, draft: dict[str, Any]):
        self._execute(
            """
            insert into email_drafts(draft_id, account_id, payload, updated_at)
            values(?, ?, ?, ?)
            on conflict(draft_id) do update set payload=excluded.payload, updated_at=excluded.updated_at
            """,
            (draft.get("draftId"), draft.get("accountId"), json.dumps(draft), draft.get("updatedAt") or draft.get("createdAt") or ""),
        )

    def listDrafts(self, accountId: str | None = None):
        if accountId:
            rows = self._fetchAll("select payload from email_drafts where account_id = ? order by updated_at desc", (accountId,))
        else:
            rows = self._fetchAll("select payload from email_drafts order by updated_at desc")
        return [json.loads(row["payload"]) for row in rows]

    def upsertScheduledEmail(self, scheduledEmail: dict[str, Any]):
        self._execute(
            """
            insert into email_scheduled_emails(scheduled_email_id, account_id, payload, send_at, state)
            values(?, ?, ?, ?, ?)
            on conflict(scheduled_email_id) do update set payload=excluded.payload, send_at=excluded.send_at, state=excluded.state
            """,
            (
                scheduledEmail.get("scheduledEmailId"),
                (scheduledEmail.get("draft") or {}).get("accountId", ""),
                json.dumps(scheduledEmail),
                scheduledEmail.get("sendAt") or "",
                scheduledEmail.get("state") or "PENDING",
            ),
        )

    def listScheduledEmails(self):
        return [json.loads(row["payload"]) for row in self._fetchAll("select payload from email_scheduled_emails order by send_at")]

    def upsertLabel(self, accountId: str, label: dict[str, Any]):
        key = f"{accountId}:{label.get('labelId') or label.get('name')}"
        self._execute(
            """
            insert into email_labels(label_key, account_id, payload)
            values(?, ?, ?)
            on conflict(label_key) do update set payload=excluded.payload
            """,
            (key, accountId, json.dumps(label)),
        )

    def listLabels(self, accountId: str | None = None):
        if accountId:
            rows = self._fetchAll("select payload from email_labels where account_id = ? order by label_key", (accountId,))
        else:
            rows = self._fetchAll("select payload from email_labels order by label_key")
        return [json.loads(row["payload"]) for row in rows]

    def setSyncState(self, accountId: str, timestamp: str):
        self._execute(
            """
            insert into email_sync_state(account_id, last_sync_at)
            values(?, ?)
            on conflict(account_id) do update set last_sync_at=excluded.last_sync_at
            """,
            (accountId, timestamp),
        )

    def getSyncState(self, accountId: str):
        row = self._fetchOne("select last_sync_at from email_sync_state where account_id = ?", (accountId,))
        return row["last_sync_at"] if row else ""

    def _ensureSchema(self):
        self._execute(
            """
            create table if not exists email_accounts(
                account_id text primary key,
                payload text not null,
                updated_at text not null
            )
            """
        )
        self._execute(
            """
            create table if not exists email_messages(
                message_id text primary key,
                account_id text not null,
                payload text not null,
                updated_at text not null
            )
            """
        )
        self._execute(
            """
            create table if not exists email_drafts(
                draft_id text primary key,
                account_id text not null,
                payload text not null,
                updated_at text not null
            )
            """
        )
        self._execute(
            """
            create table if not exists email_scheduled_emails(
                scheduled_email_id text primary key,
                account_id text not null,
                payload text not null,
                send_at text not null,
                state text not null
            )
            """
        )
        self._execute(
            """
            create table if not exists email_labels(
                label_key text primary key,
                account_id text not null,
                payload text not null
            )
            """
        )
        self._execute(
            """
            create table if not exists email_sync_state(
                account_id text primary key,
                last_sync_at text not null
            )
            """
        )

    def _execute(self, query: str, params: tuple = ()):
        if self.connection is None:
            self.initialize()
        assert self.connection is not None
        with self.connection:
            self.connection.execute(query, params)

    def _fetchOne(self, query: str, params: tuple = ()):
        if self.connection is None:
            self.initialize()
        assert self.connection is not None
        cursor = self.connection.execute(query, params)
        return cursor.fetchone()

    def _fetchAll(self, query: str, params: tuple = ()):
        if self.connection is None:
            self.initialize()
        assert self.connection is not None
        cursor = self.connection.execute(query, params)
        return cursor.fetchall()
