# Aura Assistant

**Author:** Nova Brown  
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
core/                   Engine, runtime context, router, threading systems
modules/                Backend modules and persistence integrations
modules/home_automation/
                        Home automation bridge, device, and service-control backend
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

All visual interfaces expose chat, reminders, calendar, notifications, and home
automation controls. Home automation UI features can refresh bridge state, show
lights/cameras/devices, and request bridge or hub service startup. The web UI
also exposes direct light and camera controls.

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

It talks to two external services:

- the home automation bridge for devices, lights, cameras, and bridge notifications
- the service-control endpoint for starting the bridge and hub services

Supported backend operations include:

- bridge connect/refresh/state
- list devices, lights, and cameras
- light on/off, brightness, color temperature, and color
- camera stream start/stop and snapshot
- bridge notification list/queue
- start bridge and start hub service-control requests

Configuration can be supplied through `config.yml` under `home_automation`:

```yaml
home_automation:
  refresh_interval_seconds: 5.0
  bridge:
    host: 127.0.0.1
    port: 8080
    use_ssl: false
    api_token: ""
    timeout_seconds: 3.0
  control:
    host: 127.0.0.1
    port: 8091
    use_ssl: false
    api_token: ""
    timeout_seconds: 5.0
    start_bridge_path: /control/startbridge
    start_hub_path: /control/starthub
```

Environment variable fallbacks are also supported:

```text
HOME_AUTOMATION_BRIDGE_HOST
HOME_AUTOMATION_BRIDGE_PORT
HOME_AUTOMATION_BRIDGE_SSL
HOME_AUTOMATION_BRIDGE_TOKEN
HOME_AUTOMATION_BRIDGE_TIMEOUT
HOME_AUTOMATION_CONTROL_HOST
HOME_AUTOMATION_CONTROL_PORT
HOME_AUTOMATION_CONTROL_SSL
HOME_AUTOMATION_CONTROL_TOKEN
HOME_AUTOMATION_CONTROL_TIMEOUT
HOME_AUTOMATION_START_BRIDGE_PATH
HOME_AUTOMATION_START_HUB_PATH
HOME_AUTOMATION_REFRESH_SECONDS
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
python run_tests.py --suite logger
python run_tests.py --suite short_memory
python run_tests.py --suite long_memory
python run_tests.py --suite calendar
python run_tests.py --suite interfaces
python run_tests.py --suite home_automation
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
