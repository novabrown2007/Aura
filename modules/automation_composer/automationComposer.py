"""User-facing automation planning and execution for Aura."""

from __future__ import annotations

import json
from datetime import datetime
from typing import Any

from core.tools.tool import Tool, ToolCategory
from modules.base import AuraModule, ModuleMetadata


class AutomationComposer(AuraModule):
    """Draft reviewable automations and activate them through Aura autonomy."""

    metadata = ModuleMetadata(
        name="automationComposer",
        version="0.1.0",
        description="Draft, activate, and run reviewable assistant automations.",
        permissions=("database:read", "database:write", "events:write", "tools:execute"),
        capabilities=("automation", "autonomy"),
    )

    AUTOMATION_TASK_TYPE = "automation_composer.execute"

    def __init__(self, context=None):
        """Initialize module state."""

        super().__init__()
        self.database = None
        self.logger = None
        if context is not None:
            self.initialize(context)

    def initialize(self, context):
        """Bind to runtime services and register the automation task handler."""

        super().initialize(context)
        self.context = context
        self.database = context.database
        self.logger = context.logger.getChild("AutomationComposer") if context.logger else None
        self.createAutomationPlansTable()

        autonomous = getattr(context, "autonomousTasks", None)
        if autonomous is not None:
            autonomous.registerHandler(self.AUTOMATION_TASK_TYPE, self._handleAutomationTask)

        self._logStartup("automationComposer module started.")

    def getIntents(self):
        """Return intents handled by the deterministic tool layer."""

        return []

    def getTools(self):
        """Return deterministic automation tools exposed to Aura."""

        return [
            Tool(
                name="automation.createDraft",
                description="Create a reviewable automation draft from structured trigger, condition, and action details.",
                parameters={
                    "name": {"type": "string"},
                    "goal": {"type": "string"},
                    "trigger_type": {"type": "string"},
                    "trigger_value": {"type": "string"},
                    "conditions": {"type": "array"},
                    "actions": {"type": "array"},
                    "safety": {"type": "object"},
                },
                requiredParameters=("name", "goal", "trigger_type", "actions"),
                module="automationComposer",
                method="createDraft",
                safe=True,
                offlineAllowed=True,
            ),
            Tool(
                name="automation.listPlans",
                description="List automation plans, optionally filtered by status.",
                parameters={"status": {"type": "string"}},
                module="automationComposer",
                method="listPlans",
                safe=True,
                offlineAllowed=True,
            ),
            Tool(
                name="automation.activate",
                description="Activate a reviewed automation draft so Aura can run it on its trigger.",
                parameters={"plan_id": {"type": "integer"}},
                requiredParameters=("plan_id",),
                module="automationComposer",
                method="activatePlan",
                safe=False,
                confirmRequired=True,
                category=ToolCategory.CONFIRM_REQUIRED,
            ),
            Tool(
                name="automation.pause",
                description="Pause an active automation plan.",
                parameters={"plan_id": {"type": "integer"}},
                requiredParameters=("plan_id",),
                module="automationComposer",
                method="pausePlan",
                safe=True,
                offlineAllowed=True,
            ),
            Tool(
                name="automation.resume",
                description="Resume a paused automation plan.",
                parameters={"plan_id": {"type": "integer"}},
                requiredParameters=("plan_id",),
                module="automationComposer",
                method="resumePlan",
                safe=False,
                confirmRequired=True,
                category=ToolCategory.CONFIRM_REQUIRED,
            ),
            Tool(
                name="automation.runNow",
                description="Run an active automation plan immediately.",
                parameters={"plan_id": {"type": "integer"}},
                requiredParameters=("plan_id",),
                module="automationComposer",
                method="runPlanNow",
                safe=False,
                confirmRequired=True,
                category=ToolCategory.CONFIRM_REQUIRED,
            ),
        ]

    def createAutomationPlansTable(self):
        """Validate database availability for automation persistence."""

        if not self.database and self.logger:
            self.logger.warning("AutomationComposer started without a database.")

    def createDraft(
        self,
        name: str,
        goal: str,
        trigger_type: str,
        actions: list[dict],
        trigger_value: str | None = None,
        conditions: list[dict] | None = None,
        safety: dict | None = None,
    ):
        """Create a draft automation plan for user review."""

        if not self.database:
            return None

        normalized = self._normalizePlan(
            name=name,
            goal=goal,
            trigger_type=trigger_type,
            trigger_value=trigger_value,
            conditions=conditions,
            actions=actions,
            safety=safety,
        )
        cursor = self.database.execute(
            """
            INSERT INTO automation_plans (
                name, goal, trigger_type, trigger_value, conditions,
                actions, safety, status
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                normalized["name"],
                normalized["goal"],
                normalized["trigger_type"],
                normalized["trigger_value"],
                self._encode(normalized["conditions"]),
                self._encode(normalized["actions"]),
                self._encode(normalized["safety"]),
                "draft",
            ),
        )
        plan_id = getattr(cursor, "lastrowid", None)
        if plan_id is None:
            row = self.database.fetchOne("SELECT id FROM automation_plans ORDER BY id DESC LIMIT 1")
            plan_id = row.get("id") if row else None

        plan = self.getPlan(plan_id) if plan_id is not None else None
        self._emit("automation.plan.created", {"plan": plan})
        return plan

    def getPlan(self, plan_id: int | str | None):
        """Return one automation plan."""

        if not self.database or plan_id is None:
            return None

        row = self.database.fetchOne(
            """
            SELECT id, name, goal, trigger_type, trigger_value, conditions,
                   actions, safety, status, autonomous_task_id, last_run_at,
                   last_result, created_at, updated_at
            FROM automation_plans
            WHERE id = ?
            """,
            (int(plan_id),),
        )
        return self._prepareRow(row)

    def listPlans(self, status: str | None = None):
        """List automation plans ordered by creation."""

        if not self.database:
            return []

        rows = self.database.fetchAll(
            """
            SELECT id, name, goal, trigger_type, trigger_value, conditions,
                   actions, safety, status, autonomous_task_id, last_run_at,
                   last_result, created_at, updated_at
            FROM automation_plans
            ORDER BY id ASC
            """
        )
        plans = [self._prepareRow(row) for row in rows]
        if status is not None:
            normalized = str(status).lower()
            plans = [plan for plan in plans if str(plan.get("status")).lower() == normalized]
        return plans

    def activatePlan(self, plan_id: int):
        """Activate a draft or paused automation by creating/resuming its task."""

        plan = self.getPlan(plan_id)
        if plan is None:
            return None
        if plan["status"] == "active":
            return plan

        autonomous = getattr(self.context, "autonomousTasks", None)
        if autonomous is None:
            raise RuntimeError("Autonomous task manager is unavailable.")

        task_id = plan.get("autonomous_task_id")
        if task_id:
            task = autonomous.resumeTask(task_id, next_run_at=self._nextRunAt(plan))
        else:
            task = autonomous.createTask(
                name=f"Automation: {plan['name']}",
                task_type=self.AUTOMATION_TASK_TYPE,
                description=plan["goal"],
                interval_seconds=self._intervalSeconds(plan),
                next_run_at=self._nextRunAt(plan),
                event_name=self._eventName(plan),
                memory_context={"automation_plan_id": plan["id"]},
                state={"automation_plan_id": plan["id"]},
            )
            task_id = task.get("id") if task else None

        self.database.execute(
            """
            UPDATE automation_plans
            SET status = ?, autonomous_task_id = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            ("active", task_id, int(plan_id)),
        )
        plan = self.getPlan(plan_id)
        self._emit("automation.plan.activated", {"plan": plan, "task": task})
        return plan

    def pausePlan(self, plan_id: int):
        """Pause an active automation and its backing autonomous task."""

        plan = self.getPlan(plan_id)
        if plan is None:
            return None

        autonomous = getattr(self.context, "autonomousTasks", None)
        if autonomous is not None and plan.get("autonomous_task_id"):
            autonomous.pauseTask(plan["autonomous_task_id"])

        self._updateStatus(plan_id, "paused")
        plan = self.getPlan(plan_id)
        self._emit("automation.plan.paused", {"plan": plan})
        return plan

    def resumePlan(self, plan_id: int):
        """Resume a paused automation."""

        return self.activatePlan(plan_id)

    def runPlanNow(self, plan_id: int):
        """Run an active automation immediately."""

        plan = self.getPlan(plan_id)
        if plan is None:
            return None
        if plan.get("status") != "active":
            raise RuntimeError("Only active automation plans can run.")
        return self.executePlan(plan, reason="manual")

    def executePlan(self, plan: dict, reason: str = "automation", trigger_event: dict | None = None):
        """Execute a plan after evaluating simple conditions."""

        if not self._conditionsMatch(plan.get("conditions") or []):
            result = {"skipped": True, "reason": "conditions_not_met"}
            self._recordRun(plan["id"], result)
            return result

        results = []
        for action in plan.get("actions") or []:
            results.append(self._executeAction(action, trigger_event=trigger_event))

        result = {"skipped": False, "reason": reason, "actions": results}
        self._recordRun(plan["id"], result)
        self._emit("automation.plan.ran", {"plan": self.getPlan(plan["id"]), "result": result})
        return result

    def _handleAutomationTask(self, payload: dict):
        task = payload["task"]
        plan_id = (task.get("memory_context") or {}).get("automation_plan_id")
        if plan_id is None:
            plan_id = (task.get("state") or {}).get("automation_plan_id")
        plan = self.getPlan(plan_id)
        if plan is None or plan.get("status") != "active":
            return {"skipped": True, "reason": "plan_not_active"}
        return self.executePlan(plan, reason=payload.get("reason", "automation"), trigger_event=payload.get("trigger_event"))

    def _executeAction(self, action: dict, trigger_event: dict | None = None):
        action_type = str(action.get("type") or "").strip().lower()
        if action_type == "event":
            event_name = action.get("name")
            data = dict(action.get("data") or {})
            if trigger_event is not None:
                data.setdefault("trigger_event", trigger_event)
            event = self._emit(event_name, data)
            return {"type": "event", "name": event_name, "data": event.data if event else data}

        if action_type == "tool":
            executor = getattr(self.context, "toolExecutor", None)
            if executor is None:
                return {"type": "tool", "success": False, "error": "Tool executor is unavailable."}
            return executor.executeToolCall(
                action.get("tool"),
                action.get("arguments") or {},
                confirmed=bool(action.get("confirmed", False)),
            )

        return {"type": action_type or "unknown", "success": False, "error": "Unknown automation action type."}

    def _conditionsMatch(self, conditions: list[dict]):
        context_awareness = getattr(self.context, "contextAwareness", None)
        for condition in conditions:
            condition_type = str(condition.get("type") or "").strip().lower()
            if condition_type in ("", "always"):
                continue
            if condition_type == "context_equals":
                if context_awareness is None or not hasattr(context_awareness, "getSignal"):
                    return False
                signal = context_awareness.getSignal(condition.get("signal"))
                value = signal.get("value") if isinstance(signal, dict) else signal
                if value != condition.get("value"):
                    return False
        return True

    def _normalizePlan(self, name, goal, trigger_type, trigger_value, conditions, actions, safety):
        trigger_type = str(trigger_type).strip().lower()
        if trigger_type not in {"manual", "interval", "datetime", "event"}:
            raise ValueError("trigger_type must be manual, interval, datetime, or event.")
        if not isinstance(actions, list) or not actions:
            raise ValueError("actions must be a non-empty list.")
        return {
            "name": str(name).strip(),
            "goal": str(goal).strip(),
            "trigger_type": trigger_type,
            "trigger_value": str(trigger_value).strip() if trigger_value is not None else None,
            "conditions": conditions or [],
            "actions": actions,
            "safety": safety or {"requires_review": True},
        }

    def _intervalSeconds(self, plan: dict):
        if plan.get("trigger_type") != "interval":
            return None
        return int(plan.get("trigger_value") or 0) or None

    def _nextRunAt(self, plan: dict):
        if plan.get("trigger_type") == "datetime":
            return self.context.dtUtil.toStorageDateTime(plan.get("trigger_value"))
        return None

    def _eventName(self, plan: dict):
        if plan.get("trigger_type") == "event":
            return plan.get("trigger_value")
        return None

    def _recordRun(self, plan_id: int, result: dict):
        self.database.execute(
            """
            UPDATE automation_plans
            SET last_run_at = ?, last_result = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (self._now(), self._encode(result), int(plan_id)),
        )

    def _updateStatus(self, plan_id: int, status: str):
        self.database.execute(
            """
            UPDATE automation_plans
            SET status = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (str(status), int(plan_id)),
        )

    def _emit(self, event_name: str | None, data: dict):
        event_manager = getattr(self.context, "eventManager", None)
        if event_manager is None or not event_name:
            return None
        return event_manager.emit(str(event_name), data)

    def _prepareRow(self, row):
        if row is None:
            return None
        prepared = dict(row)
        prepared["conditions"] = self._decode(prepared.get("conditions"), [])
        prepared["actions"] = self._decode(prepared.get("actions"), [])
        prepared["safety"] = self._decode(prepared.get("safety"), {})
        prepared["last_result"] = self._decode(prepared.get("last_result"), None)
        return prepared

    @staticmethod
    def _encode(value: Any):
        return json.dumps(value, sort_keys=True)

    @staticmethod
    def _decode(value, default):
        if value in (None, ""):
            return default
        if isinstance(value, (dict, list)):
            return value
        try:
            return json.loads(value)
        except (TypeError, json.JSONDecodeError):
            return default

    @staticmethod
    def _now():
        return datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
