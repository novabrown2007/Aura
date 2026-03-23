# Aura Command Contract

## Purpose
This document defines the behavioral contract for Aura CLI commands so new commands remain consistent, testable, and predictable as the command surface grows.

## Command Taxonomy
- Root commands: global utilities (`/help`, `/status`, `/version`).
- Namespace commands: grouped commands under a handler (`/system ...`, `/debug ...`, `/config ...`, `/memory ...`, `/history ...`).
- Each namespace must have a dedicated `...CommandHandler` class.

## Naming Rules
- Package folders use the existing scheme: `...Commands`.
- Files use lower-camel style already used in the repo, for example `memorySetCommand.py`.
- Command classes are PascalCase and end with `Command`.
- Handler classes are PascalCase and end with `CommandHandler`.
- Command identifiers (`name`) are lowercase and space-free.

## Registration Rules
- `CommandRegistry` is the central wiring point for command handlers and commands.
- Each command must self-register in `__init__` by calling the appropriate handler registration method.
- `modules.commands.register(context)` must remain the entrypoint used by `ModuleLoader`.
- `main.py` must not manually wire individual commands.

## Execution Contract
- All command execution methods follow `execute(args: list[str]) -> str`.
- Command handlers route by first token and call `command.execute(parts[1:])`.
- Invalid command input must return the standardized invalid-command message used by handlers.
- Each command must provide a clear usage string when required arguments are missing.

## Output Contract
- Command responses are user-facing plain strings.
- Success responses should be concise and explicit.
- Error responses should:
  - identify what failed,
  - include the actionable next step when possible (usage, missing key, missing file, etc.),
  - avoid stack traces in normal output.

## Help Contract
- Every command must set `help_message`.
- Every handler must implement `getCommands()` so `/help` can enumerate commands consistently.
- `/help <term>` should match both full command path and command name.

## Argument and Parsing Rules
- Use positional args for simple commands.
- Use optional flags only when needed (`--force` style).
- Quote-aware value handling should be implemented in commands that accept free text (`/memory set ...`).
- Keep parsing in command classes unless shared parsing logic is introduced explicitly.

## Confirmation and Destructive Actions
- Destructive operations (clear/delete/shutdown/restart/import overwrite semantics) must:
  - use explicit command forms,
  - provide unmistakable confirmation text.
- If interactive confirmations are introduced later, they must be standardized across destructive commands.

## Configuration and Runtime State
- `/config set` currently updates runtime config only (in-memory).
- Commands that rely on runtime dependencies must use `context.require(...)`.
- Commands should degrade gracefully when optional systems are unavailable, with clear failure messaging.

## Testing Requirements
- New commands must include test coverage in command registry/runtime command tests.
- Command behavior changes require updates to expected help output and usage/error assertions.
- Real service tests (LLM/MySQL) must be env-gated and skipped by default.

## Extension Checklist for New Commands
1. Add command file/class in the correct namespace package.
2. Implement `name`, `help_message`, and `execute(args)`.
3. Register command in `CommandRegistry`.
4. Ensure namespace handler exposes `getCommands()`.
5. Add/extend automated tests.
6. Update docs when command semantics differ from this contract.

