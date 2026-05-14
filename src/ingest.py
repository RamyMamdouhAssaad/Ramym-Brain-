"""Ingest queued auto-capture entries into the brain database."""

import json
import logging
import os
from pathlib import Path

from src.memory.store import log_decision, remember

logger = logging.getLogger("rbrain.ingest")

QUEUE_DIR = Path.home() / ".ramym-brain" / "queue"


async def ingest_queue():
    """Process all queued entries and store in database."""
    if not QUEUE_DIR.exists():
        return

    files = sorted(QUEUE_DIR.glob("*.json"))
    if not files:
        return

    logger.info(f"Ingesting {len(files)} queued entries...")

    for filepath in files:
        try:
            with open(filepath) as f:
                entry = json.load(f)

            entry_type = entry.get("type", "memory")

            if entry_type == "decision":
                await log_decision(
                    decision=entry["decision"],
                    context=entry.get("context", ""),
                    tags=entry.get("tags", []),
                )
            elif entry_type == "memory":
                await remember(
                    content=entry["content"],
                    tags=entry.get("tags", []),
                    source=entry.get("source", "auto"),
                )

            # Remove processed file
            filepath.unlink()
            logger.debug(f"Ingested: {filepath.name}")

        except Exception as e:
            logger.error(f"Failed to ingest {filepath.name}: {e}")

    logger.info("Queue ingestion complete.")
