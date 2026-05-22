"""Automated tests for `fakes` behavior and regression coverage."""

from types import SimpleNamespace
from core.runtime.datetimeUtils import DateTimeUtils


class DictConfig:
    """Defines the `DictConfig` type used by Aura runtime components."""
    def __init__(self, data):
        """Initialize `DictConfig` with required dependencies and internal state."""
        self._data = data
        self.reload_calls = 0

    def get(self, key, default=None):
        """Return `get` data from the component's current state."""
        value = self._data
        for part in key.split("."):
            if not isinstance(value, dict) or part not in value:
                return default
            value = value[part]
        return value

    def require(self, key):
        """Implement `require` as part of this component's public/internal behavior."""
        value = self.get(key)
        if value is None:
            raise KeyError(f"Missing required config value: {key}")
        return value

    def reload(self):
        """Implement `reload` as part of this component's public/internal behavior."""
        self.reload_calls += 1


class TestContext(SimpleNamespace):
    """Defines the `TestContext` type used by Aura runtime components."""
    def require(self, name):
        """Implement `require` as part of this component's public/internal behavior."""
        if not hasattr(self, name):
            raise AttributeError(f"{name} is not a valid context attribute.")
        value = getattr(self, name)
        if value is None:
            raise RuntimeError(f"{name} has not been initialized.")
        return value


class InMemoryDatabase:
    """
    Tiny in-memory database stub that supports the SQL patterns used by tests.
    """

    def __init__(self):
        """Initialize `InMemoryDatabase` with required dependencies and internal state."""
        self._conversation_rows = []
        self._memory_rows = {}
        self._semantic_memory_rows = {}
        self._command_logs = []
        self._conversation_id = 0
        self.connection = SimpleNamespace(is_connected=lambda: True)
        self.database_name = "aura"

    def execute(self, query, params=()):
        """Execute the command using parsed arguments and return a user-facing message."""
        normalized = " ".join(query.lower().split())

        if "insert into conversation_history" in normalized:
            role, content = params
            self._conversation_id += 1
            self._conversation_rows.append(
                {"id": self._conversation_id, "role": role, "content": content}
            )
            return None

        if normalized.startswith("delete from conversation_history where id not in"):
            limit = int(params[0])
            keep_ids = {
                row["id"]
                for row in sorted(
                    self._conversation_rows,
                    key=lambda item: item["id"],
                    reverse=True,
                )[:limit]
            }
            self._conversation_rows = [
                row for row in self._conversation_rows if row["id"] in keep_ids
            ]
            return None

        if normalized.startswith("delete from conversation_history"):
            self._conversation_rows.clear()
            return None

        if "insert into semantic_memory" in normalized:
            (
                key,
                content,
                summary,
                memory_type,
                topics,
                relationships,
                importance,
                source,
                embedding,
                updated_at,
            ) = params
            existing = self._semantic_memory_rows.get(key, {})
            created_at = existing.get("created_at", updated_at)
            self._semantic_memory_rows[key] = {
                "memory_key": key,
                "content": content,
                "summary": summary,
                "memory_type": memory_type,
                "topics": topics,
                "relationships": relationships,
                "importance": importance,
                "source": source,
                "embedding": embedding,
                "created_at": created_at,
                "updated_at": updated_at,
            }
            return None

        if "insert into memory" in normalized:
            key, value, importance = params
            self._memory_rows[key] = {
                "memory_key": key,
                "value": value,
                "importance": importance,
            }
            return None

        if normalized.startswith("delete from semantic_memory where memory_key"):
            key = params[0]
            self._semantic_memory_rows.pop(key, None)
            return None

        if normalized.startswith("delete from semantic_memory"):
            self._semantic_memory_rows.clear()
            return None

        if normalized.startswith("delete from memory where memory_key"):
            key = params[0]
            self._memory_rows.pop(key, None)
            return None

        if normalized.startswith("delete from memory"):
            self._memory_rows.clear()
            return None

        if "insert into command_logs" in normalized:
            (
                command_text,
                command_root,
                status,
                response_text,
                error_text,
                duration_ms,
            ) = params
            self._command_logs.append(
                {
                    "command_text": command_text,
                    "command_root": command_root,
                    "status": status,
                    "response_text": response_text,
                    "error_text": error_text,
                    "duration_ms": duration_ms,
                }
            )
            return None

        if normalized.startswith("delete from command_logs"):
            self._command_logs.clear()
            return None

        return None

    def fetchOne(self, query, params=()):
        """Implement `fetchOne` as part of this component's public/internal behavior."""
        normalized = " ".join(query.lower().split())

        if normalized.startswith("select value from memory where memory_key"):
            key = params[0]
            row = self._memory_rows.get(key)
            if row:
                return {"value": row["value"]}
            return None

        if normalized.startswith("select 1 as ok"):
            return {"ok": 1}

        return None

    def fetchAll(self, query, params=()):
        """Implement `fetchAll` as part of this component's public/internal behavior."""
        normalized = " ".join(query.lower().split())

        if "from conversation_history" in normalized:
            limit = params[0] if params else len(self._conversation_rows)
            desc = list(reversed(self._conversation_rows))
            selected = desc[:limit]
            return [{"role": row["role"], "content": row["content"]} for row in selected]

        if "select memory_key, value from memory" in normalized:
            return [
                {"memory_key": row["memory_key"], "value": row["value"]}
                for row in self._memory_rows.values()
            ]

        if "from semantic_memory" in normalized:
            return [dict(row) for row in self._semantic_memory_rows.values()]

        if "from information_schema.tables" in normalized:
            return [
                {"table_name": "conversation_history"},
                {"table_name": "memory"},
                {"table_name": "semantic_memory"},
                {"table_name": "command_logs"},
                {"table_name": "system_info"},
            ]

        if "from command_logs" in normalized:
            rows = list(self._command_logs)

            if "where status in ('error', 'invalid')" in normalized:
                rows = [row for row in rows if row.get("status") in {"error", "invalid"}]

            if "where command_text like" in normalized:
                like_1 = str(params[0]).strip("%").lower()
                like_2 = str(params[1]).strip("%").lower()
                like_3 = str(params[2]).strip("%").lower()

                def _matches(row):
                    text = str(row.get("command_text") or "").lower()
                    response = str(row.get("response_text") or "").lower()
                    error = str(row.get("error_text") or "").lower()
                    return like_1 in text or like_2 in response or like_3 in error

                rows = [row for row in rows if _matches(row)]

            if "order by id desc" in normalized:
                rows = list(reversed(rows))

            if "limit ?" in normalized:
                limit = int(params[-1]) if params else len(rows)
                rows = rows[:limit]

            return rows

        return []


def make_context(database=None, extra=None):
    """Construct and return a configured helper object for tests/runtime wiring."""
    config = DictConfig(
        {
            "llm": {
                "activeProvider": "ollama",
                "fallbackProvider": "ollama",
                "ollama": {
                    "endpoint": "http://localhost:11434/api/generate",
                    "model": "llama3.1:8b",
                },
                "history": {"enabled": True, "limit": 25},
                "memory": {"enabled": True, "frequency": 20},
            },
            "database": {
                "host": "localhost",
                "port": 3306,
                "name": "aura",
                "user": "root",
                "password": "pass",
            },
        }
    )

    context = TestContext()
    context.logger = None
    context.dtUtil = DateTimeUtils
    context.config = config
    context.database = database
    context.conversationHistory = None
    context.memoryManager = None
    context.llmManager = None
    context.llm = None
    context.voiceManager = None
    context.textToSpeech = None
    context.audioPlayer = None
    context.speechQueue = None
    context.modules = {}
    context.threader = None
    context.taskManager = None
    context.scheduler = None
    context.commandHandler = None
    context.systemCommandHandler = None
    context.should_exit = False

    if extra:
        for key, value in extra.items():
            setattr(context, key, value)

    return context
