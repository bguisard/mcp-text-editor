"""MCP Text Editor Server implementation."""

import logging
import sys
import traceback
from collections.abc import Sequence
from typing import Any

from mcp.server import Server
from mcp.types import TextContent, Tool

from .handlers import (
    AppendTextFileContentsHandler,
    CreateTextFileHandler,
    DeleteTextFileContentsHandler,
    GetTextFileContentsHandler,
    InsertTextFileContentsHandler,
    PatchTextFileContentsHandler,
)
from .text_editor import TextEditor
from .version import __version__

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("mcp-text-editor")


class TextEditorServer:
    """Server class for the MCP Text Editor."""

    def __init__(self, allowed_paths: list[str] | None = None):
        """Initialize the server with optional path restrictions.

        Args:
            allowed_paths: List of directory paths that are allowed to be accessed.
                        If None or empty list, all paths are allowed.
        """
        self.app = Server("mcp-text-editor")
        self.editor = TextEditor(allowed_paths=allowed_paths)

        if allowed_paths:
            logger.info(f"Editor initialized with path restrictions: {allowed_paths}")
        else:
            logger.info(
                "Editor initialized without path restrictions - all paths accessible"
            )

        self.handlers = {
            "get_text_file_contents": GetTextFileContentsHandler(self.editor),
            "create_text_file": CreateTextFileHandler(self.editor),
            "append_text_file_contents": AppendTextFileContentsHandler(self.editor),
            "delete_text_file_contents": DeleteTextFileContentsHandler(self.editor),
            "insert_text_file_contents": InsertTextFileContentsHandler(self.editor),
            "patch_text_file_contents": PatchTextFileContentsHandler(self.editor),
        }

        self._register_handlers()

    def _register_handlers(self):
        """Post-initialization setup."""
        self.app.list_tools()(self.list_tools)
        self.app.call_tool()(self.call_tool)

    async def call_tool(self, name: str, arguments: Any) -> Sequence[TextContent]:
        """Handle tool calls."""
        logger.info(f"Calling tool: {name}")

        try:
            handler = self.handlers[name]
            return await handler.run_tool(arguments)
        except ValueError:
            logger.error(traceback.format_exc())
            raise
        except Exception as e:
            logger.error(traceback.format_exc())
            raise RuntimeError(f"Error executing command: {str(e)}") from e

    async def list_tools(self) -> list[Tool]:
        """List available tools."""
        tool_list = []
        for handler in self.handlers.values():
            tool_list.append(handler.get_tool_description())
        return tool_list

    async def run(self) -> None:
        """Run the server."""
        try:
            from mcp.server.stdio import stdio_server

            async with stdio_server() as (read_stream, write_stream):
                await self.app.run(
                    read_stream,
                    write_stream,
                    self.app.create_initialization_options(),
                )
        except Exception as e:
            logger.error(f"Server error: {str(e)}")
            raise


# Module-level server instance
_server_instance: TextEditorServer | None = None


def get_server() -> TextEditorServer:
    """Get the global server instance, initializing it if necessary."""
    global _server_instance
    if _server_instance is None:
        # Parse command line arguments as allowed paths
        allowed_paths = sys.argv[1:] if len(sys.argv) > 1 else None
        _server_instance = TextEditorServer(allowed_paths=allowed_paths)
    return _server_instance


async def main() -> None:
    """Main entry point for the MCP text editor server."""
    logger.info(f"Starting MCP text editor server v{__version__}")

    server = get_server()
    await server.run()
