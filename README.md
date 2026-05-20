# Aura Assistant

**Author:** Nova Brown  
**Copyright:** (c) Nova Brown - All Rights Reserved

## Overview

Aura is a personal assistant runtime with shared backend systems and separate
interface packages in one master branch.

The backend owns runtime startup, persistence, scheduling, LLM integration,
memory/history, calendar, reminders, notifications, and system lifecycle logic.
Each interface package is kept isolated so platform-specific builds can include
only the files needed for that target.

## Project Structure

```text
config/                 Runtime configuration loading
core/                   Engine, runtime context, router, threading systems
modules/                Backend modules and persistence integrations
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

## Interfaces

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
python run_tests.py --suite interfaces
python run_tests.py --suite reminders
python run_tests.py --suite llm
python run_tests.py --suite mysql_integration
```

Interface-specific tests live in `tests/interfaceTests/`:

```text
tests/interfaceTests/test_windows_interface.py
tests/interfaceTests/test_android_interface.py
tests/interfaceTests/test_web_interface.py
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
