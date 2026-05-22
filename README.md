# Aura Assistant

**Author:** Nova Brown
**Version:** 1.8.0
**Copyright:** (c) Nova Brown - All Rights Reserved

## Overview

Aura is a personal assistant runtime with shared backend systems and separate
interface packages in one master branch.

The backend owns runtime startup, persistence, scheduling, LLM integration,
memory/history, calendar, reminders, notifications, home automation, and system
lifecycle logic. Each interface package is kept isolated so platform-specific
builds can include only the files needed for that target.

## Project Structure

```text
config/                 Runtime configuration loading
core/                   Engine, runtime context, router, threading, autonomy,
                        context awareness, and observability systems
modules/                Backend modules and persistence integrations
modules/home_automation/
                        Home automation bridge and device backend
interface/windows/      Windows visual interface
interface/android/      Android visual interface
interface/web/          Web visual interface and static assets
interface/inputProcessing/
tests/                  Automated test suites
scripts/                Build and maintenance helpers
```

## Requirements

Shared backend requirements are listed in:

```text
requirements.txt
```

Each interface also has its own requirements file:

```text
interface/windows/requirements.txt
interface/android/requirements.txt
interface/web/requirements.txt
```

Install shared backend dependencies:

```powershell
python -m pip install -r requirements.txt
```

Install a platform interface dependency set:

```powershell
python -m pip install -r interface/windows/requirements.txt
python -m pip install -r interface/android/requirements.txt
python -m pip install -r interface/web/requirements.txt
```

The desktop, web, and Android chat headers each show the currently active LLM model or fallback provider so you can verify what the runtime is using at a glance.

## Interfaces

All visual interfaces expose chat, reminders, calendar, notifications, and home
automation controls. Home automation UI features can refresh bridge state, show
lights/cameras/devices, and request bridge or hub startup locally inside Aura.
The web UI also exposes direct light and camera controls.

Windows:

```python
from interface.windows import AuraWindowsApp
```

Android:

```python
from interface.android import AuraAndroidApp
```

Web:

```powershell
python -m interface.web
```

Default local web URL:

```text
http://127.0.0.1:8765/
```

## Home Automation

The `modules.home_automation` backend is registered as:

```python
context.homeAutomation
```

It talks to the bridge for device state and handles service-start requests locally inside Aura:

- the home automation bridge for devices, lights, cameras, and bridge notifications
- local bridge and hub start requests handled by the Aura runtime

Supported backend operations include:

- bridge connect/refresh/state
- list devices, lights, and cameras
- read light state by device or room
- light on/off, brightness, color temperature, and color
- set light color by device or room
- camera stream start/stop and snapshot
- bridge notification list/queue
- local start bridge and start hub acknowledgements

Configuration can be supplied through `config.yml` under `homeAutomationBridge`:

```yaml
homeAutomationBridge:
  host: 127.0.0.1
  port: 8080
  ssl: false
  timeout: 5
  refreshSeconds: 5
```

Environment variable fallbacks are also supported:

```text
HOME_AUTOMATION_BRIDGE_HOST
HOME_AUTOMATION_BRIDGE_PORT
HOME_AUTOMATION_BRIDGE_SSL
HOME_AUTOMATION_BRIDGE_TIMEOUT
HOME_AUTOMATION_REFRESH_SECONDS
```

The legacy nested `home_automation.bridge` config path is still accepted as a fallback for older config files.

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

LLM offline mode is auto-detected from Gemini availability. If Gemini cannot be
reached, Aura uses the local Ollama provider instead of reading an
`offlineMode` setting from config.

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

Each platform interface has its own build script. The scripts create source
bundles under `build/interfaces/<platform>` and zip archives under
`build/interfaces/aura_<platform>.zip`.

The bundle includes:

- shared backend files from `config/`, `core/`, `modules/`, and `main.py`
- `interface/__init__.py`
- only the selected platform interface package
- a flattened platform-specific `requirements.txt`
- a platform launcher named `run_aura_<platform>.py`
- `BUILD_MANIFEST.json`

Build Windows interface bundle:

```powershell
python interface/windows/build.py
```

Build Android interface bundle:

```powershell
python interface/android/build.py
```

Build Web interface bundle:

```powershell
python interface/web/build.py
```

The shared helper can also be called directly:

```powershell
python -m scripts.interface_build windows
python -m scripts.interface_build android
python -m scripts.interface_build web
```

Generated build artifacts are ignored by git.

### Windows `.exe`

The Windows interface bundle can be packaged with PyInstaller after the source
bundle is created.

Build the Windows bundle:

```powershell
.\.venv\python.exe interface/windows/build.py
```

Install the bundled requirements and PyInstaller:

```powershell
.\.venv\python.exe -m pip install -r build/interfaces/windows/requirements.txt
.\.venv\python.exe -m pip install pyinstaller
```

Build the executable:

```powershell
.\.venv\python.exe -m PyInstaller `
  --onefile `
  --name AuraWindows `
  --paths build/interfaces/windows `
  build/interfaces/windows/run_aura_windows.py
```

The generated executable is written to:

```text
dist/AuraWindows.exe
```

Run the executable from the project root, or copy `config.yml`, `.env`, and any
local SQLite database file next to the executable before distributing it. If
`config.yml` is missing, Aura creates a default config on first startup.

If the app needs the icon embedded, add:

```powershell
--icon assets/icons/aura.ico
```

### Web `.exe`

The web interface can also be packaged as a Windows executable. The executable
starts Aura's local web server; users still open the UI in a browser at
`http://127.0.0.1:8765/`.

Build the web bundle:

```powershell
.\.venv\python.exe interface/web/build.py
```

Install the bundled requirements and PyInstaller:

```powershell
.\.venv\python.exe -m pip install -r build/interfaces/web/requirements.txt
.\.venv\python.exe -m pip install pyinstaller
```

Build the executable:

```powershell
.\.venv\python.exe -m PyInstaller `
  --onefile `
  --name AuraWeb `
  --paths build/interfaces/web `
  --add-data "build/interfaces/web/interface/web/static;interface/web/static" `
  build/interfaces/web/run_aura_web.py
```

The generated executable is written to:

```text
dist/AuraWeb.exe
```

Run the executable from the project root, or copy `config.yml`, `.env`, and any
local SQLite database file next to the executable before distributing it. If
`config.yml` is missing, Aura creates a default config on first startup.

### Android `.apk`

The Android interface uses Kivy. Buildozer is the expected APK packaging tool,
and it runs on Linux. On Windows, use WSL or a Linux build machine.

Build the Android source bundle:

```powershell
.\.venv\python.exe interface/android/build.py
```

Copy or rename the Android launcher in the generated bundle so Buildozer sees a
root-level `main.py`:

```powershell
Copy-Item build/interfaces/android/run_aura_android.py build/interfaces/android/main.py
```

From WSL/Linux, install Buildozer and initialize the Android project inside the
bundle:

```bash
cd /mnt/c/Users/novab/PycharmProjects/Aura/build/interfaces/android
python3 -m pip install --user buildozer cython
buildozer init
```

Edit the generated `buildozer.spec` before building:

```ini
title = Aura
package.name = aura
package.domain = org.novabrown
source.include_exts = py,png,jpg,kv,json,yml,txt
requirements = python3,kivy,requests,PyYAML,mysql-connector-python,tzdata,google-genai
orientation = portrait
```

Build a debug APK:

```bash
buildozer android debug
```

The generated debug APK is written under:

```text
build/interfaces/android/bin/
```

For a releasable APK, configure signing in `buildozer.spec` and use:

```bash
buildozer android release
```

## Logging

Aura creates a `logs` directory automatically if it does not exist.

Each startup creates a new timestamped log file in `logs/`, and all log levels
are written there for that run.

## Configuration

Primary runtime config file:

```text
config.yml
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
python run_tests.py --suite observability
python run_tests.py --suite notifications
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

Interface-specific tests live in `tests/interfaceTests/`:

```text
tests/interfaceTests/test_windows_interface.py
tests/interfaceTests/test_android_interface.py
tests/interfaceTests/test_web_interface.py
```

Optional live LLM connectivity test:

```powershell
$env:RUN_LIVE_LLM_TEST="true"
$env:OLLAMA_ENDPOINT="http://localhost:11434/api/generate"
$env:OLLAMA_MODEL="llama3.1:8b"
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
