"""Developer MCP tools - decisions, errors, snippets, tech debt."""

import json

from mcp.server import Server
from mcp.types import Tool, TextContent

from src.memory.store import log_decision, log_error, save_snippet
from src.memory.search import search_decisions, search_errors, search_snippets


def register_developer_tools(server: Server) -> None:
    """Register developer-specific MCP tools."""

    original_list_tools = None
    original_call_tool = None

    # Get existing handlers to chain
    if hasattr(server, "_tool_handlers"):
        original_list_tools = server._tool_handlers.get("list_tools")
        original_call_tool = server._tool_handlers.get("call_tool")

    DEVELOPER_TOOLS = [
        Tool(
            name="log_decision",
            description=(
                "Log a technical or architecture decision with reasoning. "
                "Use when you choose one approach over another."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "what": {
                        "type": "string",
                        "description": "The decision made (e.g., 'Use pgvector over Pinecone')",
                    },
                    "why": {
                        "type": "string",
                        "description": "Reasoning (e.g., 'Cost, no vendor lock-in, already using Postgres')",
                    },
                    "context": {
                        "type": "string",
                        "description": "Additional context (project, PR, ticket)",
                        "default": "",
                    },
                    "revisit_date": {
                        "type": "string",
                        "description": "When to revisit this decision (ISO date, optional)",
                    },
                },
                "required": ["what", "why"],
            },
        ),
        Tool(
            name="log_error",
            description=(
                "Log an error and its fix to the error journal. "
                "Next time you see the same error, the fix is instant."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "error": {
                        "type": "string",
                        "description": "The error message or description",
                    },
                    "fix": {
                        "type": "string",
                        "description": "How you fixed it",
                    },
                    "tags": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Tags (e.g., ['postgres', 'prod', 'connection'])",
                    },
                },
                "required": ["error", "fix"],
            },
        ),
        Tool(
            name="save_snippet",
            description="Save a reusable code snippet or pattern for later reference.",
            inputSchema={
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string",
                        "description": "Short name for the snippet",
                    },
                    "code": {
                        "type": "string",
                        "description": "The code snippet",
                    },
                    "language": {
                        "type": "string",
                        "description": "Programming language",
                        "default": "python",
                    },
                    "description": {
                        "type": "string",
                        "description": "When/why to use this snippet",
                        "default": "",
                    },
                },
                "required": ["name", "code"],
            },
        ),
        Tool(
            name="search_decisions",
            description="Search past architecture and technical decisions.",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "What decision are you looking for?",
                    },
                    "limit": {"type": "integer", "default": 5},
                },
                "required": ["query"],
            },
        ),
        Tool(
            name="search_errors",
            description="Search the error journal for past errors and their fixes.",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Error message or description to search for",
                    },
                    "limit": {"type": "integer", "default": 5},
                },
                "required": ["query"],
            },
        ),
        Tool(
            name="search_snippets",
            description="Search saved code snippets and patterns.",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "What snippet are you looking for?",
                    },
                    "limit": {"type": "integer", "default": 5},
                },
                "required": ["query"],
            },
        ),
    ]

    @server.list_tools()
    async def list_tools() -> list[Tool]:
        # Chain with memory tools
        tools = []
        if original_list_tools:
            tools = await original_list_tools()
        tools.extend(DEVELOPER_TOOLS)
        return tools

    @server.call_tool()
    async def call_tool(name: str, arguments: dict) -> list[TextContent]:
        if name == "log_decision":
            result = await log_decision(
                what=arguments["what"],
                why=arguments["why"],
                context=arguments.get("context", ""),
                revisit_date=arguments.get("revisit_date"),
            )
            return [TextContent(type="text", text=f"Decision logged: {json.dumps(result, indent=2)}")]

        elif name == "log_error":
            result = await log_error(
                error=arguments["error"],
                fix=arguments["fix"],
                tags=arguments.get("tags"),
            )
            status = result["status"]
            if status == "updated_existing":
                return [TextContent(
                    type="text",
                    text=f"Updated existing error (seen {result['occurrences']} times now)",
                )]
            return [TextContent(type="text", text=f"Error logged: {json.dumps(result, indent=2)}")]

        elif name == "save_snippet":
            result = await save_snippet(
                name=arguments["name"],
                code=arguments["code"],
                language=arguments.get("language", "python"),
                description=arguments.get("description", ""),
            )
            return [TextContent(type="text", text=f"Snippet saved: {result['name']} ({result['language']})")]

        elif name == "search_decisions":
            results = await search_decisions(
                query=arguments["query"],
                limit=arguments.get("limit", 5),
            )
            if not results:
                return [TextContent(type="text", text="No matching decisions found.")]
            formatted = "\n\n".join(
                f"**[{r['created_at'][:10] if r['created_at'] else '?'}]** {r['what']}\n"
                f"  Why: {r['why']}\n"
                f"  Context: {r['context'] or 'none'}"
                for r in results
            )
            return [TextContent(type="text", text=f"Found {len(results)} decisions:\n\n{formatted}")]

        elif name == "search_errors":
            results = await search_errors(
                query=arguments["query"],
                limit=arguments.get("limit", 5),
            )
            if not results:
                return [TextContent(type="text", text="No matching errors in journal.")]
            formatted = "\n\n".join(
                f"**Error:** {r['error']}\n"
                f"**Fix:** {r['fix']}\n"
                f"  Seen {r['occurrences']}x | Last: {r['last_seen']}"
                for r in results
            )
            return [TextContent(type="text", text=f"Found {len(results)} errors:\n\n{formatted}")]

        elif name == "search_snippets":
            results = await search_snippets(
                query=arguments["query"],
                limit=arguments.get("limit", 5),
            )
            if not results:
                return [TextContent(type="text", text="No matching snippets found.")]
            formatted = "\n\n".join(
                f"**{r['name']}** ({r['language']})\n"
                f"{r['description']}\n```{r['language']}\n{r['code']}\n```"
                for r in results
            )
            return [TextContent(type="text", text=formatted)]

        # Pass to previous handler if not our tool
        if original_call_tool:
            return await original_call_tool(name, arguments)
        return [TextContent(type="text", text=f"Unknown tool: {name}")]
