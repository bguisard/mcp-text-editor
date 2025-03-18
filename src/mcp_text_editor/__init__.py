"""MCP Text Editor Server package."""

import asyncio

from .server import main


def run() -> None:
    """Run the MCP Text Editor Server.

    Any command-line arguments are treated as allowed path restrictions.
    If no arguments are provided, the server runs in unrestricted mode.
    """
    asyncio.run(main())
