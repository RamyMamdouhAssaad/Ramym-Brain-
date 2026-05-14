"""Memory MCP tools - remember, recall, daily/weekly summaries."""

import json

from mcp.server import Server
from mcp.types import Tool, TextContent

from src.memory.store import remember
from src.memory.search import search_memories, get_daily_summary


def register_memory_tools(server: Server) -> None:
    """Register memory-related MCP tools on the server."""

    @server.list_tools()
    async def list_tools() -> list[Tool]:
        return [
            Tool(
                name="remember",
                description=(
                    "Save something to Ramy's brain. Use for decisions, notes, "
                    "observations, meeting takeaways, or anything worth remembering later."
                ),
                inputSchema={
                    "type": "object",
                    "properties": {
                        "content": {
                            "type": "string",
                            "description": "What to remember. Be specific and include context.",
                        },
                        "tags": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Tags for categorization (e.g., ['architecture', 'auth'])",
                        },
                        "source": {
                            "type": "string",
                            "description": "Where this came from (vscode, email, meeting, jira, manual)",
                            "default": "manual",
                        },
                        "category": {
                            "type": "string",
                            "description": "Category: general, decision, observation, meeting, task",
                            "default": "general",
                        },
                    },
                    "required": ["content"],
                },
            ),
            Tool(
                name="recall",
                description=(
                    "Search Ramy's brain for memories, decisions, notes. Uses semantic search "
                    "so you don't need exact keywords - describe what you're looking for."
                ),
                inputSchema={
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "What to search for. Can be a question or keywords.",
                        },
                        "tags": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Filter by tags (optional)",
                        },
                        "limit": {
                            "type": "integer",
                            "description": "Max results to return",
                            "default": 5,
                        },
                    },
                    "required": ["query"],
                },
            ),
            Tool(
                name="daily_summary",
                description=(
                    "Get a summary of today's activities - what was remembered, "
                    "decisions made, pending delegations, and tasks."
                ),
                inputSchema={
                    "type": "object",
                    "properties": {},
                },
            ),
        ]

    @server.call_tool()
    async def call_tool(name: str, arguments: dict) -> list[TextContent]:
        if name == "remember":
            result = await remember(
                content=arguments["content"],
                tags=arguments.get("tags"),
                source=arguments.get("source", "manual"),
                category=arguments.get("category", "general"),
            )
            return [TextContent(type="text", text=f"Remembered: {json.dumps(result, indent=2)}")]

        elif name == "recall":
            results = await search_memories(
                query=arguments["query"],
                limit=arguments.get("limit", 5),
                tags=arguments.get("tags"),
            )
            if not results:
                return [TextContent(type="text", text="No matching memories found.")]

            formatted = "\n\n".join(
                f"**[{r['created_at'][:10]}]** ({r['source']}) {r['content']}\n"
                f"  Tags: {', '.join(r.get('tags', []))}"
                for r in results
            )
            return [TextContent(type="text", text=f"Found {len(results)} memories:\n\n{formatted}")]

        elif name == "daily_summary":
            summary = await get_daily_summary()
            parts = [f"**Today's Summary** ({summary['memories_today']} items recorded)\n"]

            if summary["activities"]:
                parts.append("**Activities:**")
                for a in summary["activities"][:10]:
                    parts.append(f"- [{a['source']}] {a['content']}")

            if summary["decisions_today"]:
                parts.append("\n**Decisions:**")
                for d in summary["decisions_today"]:
                    parts.append(f"- {d['what']} — because: {d['why']}")

            if summary["pending_delegations"]:
                parts.append("\n**Pending Delegations:**")
                for d in summary["pending_delegations"]:
                    due = f" (due: {d['due']})" if d["due"] else ""
                    parts.append(f"- {d['task']} → {d['assigned_to']}{due}")

            return [TextContent(type="text", text="\n".join(parts))]

        return [TextContent(type="text", text=f"Unknown tool: {name}")]
