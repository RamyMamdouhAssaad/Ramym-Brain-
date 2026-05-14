"""MCP Server entry point for Ramy's Brain."""

import asyncio
import logging

from mcp.server import Server
from mcp.server.stdio import stdio_server

from src.db import close_pool, get_pool
from src.ingest import ingest_queue
from src.prompts import register_prompts
from src.tools.memory_tools import register_memory_tools
from src.tools.developer_tools import register_developer_tools
from src.tools.leader_tools import register_leader_tools

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("rbrain")

server = Server("ramym-brain")

# Register all tool groups
register_memory_tools(server)
register_developer_tools(server)
register_leader_tools(server)
register_prompts(server)


def main():
    """Entry point for the MCP server."""
    logger.info("Starting Ramy's Brain MCP server...")
    asyncio.run(_run())


async def _run():
    try:
        # Ingest any queued auto-captures (from git hooks, etc.)
        await get_pool()  # ensure DB connection
        await ingest_queue()

        async with stdio_server() as (read_stream, write_stream):
            await server.run(
                read_stream,
                write_stream,
                server.create_initialization_options(),
            )
    finally:
        await close_pool()


if __name__ == "__main__":
    main()
