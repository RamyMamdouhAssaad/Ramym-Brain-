"""Outlook integration via Microsoft Graph API.

Setup:
1. Register an app in Azure AD (portal.azure.com → App Registrations)
2. Add delegated permissions: Mail.Read, Mail.Send
3. Set MICROSOFT_CLIENT_ID and MICROSOFT_TENANT_ID in .env
4. On first use, authenticate via device code flow

Docs: https://learn.microsoft.com/en-us/graph/api/resources/mail-api-overview
"""

import httpx

from src.config import MICROSOFT_CLIENT_ID, MICROSOFT_TENANT_ID

# Token cache (in-memory, refreshed on expiry)
_access_token: str | None = None

GRAPH_BASE_URL = "https://graph.microsoft.com/v1.0"


async def authenticate() -> str:
    """
    Authenticate via device code flow.
    Returns access token. Caches for session.

    TODO: Implement device code flow with MSAL.
    """
    if not MICROSOFT_CLIENT_ID:
        raise RuntimeError(
            "MICROSOFT_CLIENT_ID not set. Register an Azure AD app and update .env"
        )
    # Placeholder - will implement with msal.PublicClientApplication
    raise NotImplementedError("Run `rbrain auth microsoft` to authenticate first")


async def search_emails(
    query: str, top: int = 10, folder: str = "inbox"
) -> list[dict]:
    """
    Search emails via Microsoft Graph.

    Args:
        query: Search query (supports KQL)
        top: Max results
        folder: Mail folder to search
    """
    # TODO: Implement after auth flow
    raise NotImplementedError("Email integration not yet configured. Set up Microsoft auth first.")


async def get_email(message_id: str) -> dict:
    """Get a specific email by ID."""
    raise NotImplementedError("Email integration not yet configured.")


async def send_email(to: str, subject: str, body: str) -> dict:
    """Send an email via Microsoft Graph."""
    raise NotImplementedError("Email integration not yet configured.")


async def get_unread_count() -> int:
    """Get count of unread emails."""
    raise NotImplementedError("Email integration not yet configured.")
