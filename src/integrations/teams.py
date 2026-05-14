"""Microsoft Teams integration via Microsoft Graph API.

Uses the same Azure AD app as Outlook (shared OAuth token).
Permissions needed: ChannelMessage.Read.All, Chat.Read

Docs: https://learn.microsoft.com/en-us/graph/api/resources/teams-api-overview
"""

import httpx

from src.config import MICROSOFT_CLIENT_ID

GRAPH_BASE_URL = "https://graph.microsoft.com/v1.0"


async def search_messages(query: str, channel: str | None = None, top: int = 10) -> list[dict]:
    """
    Search Teams messages.

    Args:
        query: Search text
        channel: Filter to specific channel (optional)
        top: Max results
    """
    raise NotImplementedError("Teams integration not yet configured. Set up Microsoft auth first.")


async def get_recent_messages(channel: str, count: int = 20) -> list[dict]:
    """Get recent messages from a channel."""
    raise NotImplementedError("Teams integration not yet configured.")


async def list_channels() -> list[dict]:
    """List Teams channels you're a member of."""
    raise NotImplementedError("Teams integration not yet configured.")


async def list_chats() -> list[dict]:
    """List recent 1:1 and group chats."""
    raise NotImplementedError("Teams integration not yet configured.")
