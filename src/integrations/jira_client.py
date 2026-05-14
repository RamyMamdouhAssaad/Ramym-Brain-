"""Jira integration via REST API v3.

Setup:
1. Go to https://id.atlassian.com/manage-profile/security/api-tokens
2. Create an API token
3. Set JIRA_URL, JIRA_EMAIL, JIRA_API_TOKEN in .env

Docs: https://developer.atlassian.com/cloud/jira/platform/rest/v3/
"""

import base64

import httpx

from src.config import JIRA_URL, JIRA_EMAIL, JIRA_API_TOKEN


def _get_auth_header() -> dict[str, str]:
    """Build Basic auth header for Jira API."""
    if not all([JIRA_URL, JIRA_EMAIL, JIRA_API_TOKEN]):
        raise RuntimeError(
            "Jira not configured. Set JIRA_URL, JIRA_EMAIL, JIRA_API_TOKEN in .env"
        )
    credentials = base64.b64encode(f"{JIRA_EMAIL}:{JIRA_API_TOKEN}".encode()).decode()
    return {
        "Authorization": f"Basic {credentials}",
        "Content-Type": "application/json",
    }


async def search_tickets(jql: str, max_results: int = 20) -> list[dict]:
    """
    Search Jira tickets using JQL.

    Args:
        jql: JQL query string (e.g., "project = PROJ AND status = 'In Progress'")
        max_results: Maximum results to return
    """
    headers = _get_auth_header()
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{JIRA_URL}/rest/api/3/search",
            headers=headers,
            params={"jql": jql, "maxResults": max_results},
            timeout=30,
        )
        response.raise_for_status()
        data = response.json()

    return [
        {
            "key": issue["key"],
            "summary": issue["fields"]["summary"],
            "status": issue["fields"]["status"]["name"],
            "assignee": (issue["fields"].get("assignee") or {}).get("displayName", "Unassigned"),
            "priority": (issue["fields"].get("priority") or {}).get("name", "None"),
            "updated": issue["fields"].get("updated", ""),
        }
        for issue in data.get("issues", [])
    ]


async def get_ticket(key: str) -> dict:
    """Get full details of a Jira ticket."""
    headers = _get_auth_header()
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{JIRA_URL}/rest/api/3/issue/{key}",
            headers=headers,
            timeout=30,
        )
        response.raise_for_status()
        data = response.json()

    fields = data["fields"]
    return {
        "key": data["key"],
        "summary": fields["summary"],
        "description": fields.get("description", ""),
        "status": fields["status"]["name"],
        "assignee": (fields.get("assignee") or {}).get("displayName", "Unassigned"),
        "reporter": (fields.get("reporter") or {}).get("displayName", "Unknown"),
        "priority": (fields.get("priority") or {}).get("name", "None"),
        "created": fields.get("created", ""),
        "updated": fields.get("updated", ""),
        "labels": fields.get("labels", []),
    }


async def my_tickets(status: str | None = None) -> list[dict]:
    """Get tickets assigned to you."""
    jql = "assignee = currentUser()"
    if status:
        jql += f" AND status = '{status}'"
    jql += " ORDER BY updated DESC"
    return await search_tickets(jql)


async def create_ticket(
    project: str, summary: str, description: str = "", issue_type: str = "Task"
) -> dict:
    """Create a new Jira ticket."""
    headers = _get_auth_header()
    payload = {
        "fields": {
            "project": {"key": project},
            "summary": summary,
            "description": {
                "type": "doc",
                "version": 1,
                "content": [
                    {
                        "type": "paragraph",
                        "content": [{"type": "text", "text": description}],
                    }
                ],
            }
            if description
            else None,
            "issuetype": {"name": issue_type},
        }
    }
    # Remove None values
    payload["fields"] = {k: v for k, v in payload["fields"].items() if v is not None}

    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{JIRA_URL}/rest/api/3/issue",
            headers=headers,
            json=payload,
            timeout=30,
        )
        response.raise_for_status()
        data = response.json()

    return {"key": data["key"], "url": f"{JIRA_URL}/browse/{data['key']}"}


async def add_comment(key: str, comment: str) -> dict:
    """Add a comment to a Jira ticket."""
    headers = _get_auth_header()
    payload = {
        "body": {
            "type": "doc",
            "version": 1,
            "content": [
                {
                    "type": "paragraph",
                    "content": [{"type": "text", "text": comment}],
                }
            ],
        }
    }

    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{JIRA_URL}/rest/api/3/issue/{key}/comment",
            headers=headers,
            json=payload,
            timeout=30,
        )
        response.raise_for_status()

    return {"status": "comment_added", "ticket": key}
