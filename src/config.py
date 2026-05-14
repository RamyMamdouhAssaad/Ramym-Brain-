"""Configuration from environment variables."""

import os
from pathlib import Path

from dotenv import load_dotenv

# Load .env from project root
_project_root = Path(__file__).parent.parent
load_dotenv(_project_root / ".env")

# ─── Supabase ───────────────────────────────────────────────
SUPABASE_DB_URL: str = os.getenv("SUPABASE_DB_URL", "")
SUPABASE_URL: str = os.getenv("SUPABASE_URL", "")
SUPABASE_KEY: str = os.getenv("SUPABASE_KEY", "")

# ─── Embeddings ─────────────────────────────────────────────
EMBEDDING_MODEL: str = os.getenv("EMBEDDING_MODEL", "all-MiniLM-L6-v2")
EMBEDDING_DIMENSION: int = 384  # all-MiniLM-L6-v2 output dim

# ─── Microsoft Graph (Outlook + Teams) ──────────────────────
MICROSOFT_CLIENT_ID: str = os.getenv("MICROSOFT_CLIENT_ID", "")
MICROSOFT_TENANT_ID: str = os.getenv("MICROSOFT_TENANT_ID", "")

# ─── Jira ────────────────────────────────────────────────────
JIRA_URL: str = os.getenv("JIRA_URL", "")
JIRA_EMAIL: str = os.getenv("JIRA_EMAIL", "")
JIRA_API_TOKEN: str = os.getenv("JIRA_API_TOKEN", "")

# ─── Optional LLM ───────────────────────────────────────────
OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
