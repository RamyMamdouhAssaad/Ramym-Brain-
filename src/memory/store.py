"""Memory store - CRUD operations against Supabase Postgres."""

from datetime import datetime, timezone
from uuid import UUID, uuid4

from src.db import get_pool
from src.memory.embeddings import embed_text


async def remember(
    content: str,
    tags: list[str] | None = None,
    source: str = "manual",
    category: str = "general",
) -> dict:
    """Save a memory with embedding for semantic search."""
    pool = await get_pool()
    embedding = embed_text(content)
    memory_id = uuid4()
    now = datetime.now(timezone.utc)

    async with pool.acquire() as conn:
        await conn.execute(
            """
            INSERT INTO memories (id, content, tags, source, category, embedding, created_at)
            VALUES ($1, $2, $3, $4, $5, $6, $7)
            """,
            memory_id,
            content,
            tags or [],
            source,
            category,
            str(embedding),
            now,
        )

    return {
        "id": str(memory_id),
        "content": content,
        "tags": tags or [],
        "source": source,
        "category": category,
        "created_at": now.isoformat(),
    }


async def log_decision(
    what: str,
    why: str,
    context: str = "",
    revisit_date: str | None = None,
) -> dict:
    """Log an architecture/technical decision."""
    pool = await get_pool()
    decision_id = uuid4()
    now = datetime.now(timezone.utc)
    embedding = embed_text(f"{what} {why} {context}")

    async with pool.acquire() as conn:
        await conn.execute(
            """
            INSERT INTO decisions (id, what, why, context, revisit_date, embedding, created_at)
            VALUES ($1, $2, $3, $4, $5, $6, $7)
            """,
            decision_id,
            what,
            why,
            context,
            revisit_date,
            str(embedding),
            now,
        )

    return {
        "id": str(decision_id),
        "what": what,
        "why": why,
        "context": context,
        "revisit_date": revisit_date,
        "created_at": now.isoformat(),
    }


async def log_error(error: str, fix: str, tags: list[str] | None = None) -> dict:
    """Log an error and its fix to the error journal."""
    pool = await get_pool()
    error_id = uuid4()
    now = datetime.now(timezone.utc)
    embedding = embed_text(f"{error} {fix}")

    async with pool.acquire() as conn:
        # Check if similar error exists (update occurrences)
        existing = await conn.fetchrow(
            """
            SELECT id, occurrences FROM error_journal
            WHERE 1 - (embedding <=> $1) > 0.85
            ORDER BY 1 - (embedding <=> $1) DESC
            LIMIT 1
            """,
            str(embedding),
        )

        if existing:
            await conn.execute(
                """
                UPDATE error_journal
                SET occurrences = occurrences + 1, last_seen = $2, fix = $3
                WHERE id = $1
                """,
                existing["id"],
                now,
                fix,
            )
            return {
                "id": str(existing["id"]),
                "status": "updated_existing",
                "occurrences": existing["occurrences"] + 1,
            }

        await conn.execute(
            """
            INSERT INTO error_journal (id, error, fix, tags, embedding, occurrences, last_seen, created_at)
            VALUES ($1, $2, $3, $4, $5, 1, $6, $6)
            """,
            error_id,
            error,
            fix,
            tags or [],
            str(embedding),
            now,
        )

    return {"id": str(error_id), "status": "created", "occurrences": 1}


async def save_snippet(
    name: str, code: str, language: str = "python", description: str = ""
) -> dict:
    """Save a reusable code snippet."""
    pool = await get_pool()
    snippet_id = uuid4()
    now = datetime.now(timezone.utc)
    embedding = embed_text(f"{name} {description} {language}")

    async with pool.acquire() as conn:
        await conn.execute(
            """
            INSERT INTO snippets (id, name, code, language, description, embedding, created_at)
            VALUES ($1, $2, $3, $4, $5, $6, $7)
            """,
            snippet_id,
            name,
            code,
            language,
            description,
            str(embedding),
            now,
        )

    return {"id": str(snippet_id), "name": name, "language": language}


async def log_person_note(
    name: str, note: str, category: str = "general"
) -> dict:
    """Add a note about a person (team member, colleague, stakeholder)."""
    pool = await get_pool()
    now = datetime.now(timezone.utc)
    embedding = embed_text(f"{name} {note}")

    # Upsert person
    async with pool.acquire() as conn:
        person = await conn.fetchrow(
            "SELECT id FROM people WHERE LOWER(name) = LOWER($1)", name
        )

        if not person:
            person_id = uuid4()
            await conn.execute(
                "INSERT INTO people (id, name, created_at) VALUES ($1, $2, $3)",
                person_id,
                name,
                now,
            )
        else:
            person_id = person["id"]

        # Add note
        note_id = uuid4()
        await conn.execute(
            """
            INSERT INTO person_notes (id, person_id, note, category, embedding, created_at)
            VALUES ($1, $2, $3, $4, $5, $6)
            """,
            note_id,
            person_id,
            note,
            category,
            str(embedding),
            now,
        )

    return {"person": name, "note_id": str(note_id), "category": category}


async def log_one_on_one(
    person: str, notes: str, action_items: list[str] | None = None
) -> dict:
    """Log a 1:1 meeting with someone."""
    pool = await get_pool()
    now = datetime.now(timezone.utc)
    meeting_id = uuid4()
    embedding = embed_text(f"1:1 with {person}: {notes}")

    async with pool.acquire() as conn:
        # Get or create person
        person_row = await conn.fetchrow(
            "SELECT id FROM people WHERE LOWER(name) = LOWER($1)", person
        )
        if not person_row:
            person_id = uuid4()
            await conn.execute(
                "INSERT INTO people (id, name, created_at) VALUES ($1, $2, $3)",
                person_id,
                person,
                now,
            )
        else:
            person_id = person_row["id"]

        await conn.execute(
            """
            INSERT INTO one_on_ones (id, person_id, notes, action_items, embedding, created_at)
            VALUES ($1, $2, $3, $4, $5, $6)
            """,
            meeting_id,
            person_id,
            notes,
            action_items or [],
            str(embedding),
            now,
        )

    return {
        "id": str(meeting_id),
        "person": person,
        "action_items": action_items or [],
    }


async def delegate_task(
    task: str, assigned_to: str, due: str | None = None, priority: str = "medium"
) -> dict:
    """Track a delegated task."""
    pool = await get_pool()
    delegation_id = uuid4()
    now = datetime.now(timezone.utc)

    async with pool.acquire() as conn:
        await conn.execute(
            """
            INSERT INTO delegations (id, task, assigned_to, due, priority, status, created_at)
            VALUES ($1, $2, $3, $4, $5, 'pending', $6)
            """,
            delegation_id,
            task,
            assigned_to,
            due,
            priority,
            now,
        )

    return {
        "id": str(delegation_id),
        "task": task,
        "assigned_to": assigned_to,
        "due": due,
        "priority": priority,
        "status": "pending",
    }
