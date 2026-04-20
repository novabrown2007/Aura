# Aura Assistant - Client Overview

## Summary

Aura is a private personal assistant platform designed to help with everyday
planning, reminders, scheduling, memory, and conversational tasks.

The system combines a modular assistant runtime with a Windows desktop
interface. The current Windows experience includes chat, notifications,
reminders, and calendar views for day, week, month, and year planning.

## What Aura Does

Aura is built to support:

- Natural language assistant conversations
- Personal reminders
- Calendar events and task planning
- Notifications
- Long-term memory and conversation history
- Local desktop workflows on Windows

The assistant is designed as a private, extensible system rather than a
single-purpose app.

## Current Windows Experience

The Windows app provides:

- A chat screen for assistant interaction
- A reminders screen for creating and reviewing reminders
- A notification panel for recent notifications
- A calendar screen with day, week, month, and year views
- A calendar event creator for scheduling new events

The calendar interface is styled around a clean agenda workflow: fast movement
between time ranges, clear event/task/reminder cards, and simple creation flows.

## Technical Foundation

Aura is powered by a headless core runtime. The desktop interface is one layer
on top of that runtime.

The backend includes:

- Runtime lifecycle management
- Input and output APIs
- Intent routing
- Scheduler and task systems
- MySQL-backed persistence
- Calendar and reminder modules
- LLM integration
- Conversation history and memory

This structure allows the Windows interface to evolve without tightly coupling
the assistant logic to one frontend.

## Current Status

Aura is under active private development.

The Windows branch currently focuses on making the desktop assistant usable for:

- Chat interaction
- Reminder management
- Calendar planning
- Notification review

Additional polish, packaging, and live integration testing are expected as the
desktop experience matures.

## Ownership

Aura is private software owned by Nova Brown. The project is intended for
private development, experimentation, and controlled demonstration only.
