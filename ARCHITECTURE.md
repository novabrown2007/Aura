# Aura Architecture

Aura is organized into five top-level layers:

| Layer | Responsibility |
| --- | --- |
| `core/` | foundational runtime, event, threading, logging, config, and engine systems |
| `assistant/` | conversation, memory, personality, clarification, suggestions, orchestration |
| `interface/` | voice input/output, desktop/mobile surfaces, notifications, presentation |
| `modules/` | deterministic capability integrations such as calendar, reminders, home automation |
| `providers/` | external AI and service adapters such as Ollama, Gemini, Whisper, Piper |

## Dependency Rules

- `assistant/` depends on `core/`, `modules/`, and `providers/`
- `interface/` depends on `assistant/` and `core/`
- `modules/` depends on `core/`
- `providers/` depends on `core/`
- `core/` does not depend on assistant cognition packages

## Layer Responsibilities

### `core/`

Core contains the foundational runtime and engine systems:

- runtime context and startup/shutdown
- logging
- event bus
- threading and scheduling
- configuration loading
- observability
- interruption/cancellation primitives
- transport and infrastructure utilities

Legacy compatibility shims may remain in `core/` while code is migrated, but new
assistant cognition should be implemented in `assistant/`.

### `assistant/`

Assistant contains all short-term cognition and behavior systems:

- conversation continuity
- memory management and retrieval
- personality, tone, humor, and suggestion systems
- clarification and reference resolution
- behavior governance
- response shaping and orchestration

### `interface/`

Interface contains input/output surfaces:

- voice capture and playback
- wake word detection
- VAD endpoint detection
- push-to-talk
- desktop/web/mobile UIs
- notifications and overlays

### `modules/`

Modules expose deterministic capabilities:

- calendar
- reminders
- home automation
- notifications
- system control
- future integrations such as Spotify, email, browser automation

### `providers/`

Providers wrap external services and AI backends:

- Gemini
- Ollama
- OpenAI
- Whisper
- Piper

Providers should remain service wrappers. They do not own assistant behavior.

## Event Flow

The event bus remains in `core/events/` and is used by higher layers for
decoupled communication.

Typical flow:

1. interface captures input
2. assistant resolves context and intent
3. modules execute deterministic capabilities
4. providers generate text or structured output when needed
5. assistant shapes the final response
6. interface presents the response

## Migration Notes

Aura currently keeps compatibility shims in legacy package paths so existing
imports continue to work while the new layer boundaries are adopted. New code
should use the canonical packages:

- `assistant.*`
- `interface.*`
- `modules.*`
- `providers.*`
- `core.*` only for foundational systems

