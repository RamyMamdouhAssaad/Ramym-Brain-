"""Hybrid search - semantic (pgvector) + keyword (full-text) with score fusion."""

from src.db import get_pool
from src.memory.embeddings import embed_text


async def search_memories(query: str, limit: int = 10, tags: list[str] | None = None) -> list[dict]:
    """
    Hybrid search across memories.

    Combines:
    1. Vector similarity (pgvector cosine distance)
    2. Full-text search (tsvector)
    3. Reciprocal Rank Fusion for final scoring
    """
    pool = await get_pool()
    embedding = embed_text(query)

    async with pool.acquire() as conn:
        # Semantic search
        vector_results = await conn.fetch(
            """
            SELECT id, content, tags, source, category, created_at,
                   1 - (embedding <=> $1) AS similarity
            FROM memories
            WHERE ($2::text[] IS NULL OR tags && $2)
            ORDER BY embedding <=> $1
            LIMIT $3
            """,
            str(embedding),
            tags,
            limit * 2,
        )

        # Full-text search
        fts_results = await conn.fetch(
            """
            SELECT id, content, tags, source, category, created_at,
                   ts_rank(to_tsvector('english', content), plainto_tsquery('english', $1)) AS rank
            FROM memories
            WHERE to_tsvector('english', content) @@ plainto_tsquery('english', $1)
              AND ($2::text[] IS NULL OR tags && $2)
            ORDER BY rank DESC
            LIMIT $3
            """,
            query,
            tags,
            limit * 2,
        )

    # Reciprocal Rank Fusion
    scored: dict[str, dict] = {}
    k = 60  # RRF constant

    for rank, row in enumerate(vector_results):
        row_id = str(row["id"])
        if row_id not in scored:
            scored[row_id] = _row_to_dict(row)
            scored[row_id]["score"] = 0.0
        scored[row_id]["score"] += 1.0 / (k + rank + 1)

    for rank, row in enumerate(fts_results):
        row_id = str(row["id"])
        if row_id not in scored:
            scored[row_id] = _row_to_dict(row)
            scored[row_id]["score"] = 0.0
        scored[row_id]["score"] += 1.0 / (k + rank + 1)

    # Sort by combined score
    results = sorted(scored.values(), key=lambda x: x["score"], reverse=True)
    return results[:limit]


async def search_decisions(query: str, limit: int = 5) -> list[dict]:
    """Search architecture/technical decisions."""
    pool = await get_pool()
    embedding = embed_text(query)

    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT id, what, why, context, revisit_date, created_at,
                   1 - (embedding <=> $1) AS similarity
            FROM decisions
            ORDER BY embedding <=> $1
            LIMIT $2
            """,
            str(embedding),
            limit,
        )

    return [
        {
            "id": str(row["id"]),
            "what": row["what"],
            "why": row["why"],
            "context": row["context"],
            "revisit_date": row["revisit_date"],
            "created_at": row["created_at"].isoformat() if row["created_at"] else None,
            "similarity": float(row["similarity"]),
        }
        for row in rows
    ]


async def search_errors(query: str, limit: int = 5) -> list[dict]:
    """Search the error journal for past fixes."""
    pool = await get_pool()
    embedding = embed_text(query)

    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT id, error, fix, tags, occurrences, last_seen, created_at,
                   1 - (embedding <=> $1) AS similarity
            FROM error_journal
            ORDER BY embedding <=> $1
            LIMIT $2
            """,
            str(embedding),
            limit,
        )

    return [
        {
            "id": str(row["id"]),
            "error": row["error"],
            "fix": row["fix"],
            "tags": row["tags"],
            "occurrences": row["occurrences"],
            "last_seen": row["last_seen"].isoformat() if row["last_seen"] else None,
            "similarity": float(row["similarity"]),
        }
        for row in rows
    ]


async def search_snippets(query: str, limit: int = 5) -> list[dict]:
    """Search saved code snippets."""
    pool = await get_pool()
    embedding = embed_text(query)

    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT id, name, code, language, description, created_at,
                   1 - (embedding <=> $1) AS similarity
            FROM snippets
            ORDER BY embedding <=> $1
            LIMIT $2
            """,
            str(embedding),
            limit,
        )

    return [
        {
            "id": str(row["id"]),
            "name": row["name"],
            "code": row["code"],
            "language": row["language"],
            "description": row["description"],
            "similarity": float(row["similarity"]),
        }
        for row in rows
    ]


async def search_person(name: str) -> dict | None:
    """Get all context about a person."""
    pool = await get_pool()

    async with pool.acquire() as conn:
        person = await conn.fetchrow(
            "SELECT id, name, created_at FROM people WHERE LOWER(name) = LOWER($1)", name
        )
        if not person:
            return None

        notes = await conn.fetch(
            """
            SELECT note, category, created_at FROM person_notes
            WHERE person_id = $1 ORDER BY created_at DESC LIMIT 20
            """,
            person["id"],
        )

        meetings = await conn.fetch(
            """
            SELECT notes, action_items, created_at FROM one_on_ones
            WHERE person_id = $1 ORDER BY created_at DESC LIMIT 5
            """,
            person["id"],
        )

        delegations = await conn.fetch(
            """
            SELECT task, due, priority, status, created_at FROM delegations
            WHERE LOWER(assigned_to) = LOWER($1) ORDER BY created_at DESC LIMIT 10
            """,
            name,
        )

    return {
        "name": person["name"],
        "notes": [{"note": n["note"], "category": n["category"], "date": n["created_at"].isoformat()} for n in notes],
        "recent_1on1s": [
            {"notes": m["notes"], "action_items": m["action_items"], "date": m["created_at"].isoformat()}
            for m in meetings
        ],
        "delegations": [
            {"task": d["task"], "due": d["due"], "priority": d["priority"], "status": d["status"]}
            for d in delegations
        ],
    }


async def get_delegations(person: str | None = None, status: str = "pending") -> list[dict]:
    """Get delegation status."""
    pool = await get_pool()

    async with pool.acquire() as conn:
        if person:
            rows = await conn.fetch(
                """
                SELECT id, task, assigned_to, due, priority, status, created_at
                FROM delegations
                WHERE LOWER(assigned_to) = LOWER($1) AND status = $2
                ORDER BY created_at DESC
                """,
                person,
                status,
            )
        else:
            rows = await conn.fetch(
                """
                SELECT id, task, assigned_to, due, priority, status, created_at
                FROM delegations WHERE status = $1
                ORDER BY created_at DESC
                """,
                status,
            )

    return [
        {
            "id": str(row["id"]),
            "task": row["task"],
            "assigned_to": row["assigned_to"],
            "due": row["due"],
            "priority": row["priority"],
            "status": row["status"],
            "created_at": row["created_at"].isoformat(),
        }
        for row in rows
    ]


async def get_daily_summary() -> dict:
    """Get today's activity summary."""
    pool = await get_pool()

    async with pool.acquire() as conn:
        today_memories = await conn.fetch(
            """
            SELECT content, tags, source, category, created_at
            FROM memories
            WHERE created_at >= CURRENT_DATE
            ORDER BY created_at DESC
            """
        )

        today_decisions = await conn.fetch(
            """
            SELECT what, why FROM decisions
            WHERE created_at >= CURRENT_DATE
            """
        )

        pending_delegations = await conn.fetch(
            """
            SELECT task, assigned_to, due, priority FROM delegations
            WHERE status = 'pending'
            ORDER BY due ASC NULLS LAST
            """
        )

    return {
        "memories_today": len(today_memories),
        "activities": [
            {"content": m["content"], "source": m["source"], "time": m["created_at"].isoformat()}
            for m in today_memories
        ],
        "decisions_today": [{"what": d["what"], "why": d["why"]} for d in today_decisions],
        "pending_delegations": [
            {"task": d["task"], "assigned_to": d["assigned_to"], "due": d["due"]}
            for d in pending_delegations
        ],
    }


def _row_to_dict(row) -> dict:
    """Convert a database row to a dict."""
    return {
        "id": str(row["id"]),
        "content": row["content"],
        "tags": row["tags"],
        "source": row["source"],
        "category": row["category"],
        "created_at": row["created_at"].isoformat() if row["created_at"] else None,
    }
