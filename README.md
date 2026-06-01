# Aura Assistant

**Author:** Nova Brown
**Version:** 1.12.0
**Copyright:** (c) Nova Brown - All Rights Reserved

## Overview

Aura is a modular assistant runtime with a layered architecture:

- `core/` for engine and infrastructure
- `assistant/` for cognition and behavior
- event-driven presentation and execution contracts
- `modules/` for deterministic capabilities
- `providers/` for external AI and service adapters

The backend owns runtime startup, persistence, scheduling, LLM integration,
memory/history, calendar, reminders, notifications, home automation, and system
lifecycle logic. Attention management lives under `assistant/notifications/`
so notification urgency, routing, suppression, and escalation stay separate from
generic storage or logging. Each interface package is kept isolated so
platform-specific builds can include only the files needed for that target.

Capability modules are now standardized through the module framework under
`core/modules/`, with example integrations for weather, Spotify, calendar,
reminders, and smart home.

## Project Structure

```text
config/                 Runtime configuration loading
core/                   Engine, runtime, logging, events, threading, config
core/modules/           Module framework infrastructure and lifecycle control
assistant/              Conversation, memory, personality, orchestration
assistant/notifications/ Notification attention management and escalation
event bus / execution    Event-driven presentation and command routing
modules/                Capability integrations and deterministic tools
providers/              External AI/service wrappers
testing/tests/                  Automated test suites
scripts/                Build and maintenance helpers
```

## Requirements

Shared backend requirements are listed in:

```text
requirements.txt
```

Install shared backend dependencies:

```powershell
python -m pip install -r requirements.txt
```

The desktop, web, and Android chat headers each show the currently active LLM model or fallback provider so you can verify what the runtime is using at a glance.

## Voice

The legacy voice package layout was removed from the runtime bootstrap during the interface reset, so the examples below are historical references rather than current startup behavior.

Aura includes local push-to-talk speech-to-text and local text-to-speech through:

```python
context.voiceManager
context.textToSpeech
context.speechQueue
```

Voice input is local-first and uses Faster-Whisper with a cached
`small.en` model on CPU by default. Voice output uses Piper with a cached
local ONNX voice and Windows `winsound` playback.

User-facing voice configuration is available under `voice` in
`config/config.yml`. Backend defaults for capture models, sample rates, and
other operational tuning live in `config/devConfig.yml`:

```yaml
voice:
  pushToTalk:
    enabled: true
  alwaysActive:
    enabled: true
    activationPhrases: ["Aura", "Hey Aura"]
```

Example usage:

```python
result = context.voiceManager.processVoiceInput()
print(result.text)

context.voiceManager.speakResponse("Hello. Aura voice systems are online.")
```

Set `voice.pushToTalk.enabled` to `true`, then press Enter
to start microphone capture and Enter again to stop. Aura transcribes with
Faster-Whisper, sends the text through the existing conversation pipeline,
speaks the response with Piper when `pushToTalkAutoSpeak` is enabled, and
returns to idle.

Always-active wake-word activation can be enabled with
`voice.alwaysActive.enabled`. Wake words use OpenWakeWord locally. Custom
activation phrases such as `Hey Aura` require a matching local OpenWakeWord
`.onnx` or `.tflite` model file, for example:

```text
core/voice/wakeWord/models/hey_aura.onnx
```

or an explicit backend path in `config/devConfig.yml`:

```yaml
voice:
  alwaysActive:
    wakeWordModelPath: path/to/hey_aura.onnx
```

If no configured Aura-specific model is available, Aura now falls back to the
built-in OpenWakeWord model configured by `wakeWordFallbackModel`
(`hey_jarvis` by default) so always-active listening still starts. Disable that
behavior with `wakeWordAllowPretrainedFallback: false` when you want startup to
fail until a custom wake model is installed. Missing OpenWakeWord assets are
downloaded automatically when `wakeWordAutoDownloadModels` is enabled.

The voice layer does not implement streaming transcription or speaker
identification. Always-active capture uses local VAD to detect speech endpoints
and then sends the finalized WAV through the existing Faster-Whisper STT
pipeline.

The legacy voice-facing package layout was removed with the interface reset.

## Memory

Aura's long-term memory remains structured and deterministic, with semantic
retrieval layered on top as an optional accelerator rather than a replacement.
The assistant memory layer can retrieve relevant memories by meaning when an
embedding provider is available, then falls back to keyword and structured
memory retrieval when it is not.

Semantic memory defaults live under `memory.semantic` in
`config/devConfig.yml`:

```yaml
memory:
  semantic:
    enabled: true
    provider: gemini
    model: text-embedding-004
    maxResults: 5
    minimumSimilarity: 0.65
```

The canonical semantic retrieval and embedding code now lives under
`assistant/memory/`, with provider adapters under `providers/embeddings/`.
The memory injector requests concise semantic context from the memory manager
and keeps prompt injection lightweight and explainable.

## Interfaces

The first rebuilt surface is a blank desktop window that serves as the starting
shell for the new presentation layer. It follows the current homepage mockup:
custom top bar, a larger 4x3 grid of draggable widget tiles, a toggleable sidebar that closes on outside clicks, and a lower bottom
text field placed in the footer band. The sidebar currently exposes Home, Chat,
and a Settings area anchored at the bottom. The top-bar controls are transparent hit targets layered above the chrome. The sidebar also has an `X` button in its top-right corner to close it. The window is taller so the footer field stays fully visible. The desktop window is resizable. On Windows, the launcher starts in the system tray when tray startup succeeds, and otherwise leaves the window visible.
The footer field now grows with the window and sits in the lower band below the separator line. The status circle is slightly larger, the send button arrow is even larger and sits a bit higher, the button sits farther in from the bottom-right edge, and the input is slightly narrower so it cannot run underneath that button.
Escape no longer closes the app; use the window controls instead.
The first row now uses the imported sprite assets for Sidebar, Close, Notifications On, and Notifications Off. The Home icon is still unused.

Launch it with:

```powershell
python scripts/run_blank_window.py
```

## Home Automation

The `modules.home_automation` backend is registered as:

```python
context.homeAutomation
```

It talks to the Home Automation Bridge through the Aura Protocol client in
`bridge` and handles service-start requests locally inside Aura:

- assistant notifications, responses, errors, and stream metadata from the bridge
- bridge-owned device state and deterministic light/camera actions
- local bridge and hub start requests handled by the Aura runtime

Supported backend operations include:

- bridge connect/refresh/state through the protocol client
- list devices, lights, and cameras
- read light state by device or room
- light on/off, brightness, color temperature, and color
- set light color by device or room
- camera stream start/stop and snapshot
- bridge notification list/queue
- local start bridge and start hub acknowledgements

Connection configuration can be supplied through `config/config.yml` under
`homeAutomationBridge`. Protocol paths, refresh intervals, and other backend
defaults live in `config/devConfig.yml`:

```yaml
homeAutomationBridge:
  host: 127.0.0.1
  port: 8080
  ssl: false
  timeout: 5
  refreshSeconds: 5
  protocolPath: /protocol/aura
  inboxPath: /protocol/inbox
  subscriptionsPath: /protocol/subscriptions
  heartbeatPath: /protocol/heartbeat
  sessionId: auto
  interface: desktop
  heartbeatSeconds: 30
```

Environment variable fallbacks are also supported:

```text
HOME_AUTOMATION_BRIDGE_HOST
HOME_AUTOMATION_BRIDGE_PORT
HOME_AUTOMATION_BRIDGE_SSL
HOME_AUTOMATION_BRIDGE_TIMEOUT
HOME_AUTOMATION_REFRESH_SECONDS
```

The bridge client auto-subscribes to:

- `assistant.notification`
- `assistant.response`
- `assistant.error`
- `assistant.stream.available`
- `assistant.context`

The legacy nested `home_automation.bridge` config path is still accepted as a fallback for older config files.

## Module Framework

Aura now treats capability integrations as first-class modules. The canonical
framework lives in `core/modules/` and handles:

- discovery
- registration
- metadata
- permissions
- actions
- intents
- lifecycle state
- safe load/unload/reload coordination

The compatibility loader in `core/runtime/moduleLoader.py` now delegates to the
new `ModuleManager`, so existing code paths continue to work while new code can
target the canonical framework directly.

Example module packages include:

- `modules/weather`
- `modules/spotify`
- `modules/calendar`
- `modules/reminders`
- `modules/smartHome`

Modules are discovered through the runtime module manager and exposed in the
developer UI through observability snapshots.

## Event Bus

Aura uses `context.eventManager` for decoupled runtime communication. Modules
and core services can emit named events without directly calling each other.

```python
context.eventManager.emit("lights.changed", {"device_id": "kitchen"})
context.eventManager.subscribe("context.changed", on_context_changed)
```

Existing event-driven integrations include:

- `calendar` emits `reminders.create` instead of directly calling reminders
- `reminders` emits `notifications.create` instead of directly calling notifications
- home automation emits `lights.changed` after light state changes
- observability records event traces automatically

## Tool Ownership

Tool ownership lives outside the LLM layer. Modules expose deterministic tools
through their `getTools()` methods, the module loader registers those tools in
`context.toolRegistry`, and `context.toolOrchestrator` owns the schemas,
validation, and execution contract.

LLM components only reason over exported tool schemas and return candidate tool
calls. Actual execution flows through `ToolExecutor`, which calls the owning
module method after validation.

## LLM Prompt Modes

Aura keeps separate prompt profiles for each cognition task:

- `conversation` for direct user-facing replies
- `intentParsing` for structured intent JSON
- `memorySummary` for durable memory extraction
- `automationPlanning` for cautious automation plans without execution
- `toolSelection` for deterministic tool-call JSON

Prompt construction is centralized in `modules.llm.utils.PromptBuilder`, with
profile bodies under `modules/llm/prompts`.

LLM routing defaults to the local Ollama provider with Gemini configured as the
fallback provider. Offline mode is auto-detected from preferred-provider
availability instead of reading an `offlineMode` setting from config.

## Autonomous Tasks

Aura exposes persistent long-running assistant tasks through:

```python
context.autonomousTasks
```

Autonomous tasks support:

- durable task definitions and JSON state
- scheduled wakeups through the shared scheduler
- pause and resume
- memory context included in execution payloads
- event-driven create, pause, resume, and run controls
- handler registration by task type

Example:

```python
def check_weather(payload):
    task = payload["task"]
    memory = payload["memory"]
    return {"checked": task["name"], "memory_keys": list(memory)}

context.autonomousTasks.registerHandler("weather.check", check_weather)
task = context.autonomousTasks.createTask(
    name="Morning weather",
    task_type="weather.check",
    interval_seconds=3600,
    memory_context={"city": "Hamilton"},
)
context.autonomousTasks.pauseTask(task["id"])
context.autonomousTasks.resumeTask(task["id"])
```

Event controls:

```python
context.eventManager.emit("autonomous.task.create", {
    "name": "Track package",
    "task_type": "package.track",
    "interval_seconds": 1800,
})
context.eventManager.emit("autonomous.task.run", {"task_id": 1})
```

## Automation Composer

Aura exposes reviewable user-facing automations through:

```python
context.automationComposer
```

Automation Composer stores draft plans, lets the user activate/pause/resume
them, and delegates scheduled or event-driven execution to
`context.autonomousTasks`. Plans are intentionally reviewable before activation:

- `manual`, `interval`, `datetime`, and `event` triggers
- simple condition blocks such as `always` and `context_equals`
- event actions for decoupled module workflows
- tool actions through Aura's deterministic tool executor
- last-run result tracking on the plan

Example:

```python
plan = context.automationComposer.createDraft(
    name="Door alert",
    goal="Notify me when the front door opens.",
    trigger_type="event",
    trigger_value="door.opened",
    actions=[
        {
            "type": "event",
            "name": "notifications.create",
            "data": {
                "title": "Door",
                "content": "The front door opened.",
            },
        }
    ],
)
context.automationComposer.activatePlan(plan["id"])
context.autonomousTasks.handleEventWakeup("door.opened", {"room": "front"})
```

The deterministic tools exposed for LLM/UI workflows are:

- `automation.createDraft`
- `automation.listPlans`
- `automation.activate`
- `automation.pause`
- `automation.resume`
- `automation.runNow`

## Context Awareness

Aura exposes current environment context through:

```python
context.contextAwareness
```

Context awareness supports signals such as:

- time
- active applications
- room occupancy
- battery level
- music playing
- desktop activity
- notifications
- location

Built-in providers currently include `time` and a conservative Windows process
list as `active_applications`. Additional providers can be registered by modules
or interfaces.

```python
context.contextAwareness.registerProvider(
    "battery",
    lambda: {"percent": 82, "charging": True},
)
context.contextAwareness.collect(["battery"])
context.contextAwareness.getPromptContext()
```

When a signal changes, Aura emits:

```text
context.changed
context.<signal>.changed
```

This enables behaviors such as:

- "You've been coding for 5 hours."
- "Minecraft launched. Switching gaming profile."

Duration helpers are available:

```python
context.contextAwareness.secondsSinceChanged("desktop_activity")
```

## Layered Architecture

The canonical architecture reference is [ARCHITECTURE.md](./ARCHITECTURE.md).
It documents:

- layer responsibilities
- dependency direction
- event flow
- compatibility shim policy

## Conversational Continuity

Aura keeps short-term conversational context through:

```python
context.conversationManager
```

The conversation manager tracks active topics, entities, recent actions, and
pending clarifications so follow-up turns can be resolved before provider or
tool routing. For example, after "Turn off the bedroom lights", a follow-up
like "Actually make them blue" is resolved against the active `bedroom lights`
entity and `lighting` topic.

Short-term context expires after `conversation.conversationTimeoutSeconds`
seconds of inactivity (`300` by default). This is separate from long-term
memory and is intended only for the active conversation.

## Personality

Aura includes a controlled personality layer through:

```python
context.personalityManager
```

The personality layer adds tone guidance, optional subtle humor, lightweight
contextual suggestions, and initiative throttling. It is deliberately bounded:
commands outrank suggestions, deterministic execution outranks personality, and
the behavior governor blocks fake consciousness, emotional coercion, refusal
drift, and self-preservation phrasing.

Configuration lives under `personality` in `config/devConfig.yml`:

```yaml
personality:
  personalityEnabled: true
  humorEnabled: true
  suggestionsEnabled: true
  initiativeLevel: 0.35
  toneMode: casual
  maxSuggestionsPerHour: 3
  personalityStrength: 0.35
```

User commands such as "Turn off jokes", "Turn off suggestions", and "Be
concise" are handled deterministically and acknowledged without provider calls.

## Providers

Provider wrappers now live under `providers/` and are the preferred imports for
LLM/provider infrastructure:

- `providers.gemini.GeminiProvider`
- `providers.ollama.OllamaProvider`
- `providers.base.LLMProvider`
- `providers.base.ProviderCapabilities`

## Observability

Aura exposes runtime diagnostics through:

```python
context.observability
```

The observability snapshot includes:

- active managed threads
- current log file and recent log lines
- event listener counts
- memory keys and counts
- registered tools
- LLM provider status
- module health
- recent execution traces
- scheduler state

Example:

```python
snapshot = context.observability.snapshot()
traces = context.observability.getTraces(limit=25)
logs = context.observability.getLogs(lines=100)
```

Execution traces are recorded for event emission, task execution, and tool
execution.

## Platform Builds

The legacy interface bundle and packaging scripts were removed during the UI reset. The backend now focuses on event emission and execution flow; presentation surfaces will be rebuilt separately on top of those contracts.

## Logging

Aura creates a `logs` directory automatically if it does not exist.

Each startup writes standard runtime logs to `logs/latest.log`. If a previous
`latest.log` exists, Aura rotates it to a timestamped log before starting the
new session. Detailed LLM prompt and provider traces are isolated in
`logs/llm/latest.log` so large conversation diagnostics do not pollute normal
runtime logs. These paths are configurable under `logging` in
`config/devConfig.yml`.

## Configuration

Primary user-facing runtime config file:

```text
config/config.yml
```

Backend/developer runtime defaults:

```text
config/devConfig.yml
```

## Testing

Run all tests:

```powershell
python run_tests.py
```

Run individual suites:

```powershell
python run_tests.py --suite build
python run_tests.py --suite runtime_smoke
python run_tests.py --suite config
python run_tests.py --suite logger
python run_tests.py --suite sqlite
python run_tests.py --suite datetime_utils
python run_tests.py --suite events
python run_tests.py --suite autonomous_tasks
python run_tests.py --suite context_awareness
python run_tests.py --suite conversation_continuity
python run_tests.py --suite architecture
python run_tests.py --suite module_framework
python run_tests.py --suite personality
python run_tests.py --suite observability
python run_tests.py --suite notifications
python run_tests.py --suite notification_priority
python run_tests.py --suite semantic_memory
python run_tests.py --suite system
python run_tests.py --suite short_memory
python run_tests.py --suite long_memory
python run_tests.py --suite calendar
python run_tests.py --suite interfaces
python run_tests.py --suite home_automation
python run_tests.py --suite module_loader
python run_tests.py --suite tools
python run_tests.py --suite intent_pipeline
python run_tests.py --suite prompts
python run_tests.py --suite voice
python run_tests.py --suite assistant_testing
python run_tests.py --suite reminders
python run_tests.py --suite llm
python run_tests.py --suite mysql_integration
```

## Merge Gate CI

The repository includes a second GitHub Actions workflow:

```text
.github/workflows/approved-pr-merge.yml
```

This workflow runs when a pull request review is approved, or manually through
`workflow_dispatch`. The intended path is:

- pull request is created
- user manually reviews and approves the pull request
- the workflow runs the full test suite on the incoming branch
- if incoming tests fail, the merge is canceled and logged
- if incoming tests pass, the workflow merges the pull request
- the workflow runs the full test suite on the updated base branch
- if updated base tests fail, the merge commit is reverted
- if updated base tests pass, the incoming branch is deleted when it belongs to
  this repository
- the workflow logs the merge as successful

To make this the actual merge path, avoid manually merging approved PRs outside
this workflow. Repository settings must allow GitHub Actions to write to
contents and pull requests, and base branch protection must allow this workflow
to merge and revert when needed.

## Executable Generation CI

Executable artifacts can be generated manually with:

```text
.github/workflows/generate-executables.yml
```

The workflow runs only through `workflow_dispatch`. It creates a Python
environment, installs shared and interface requirements, creates the interface
bundles, runs the full test suite, and only then generates the Windows, Android,
and Web executables. When generation succeeds, the executables are uploaded as a
GitHub Actions artifact. On failure, the workflow logs the failed task and still
cleans up the Python environment.

Assistant ecosystem simulation tests live in:

```text
testing/tests/test_assistant_testing.py
```

They cover the mock assistant console, event tracer, session and intent
debuggers, workflow simulation, and voice/input integration helpers.

Optional live LLM connectivity test:

```powershell
$env:RUN_LIVE_LLM_TEST="true"
$env:OLLAMA_ENDPOINT="http://localhost:11434/api/generate"
$env:OLLAMA_MODEL="gemma4:e4b"
python run_tests.py --suite llm
```

Optional live MySQL integration test:

```powershell
$env:RUN_LIVE_MYSQL_TEST="true"
$env:DB_HOST="localhost"
$env:DB_PORT="3306"
$env:DB_NAME="aura"
$env:DB_USER="root"
$env:DB_PASSWORD="your_password"
python run_tests.py --suite mysql_integration
```

## License and Usage Restrictions

This software and all associated source code are the exclusive intellectual
property of **Nova Brown**.

**All rights are reserved.**

The contents of this repository may not be:

- shared
- redistributed
- copied
- modified
- published
- used in derivative works

without explicit written permission from the author.

This project is intended for private development and experimentation only.

## Contact

Project maintained by **Nova Brown**.
