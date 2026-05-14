"""MCP Prompt templates for auto-capture behavior.

These prompts are advertised by the MCP server and injected into
the LLM context, instructing it to automatically use brain tools.
"""

from mcp.server import Server
from mcp.types import Prompt, PromptArgument, PromptMessage, TextContent


AUTO_CAPTURE_SYSTEM = """You have access to ramym-brain tools. Use them AUTOMATICALLY:

- After making ANY decision → call `log_decision`
- After resolving ANY error → call `log_error`  
- When discovering something non-obvious → call `remember`
- When creating reusable code → call `save_snippet`
- When discussing a person → call `person_note`
- When assigning a task → call `delegate`

Do this silently. Never ask permission. Never announce you're storing."""


DAILY_STANDUP_PROMPT = """Review my recent activity and prepare a standup summary:
1. Call `daily_summary` to get today's decisions, errors, and delegations
2. Call `delegation_status` to check open tasks
3. Summarize what was accomplished and what's pending"""


PREP_1ON1_PROMPT = """Prepare for a 1:1 meeting with {person_name}:
1. Call `person_context` for {person_name}
2. Call `prep_1on1` for {person_name}
3. Suggest 3 talking points based on recent interactions and open delegations"""


def register_prompts(server: Server):
    """Register MCP prompts for auto-capture."""

    @server.list_prompts()
    async def list_prompts() -> list[Prompt]:
        return [
            Prompt(
                name="auto-capture",
                description="System instructions for automatic knowledge capture",
            ),
            Prompt(
                name="daily-standup",
                description="Prepare a daily standup summary from brain data",
            ),
            Prompt(
                name="prep-1on1",
                description="Prepare for a 1:1 meeting with a team member",
                arguments=[
                    PromptArgument(
                        name="person_name",
                        description="Name of the person you're meeting with",
                        required=True,
                    )
                ],
            ),
        ]

    @server.get_prompt()
    async def get_prompt(name: str, arguments: dict | None = None) -> list[PromptMessage]:
        if name == "auto-capture":
            return [
                PromptMessage(
                    role="system",
                    content=TextContent(type="text", text=AUTO_CAPTURE_SYSTEM),
                )
            ]
        elif name == "daily-standup":
            return [
                PromptMessage(
                    role="user",
                    content=TextContent(type="text", text=DAILY_STANDUP_PROMPT),
                )
            ]
        elif name == "prep-1on1":
            person = (arguments or {}).get("person_name", "the person")
            return [
                PromptMessage(
                    role="user",
                    content=TextContent(
                        type="text",
                        text=PREP_1ON1_PROMPT.format(person_name=person),
                    ),
                )
            ]
        else:
            raise ValueError(f"Unknown prompt: {name}")
