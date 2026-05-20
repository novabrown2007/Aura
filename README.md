# Aura Assistant

**Author:** Nova Brown  
**Copyright:** © Nova Brown - All Rights Reserved

## Overview

Aura is a backend-only personal assistant runtime.

The `master` branch contains shared runtime systems, persistence, scheduling,
LLM integration, memory/history, calendar, reminder, notification, and system
lifecycle backends. It intentionally does not ship UI, CLI, desktop, mobile,
web, speech, or other user-facing interface code.

## Current Architecture

Aura currently includes:

- A headless runtime engine
- Runtime context and module loading
- Scheduler, task manager, and event manager
- MySQL-backed persistence
- Conversation history and long-term memory
- Calendar backend with events, tasks, reminders, recurrence, exceptions, and timezone support
- Standalone reminders backend

## Branch Intent

The purpose of `master` is to remain a stable backend foundation.

That means this branch should contain:

- shared runtime systems
- backend modules
- storage and scheduling logic
- backend service APIs

That means this branch should not contain:

- CLI workflows
- desktop UI implementations
- mobile UI implementations
- web interface implementations
- speech input/output implementations
- generated application bundles or UI build artifacts

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
