"""Memory panel for the Aura Developer UI."""

from __future__ import annotations

from interface.developerUI.panels.basePanel import TextPanel


class MemoryPanel(TextPanel):
    """Display retrieval scores, injected memories, and memory summaries."""

    title = "Memory"

    def refresh(self, snapshot):
        memory = snapshot.memory
        lines = [
            "[MEMORY]",
            f"Manager: {'Available' if memory.get('managerAvailable') else 'Unavailable'}",
            f"Database: {memory.get('databasePath', '') or 'Unknown'}",
            f"Stored: {memory.get('storedCount', 0)}",
            f"Retrieved: {memory.get('retrieved', 0)}",
            f"Injected: {memory.get('injected', 0)}",
            f"Filtered: {memory.get('filtered', 0)}",
            f"Top Score: {memory.get('topScore', 0.0)}",
        ]
        semantic = memory.get("semantic") or {}
        lines.extend(
            [
                "",
                "Semantic Memory:",
                f"Enabled: {'Yes' if semantic.get('enabled') else 'No'}",
                f"Provider: {semantic.get('provider') or 'Unknown'}",
                f"Indexed: {semantic.get('indexedCount', 0)}",
                f"Last Index: {semantic.get('lastIndexAt') or 'Never'}",
            ]
        )
        if semantic.get("lastSearchText"):
            lines.append(f"Last Search: {semantic.get('lastSearchText')}")
        lastSearch = semantic.get("lastSearch") or {}
        if isinstance(lastSearch, dict) and lastSearch.get("combinedCount") is not None:
            lines.append(f"Last Results: {lastSearch.get('combinedCount')} (semantic={lastSearch.get('semanticCount', 0)}, keyword={lastSearch.get('keywordCount', 0)})")
        if semantic.get("lastError"):
            lines.append(f"Semantic Error: {semantic.get('lastError')}")
        if memory.get("refreshError"):
            lines.extend(["", f"Refresh Error: {memory.get('refreshError')}"])
        lines.extend(["", "Stored Memories:"])
        items = memory.get("items") or []
        if items:
            for item in items:
                content = str(item.get("content") or "")
                if len(content) > 120:
                    content = content[:117].rstrip() + "..."
                lines.append(
                    f"- [{item.get('category', '')}] {item.get('title', '')} "
                    f"(importance={float(item.get('importance') or 0.0):.2f}, source={item.get('source', '')})"
                )
                if content:
                    lines.append(f"  {content}")
        else:
            lines.append("No structured memories stored yet.")
        lines.extend([
            "",
            "Debug Output:",
            memory.get("debugOutput", "") or "No memory retrieval debug output yet.",
        ])
        self.setText("\n".join(str(line) for line in lines))
