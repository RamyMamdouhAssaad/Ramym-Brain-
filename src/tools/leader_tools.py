"""Team Leader MCP tools - people, 1:1s, delegation, feedback."""

import json

from mcp.server import Server
from mcp.types import Tool, TextContent

from src.memory.store import log_person_note, log_one_on_one, delegate_task
from src.memory.search import search_person, get_delegations


def register_leader_tools(server: Server) -> None:
    """Register team leader MCP tools."""

    original_list_tools = None
    original_call_tool = None

    if hasattr(server, "_tool_handlers"):
        original_list_tools = server._tool_handlers.get("list_tools")
        original_call_tool = server._tool_handlers.get("call_tool")

    LEADER_TOOLS = [
        Tool(
            name="person_note",
            description=(
                "Add a note about a person - observations, strengths, growth areas, "
                "or general context you want to remember about them."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string",
                        "description": "Person's name",
                    },
                    "note": {
                        "type": "string",
                        "description": "The observation or note",
                    },
                    "category": {
                        "type": "string",
                        "description": "Category: general, strength, growth, feedback, context",
                        "default": "general",
                    },
                },
                "required": ["name", "note"],
            },
        ),
        Tool(
            name="person_context",
            description=(
                "Get all context about a person - notes, recent 1:1s, "
                "delegated tasks, observations. Use before meetings."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string",
                        "description": "Person's name",
                    },
                },
                "required": ["name"],
            },
        ),
        Tool(
            name="log_1on1",
            description="Log notes and action items from a 1:1 meeting.",
            inputSchema={
                "type": "object",
                "properties": {
                    "person": {
                        "type": "string",
                        "description": "Who you had the 1:1 with",
                    },
                    "notes": {
                        "type": "string",
                        "description": "Key points discussed",
                    },
                    "action_items": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Action items from the meeting",
                    },
                },
                "required": ["person", "notes"],
            },
        ),
        Tool(
            name="delegate",
            description="Track a task you've delegated to someone.",
            inputSchema={
                "type": "object",
                "properties": {
                    "task": {
                        "type": "string",
                        "description": "What you delegated",
                    },
                    "assigned_to": {
                        "type": "string",
                        "description": "Who you assigned it to",
                    },
                    "due": {
                        "type": "string",
                        "description": "Due date (optional, ISO format)",
                    },
                    "priority": {
                        "type": "string",
                        "description": "Priority: low, medium, high",
                        "default": "medium",
                    },
                },
                "required": ["task", "assigned_to"],
            },
        ),
        Tool(
            name="delegation_status",
            description="Check status of delegated tasks - all or filtered by person.",
            inputSchema={
                "type": "object",
                "properties": {
                    "person": {
                        "type": "string",
                        "description": "Filter by person (optional, shows all if empty)",
                    },
                    "status": {
                        "type": "string",
                        "description": "Filter by status: pending, done, overdue",
                        "default": "pending",
                    },
                },
            },
        ),
        Tool(
            name="prep_1on1",
            description=(
                "Prepare for a 1:1 meeting - shows last meeting notes, "
                "pending action items, recent observations, and delegated tasks."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "person": {
                        "type": "string",
                        "description": "Who you're meeting with",
                    },
                },
                "required": ["person"],
            },
        ),
    ]

    @server.list_tools()
    async def list_tools() -> list[Tool]:
        tools = []
        if original_list_tools:
            tools = await original_list_tools()
        tools.extend(LEADER_TOOLS)
        return tools

    @server.call_tool()
    async def call_tool(name: str, arguments: dict) -> list[TextContent]:
        if name == "person_note":
            result = await log_person_note(
                name=arguments["name"],
                note=arguments["note"],
                category=arguments.get("category", "general"),
            )
            return [TextContent(
                type="text",
                text=f"Note saved for {result['person']} [{result['category']}]",
            )]

        elif name == "person_context":
            context = await search_person(arguments["name"])
            if not context:
                return [TextContent(type="text", text=f"No records found for '{arguments['name']}'")]

            parts = [f"## {context['name']}\n"]

            if context["notes"]:
                parts.append("**Notes:**")
                for n in context["notes"][:10]:
                    parts.append(f"- [{n['category']}] {n['note']} ({n['date'][:10]})")

            if context["recent_1on1s"]:
                parts.append("\n**Recent 1:1s:**")
                for m in context["recent_1on1s"]:
                    parts.append(f"- {m['date'][:10]}: {m['notes'][:100]}")
                    if m["action_items"]:
                        for ai in m["action_items"]:
                            parts.append(f"  - [ ] {ai}")

            if context["delegations"]:
                parts.append("\n**Delegated Tasks:**")
                for d in context["delegations"]:
                    status_icon = "✅" if d["status"] == "done" else "⏳"
                    due = f" (due: {d['due']})" if d["due"] else ""
                    parts.append(f"- {status_icon} {d['task']}{due} [{d['priority']}]")

            return [TextContent(type="text", text="\n".join(parts))]

        elif name == "log_1on1":
            result = await log_one_on_one(
                person=arguments["person"],
                notes=arguments["notes"],
                action_items=arguments.get("action_items"),
            )
            items = result["action_items"]
            action_str = f" | {len(items)} action items" if items else ""
            return [TextContent(
                type="text",
                text=f"1:1 logged with {result['person']}{action_str}",
            )]

        elif name == "delegate":
            result = await delegate_task(
                task=arguments["task"],
                assigned_to=arguments["assigned_to"],
                due=arguments.get("due"),
                priority=arguments.get("priority", "medium"),
            )
            return [TextContent(
                type="text",
                text=f"Delegated: '{result['task']}' → {result['assigned_to']} [{result['priority']}]",
            )]

        elif name == "delegation_status":
            results = await get_delegations(
                person=arguments.get("person"),
                status=arguments.get("status", "pending"),
            )
            if not results:
                return [TextContent(type="text", text="No pending delegations.")]

            formatted = "\n".join(
                f"- {r['task']} → {r['assigned_to']}"
                f"{' (due: ' + r['due'] + ')' if r['due'] else ''}"
                f" [{r['priority']}]"
                for r in results
            )
            return [TextContent(type="text", text=f"**Delegations ({len(results)}):**\n{formatted}")]

        elif name == "prep_1on1":
            context = await search_person(arguments["person"])
            if not context:
                return [TextContent(
                    type="text",
                    text=f"No records for '{arguments['person']}'. This will be your first tracked 1:1.",
                )]

            parts = [f"## 1:1 Prep: {context['name']}\n"]

            # Last meeting
            if context["recent_1on1s"]:
                last = context["recent_1on1s"][0]
                parts.append(f"**Last 1:1** ({last['date'][:10]}):")
                parts.append(f"  {last['notes'][:200]}")
                if last["action_items"]:
                    parts.append("  **Action items to follow up:**")
                    for ai in last["action_items"]:
                        parts.append(f"  - [ ] {ai}")

            # Pending delegations
            pending = [d for d in context["delegations"] if d["status"] == "pending"]
            if pending:
                parts.append(f"\n**Pending tasks assigned ({len(pending)}):**")
                for d in pending:
                    parts.append(f"- {d['task']} [{d['priority']}]")

            # Recent notes
            if context["notes"]:
                parts.append("\n**Recent observations:**")
                for n in context["notes"][:5]:
                    parts.append(f"- [{n['category']}] {n['note']}")

            return [TextContent(type="text", text="\n".join(parts))]

        # Pass to previous handler
        if original_call_tool:
            return await original_call_tool(name, arguments)
        return [TextContent(type="text", text=f"Unknown tool: {name}")]
