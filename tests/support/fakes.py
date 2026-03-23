from types import SimpleNamespace


class DictConfig:
    def __init__(self, data):
        self._data = data

    def get(self, key, default=None):
        value = self._data
        for part in key.split("."):
            if not isinstance(value, dict) or part not in value:
                return default
            value = value[part]
        return value

    def require(self, key):
        value = self.get(key)
        if value is None:
            raise KeyError(f"Missing required config value: {key}")
        return value


class InMemoryDatabase:
    """
    Tiny in-memory database stub that supports the SQL patterns used by tests.
    """

    def __init__(self):
        self._conversation_rows = []
        self._memory_rows = {}
        self._conversation_id = 0

    def execute(self, query, params=()):
        normalized = " ".join(query.lower().split())

        if "insert into conversation_history" in normalized:
            role, content = params
            self._conversation_id += 1
            self._conversation_rows.append(
                {"id": self._conversation_id, "role": role, "content": content}
            )
            return None

        if normalized.startswith("delete from conversation_history"):
            self._conversation_rows.clear()
            return None

        if "insert into memory" in normalized:
            key, value, importance = params
            self._memory_rows[key] = {
                "memory_key": key,
                "value": value,
                "importance": importance,
            }
            return None

        if normalized.startswith("delete from memory where memory_key"):
            key = params[0]
            self._memory_rows.pop(key, None)
            return None

        if normalized.startswith("delete from memory"):
            self._memory_rows.clear()
            return None

        return None

    def fetchOne(self, query, params=()):
        normalized = " ".join(query.lower().split())

        if normalized.startswith("select value from memory where memory_key"):
            key = params[0]
            row = self._memory_rows.get(key)
            if row:
                return {"value": row["value"]}
            return None

        return None

    def fetchAll(self, query, params=()):
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

        return []


def make_context(database=None, extra=None):
    config = DictConfig(
        {
            "llm": {
                "endpoint": "http://localhost:11434/api/generate",
                "model": "llama3.1:8b",
                "history": {"enabled": True, "limit": 25},
                "memory": {"enabled": True},
            }
        }
    )

    context = SimpleNamespace()
    context.logger = None
    context.config = config
    context.database = database
    context.conversationHistory = None
    context.memoryManager = None
    context.commandHandler = None
    context.systemCommandHandler = None
    context.should_exit = False

    if extra:
        for key, value in extra.items():
            setattr(context, key, value)

    return context

