"""Resolver - routes user intent to the correct tool without LLM calls."""

import re
from dataclasses import dataclass


@dataclass
class ResolvedIntent:
    """Result of resolving user input to a tool."""

    module: str  # Tool group: memory, developer, leader, email, teams, jira, workflow
    action: str  # Specific action within the group
    confidence: float  # 0.0 - 1.0, below 0.5 falls back to LLM


# Pattern → (module, action) mapping
# Order matters: more specific patterns first
_ROUTES: list[tuple[str, str, str]] = [
    # ─── Memory ─────────────────────────────────────────
    (r"remember|save this|note this|store this", "memory", "remember"),
    (r"recall|what did i|find.*(?:note|memory|decision)|when did i", "memory", "recall"),
    (r"daily.?summary|what.*today|end.?of.?day", "memory", "daily_summary"),
    (r"weekly.?summary|this week|week.?report", "memory", "weekly_summary"),
    (r"standup|stand.?up", "memory", "standup"),

    # ─── Developer ──────────────────────────────────────
    (r"log.?decision|decided|decision.*(?:log|save)", "developer", "log_decision"),
    (r"log.?error|error.*(?:fix|log)|bug.*fix", "developer", "log_error"),
    (r"save.?snippet|snippet.*save", "developer", "save_snippet"),
    (r"find.?snippet|snippet.*(?:find|search)|pattern.*(?:find|search)", "developer", "search_snippets"),
    (r"pr.?status|pull.?request|my.?prs", "developer", "pr_status"),
    (r"tech.?debt|technical.?debt", "developer", "tech_debt"),
    (r"context.?switch|switch.*(?:to|project)|load.*context", "developer", "context_switch"),

    # ─── Team Leader ────────────────────────────────────
    (r"1.?on.?1|one.?on.?one|1:1", "leader", "one_on_one"),
    (r"prep.*(?:1.?on.?1|meeting|1:1)", "leader", "prep_meeting"),
    (r"delegate|assign.*(?:to|task)", "leader", "delegate"),
    (r"delegation.*(?:status|check)|who.*assigned", "leader", "delegation_status"),
    (r"person.*(?:note|context)|about.*(?:person|team.?member)", "leader", "person_note"),
    (r"team.*block|who.*(?:stuck|blocked)", "leader", "team_blockers"),
    (r"feedback.*(?:for|about)|performance.*(?:note|log)", "leader", "feedback"),
    (r"broadcast|did i.*tell|communicate", "leader", "broadcast_check"),

    # ─── Integrations ──────────────────────────────────
    (r"email|inbox|outlook|mail", "email", "search"),
    (r"teams.*(?:message|search|channel)|channel", "teams", "search"),
    (r"jira|ticket|sprint|issue|backlog", "jira", "search"),
    (r"my.?tickets|assigned.*(?:to me|tickets)", "jira", "my_tickets"),
    (r"create.?ticket|new.?ticket|open.?issue", "jira", "create_ticket"),
]


def resolve(user_input: str) -> ResolvedIntent:
    """
    Route user input to the correct module and action.

    Returns the resolved intent. If no pattern matches,
    returns a fallback to LLM with low confidence.
    """
    lower = user_input.lower().strip()

    for pattern, module, action in _ROUTES:
        if re.search(pattern, lower):
            return ResolvedIntent(module=module, action=action, confidence=0.9)

    # No match — fall back to LLM (or generic search)
    return ResolvedIntent(module="memory", action="recall", confidence=0.3)
