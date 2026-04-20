# Aura Windows Interface Branch

## Overview

This branch, `interface/windowsOS`, contains Aura's Windows desktop interface
work. It builds on the shared headless runtime and adds a Tkinter shell for
chat, notifications, reminders, and calendar workflows.

The original root `README.md` is kept unchanged so the shared project
description stays aligned with the backend foundation.

## Windows App

The Windows desktop app lives in:

```text
core/interface/desktopInterface/windows/
```

Primary entry point:

```text
core/interface/desktopInterface/windows/runAuraWindows.py
```

The current Windows UI includes:

- Chat input and transcript view
- Sidebar navigation
- Notifications overlay
- Reminders page with a reminder composer
- Calendar page with day, week, month, and year views
- Calendar event composer
- Calendar agenda cards for events, tasks, and reminders

The calendar UI uses the backend calendar API:

- `context.calendar.buildDayView(...)`
- `context.calendar.buildWeekView(...)`
- `context.calendar.buildMonthView(...)`
- `context.calendar.createEvent(...)`

Year view aggregates all twelve month views for the selected year.

## Setup

Install dependencies:

```powershell
python -m pip install -r requirements.txt
```

Primary runtime config file:

```text
config.yml
```

The runtime expects database and LLM settings in the config file or matching
environment variables for live integrations.

## Running The Windows App

Launch the Windows desktop shell:

```powershell
python core\interface\desktopInterface\windows\runAuraWindows.py
```

The app initializes the runtime context, starts scheduler services, opens the
Tkinter window, and shuts runtime services down when the window closes.

## Building The Windows Executable

Build with the helper script:

```powershell
python core\interface\desktopInterface\windows\buildAuraExe.py
```

The helper uses PyInstaller and writes the executable to `dist/`.

## Testing

Run all tests:

```powershell
python run_tests.py
```

Run the Windows interface suite:

```powershell
python run_tests.py --suite windows_interface
```

Useful related suites:

```powershell
python run_tests.py --suite build
python run_tests.py --suite runtime_smoke
python run_tests.py --suite calendar
python run_tests.py --suite reminders
python run_tests.py --suite notifications
```
