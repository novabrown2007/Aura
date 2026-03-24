"""Terminal interface layer for the Aura CLI branch."""

from __future__ import annotations

from modules.commands.baseCommand import CommandResult


class CliInterface:
    """
    Run a terminal conversation loop on top of Aura's headless runtime.
    """

    def __init__(self, context, input_func=input, output_func=print):
        """Store context and terminal IO callables."""

        self.context = context
        self.input = input_func
        self.output = output_func
        self.logger = context.logger.getChild("CLI.Interface") if context.logger else None

    def run(self):
        """Run the interactive CLI loop until shutdown or restart is requested."""

        self.output("Aura CLI ready. Use /help for commands.")

        while not self.context.should_exit:
            try:
                raw_text = self.input("> ")
            except EOFError:
                self.context.system.shutdown()
                break
            except KeyboardInterrupt:
                self.output("")
                self.context.system.shutdown()
                break

            text = str(raw_text).strip()
            if not text:
                continue

            if self.context.commandHandler.isCommand(text):
                result = self.context.commandHandler.handle(text)
                self._emitCommandResult(result)
                continue

            packet = self.context.engine.handleInput(text, source="cli")
            self.output(str(packet.get("response", "")))

    def _emitCommandResult(self, result: CommandResult):
        """Render one command result to the terminal."""

        message = str(result.message or "")
        if message:
            self.output(message)
