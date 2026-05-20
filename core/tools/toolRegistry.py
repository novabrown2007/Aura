"""Central registry for deterministic Aura tools."""

from __future__ import annotations

from core.tools.tool import Tool


class ToolRegistry:
    """Registry of tools provided by Aura modules and plugins."""

    def __init__(self, context=None):
        """Create an empty registry."""

        self.context = context
        self.tools: dict[str, Tool] = {}
        self.logger = context.logger.getChild("ToolRegistry") if context and context.logger else None

    def registerTool(self, tool: Tool):
        """Register or replace a tool definition."""

        self.tools[tool.name] = tool
        if self.logger:
            self.logger.info(f"Registered tool: {tool.name}")

    def registerTools(self, tools):
        """Register a collection of tools."""

        for tool in tools:
            self.registerTool(tool)

    def unregisterTool(self, name: str):
        """Remove a tool from the registry."""

        self.tools.pop(name, None)

    def getTool(self, name: str) -> Tool | None:
        """Return a tool by name."""

        return self.tools.get(name)

    def getAvailableTools(
        self,
        includeUnsafe: bool = False,
        offlineMode: bool = False,
        includeConfirmRequired: bool = True,
    ) -> list[Tool]:
        """Return tools available under the supplied policy constraints."""

        available = []
        for tool in self.tools.values():
            if not includeUnsafe and not tool.safe:
                continue
            if offlineMode and not tool.offlineAllowed:
                continue
            if not includeConfirmRequired and tool.confirmRequired:
                continue
            available.append(tool)
        return available

    def exportSchemas(self, **filters):
        """Export available tools as prompt-friendly schemas."""

        return [tool.toSchema() for tool in self.getAvailableTools(**filters)]

    def searchByCapability(self, capability: str) -> list[Tool]:
        """Search tools by capability/module/name text."""

        needle = capability.lower()
        return [
            tool
            for tool in self.tools.values()
            if needle in tool.name.lower()
            or needle in tool.module.lower()
            or needle in tool.description.lower()
        ]

