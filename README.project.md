# Aura Assistant

**Author:** Nova Brown  
**Copyright:** © Nova Brown - All Rights Reserved

## Overview

Aura is a modular personal assistant framework built around a headless core runtime.

The `master` branch is intentionally interface-neutral. It contains the runtime,
threading systems, routing, LLM integration, database-backed memory/history,
calendar/reminder backends, and interface-agnostic input/output APIs. It does not
ship with a CLI or desktop frontend.

Interface-specific work is intended to live in separate branches that call into
the core runtime through the shared API surface.

## Current Architecture

Aura currently includes:

- A headless runtime engine
- Interface-agnostic `InputManager` and `OutputManager`
- Runtime context and module loading
- Scheduler, task manager, and event manager
- MySQL-backed persistence
- Conversation history and long-term memory
- Calendar backend with events, tasks, reminders, recurrence, exceptions, and timezone support
- Standalone reminders backend

The runtime is designed so an interface branch can attach by calling:

- `context.inputManager.submit(...)`
- `context.engine.handleInput(...)`
- `context.outputManager.subscribe(...)`

## Branch Intent

The purpose of `master` is to remain a stable backend foundation.

That means this branch should contain:

- shared runtime systems
- backend modules
- storage and scheduling logic
- interface-independent APIs

That means this branch should not contain:

- CLI workflows
- desktop UI implementations
- mobile UI implementations
- web interface implementations

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
python run_tests.py --suite logger
python run_tests.py --suite short_memory
python run_tests.py --suite long_memory
python run_tests.py --suite calendar
python run_tests.py --suite reminders
python run_tests.py --suite llm
python run_tests.py --suite mysql_integration
```

Optional live LLM connectivity test:

```powershell
$env:RUN_LIVE_LLM_TEST="true"
$env:LLM_ENDPOINT="http://localhost:11434/api/generate"
$env:LLM_MODEL="llama3.1:8b"
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
