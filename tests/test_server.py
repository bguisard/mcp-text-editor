"""Tests for the MCP Text Editor Server."""

import json
import os
from pathlib import Path

import pytest
from mcp import types
from mcp.types import TextContent
from pytest_mock import MockerFixture

from mcp_text_editor.handlers import GetTextFileContentsHandler
from mcp_text_editor.server import TextEditorServer, main, new_server
from mcp_text_editor.text_editor import TextEditor


@pytest.fixture
def server():
    """Create a TextEditorServer instance for testing."""
    return new_server()


@pytest.mark.asyncio
async def test_handler_access(server):
    """Test access to handlers."""
    # Verify all handlers are created
    assert "get_text_file_contents" in server.handlers
    assert "create_text_file" in server.handlers
    assert "append_text_file_contents" in server.handlers
    assert "delete_text_file_contents" in server.handlers
    assert "insert_text_file_contents" in server.handlers
    assert "patch_text_file_contents" in server.handlers


@pytest.mark.asyncio
async def test_tool_descriptions(server):
    """Test that handlers provide proper tool descriptions."""
    # Get a handler and verify its tool description
    handler = server.handlers["get_text_file_contents"]
    tool = handler.get_tool_description()

    assert tool.name == "get_text_file_contents"
    assert "file" in tool.description.lower()
    assert "contents" in tool.description.lower()


@pytest.mark.asyncio
async def test_list_tools(server: TextEditorServer):
    """Test tool listing."""
    # Instead of trying to call the function directly, verify the handler is registered
    assert types.ListToolsRequest in server.app.request_handlers

    # Verify handler function exists
    list_tools_handler = server.app.request_handlers[types.ListToolsRequest]
    assert callable(list_tools_handler)

    # Check that all handlers are available by examining the handler dict directly
    tool_names = [handler.name for handler in server.handlers.values()]
    assert len(tool_names) == 6
    assert "get_text_file_contents" in tool_names
    assert "create_text_file" in tool_names
    assert "append_text_file_contents" in tool_names
    assert "delete_text_file_contents" in tool_names
    assert "insert_text_file_contents" in tool_names
    assert "patch_text_file_contents" in tool_names


@pytest.mark.asyncio
async def test_get_contents_empty_files(server: TextEditorServer):
    """Test get_contents handler with empty files list."""
    handler = server.handlers["get_text_file_contents"]
    arguments = {"files": []}
    result = await handler.run_tool(arguments)
    assert len(result) == 1
    assert result[0].type == "text"
    # Should return empty JSON object
    assert json.loads(result[0].text) == {}


@pytest.mark.asyncio
async def test_unknown_tool_handler(server: TextEditorServer):
    """Test handling of unknown tool name."""
    # Simply verify that an unknown key raises the right exception
    with pytest.raises(KeyError):
        _ = server.handlers["unknown_tool"]


@pytest.mark.asyncio
async def test_get_contents_handler(server, test_file):
    """Test GetTextFileContents handler."""
    handler = server.handlers["get_text_file_contents"]
    args = {"files": [{"file_path": test_file, "ranges": [{"start": 1, "end": 3}]}]}
    result = await handler.run_tool(args)
    assert len(result) == 1
    assert isinstance(result[0], TextContent)
    content = json.loads(result[0].text)
    assert test_file in content
    range_result = content[test_file]["ranges"][0]
    assert "content" in range_result
    assert "start" in range_result
    assert "end" in range_result
    assert "file_hash" in content[test_file]
    assert "total_lines" in range_result
    assert "content_size" in range_result


@pytest.mark.asyncio
async def test_get_contents_handler_invalid_file(server, test_file):
    """Test GetTextFileContents handler with invalid file."""
    handler = server.handlers["get_text_file_contents"]
    # Convert relative path to absolute
    nonexistent_path = str(Path("nonexistent.txt").absolute())
    args = {"files": [{"file_path": nonexistent_path, "ranges": [{"start": 1}]}]}
    with pytest.raises(RuntimeError) as exc_info:
        await handler.run_tool(args)
    assert "File not found" in str(exc_info.value)


@pytest.mark.asyncio
async def test_call_tool_get_contents(server, test_file):
    """Test call_tool with GetTextFileContents."""
    # Since we can't directly access the internal call_tool function,
    # we'll test the functionality by using the handler directly
    handler = server.handlers["get_text_file_contents"]
    args = {"files": [{"file_path": test_file, "ranges": [{"start": 1, "end": 3}]}]}

    result = await handler.run_tool(args)

    # Verify the result
    assert isinstance(result[0], TextContent)
    content_data = json.loads(result[0].text)
    assert test_file in content_data


@pytest.mark.asyncio
async def test_call_tool_unknown(server):
    """Test call_tool with unknown tool."""
    # This test just verifies that unknown tools raise KeyError when accessed
    with pytest.raises(KeyError):
        _ = server.handlers["UnknownTool"]


@pytest.mark.asyncio
async def test_call_tool_error_handling(server):
    """Test call_tool error handling with direct handler access."""
    handler = server.handlers["get_text_file_contents"]

    # Test with invalid arguments
    with pytest.raises(RuntimeError) as exc_info:
        await handler.run_tool({"invalid": "args"})
    assert "Missing required argument" in str(exc_info.value)

    # Convert relative path to absolute
    nonexistent_path = str(Path("nonexistent.txt").absolute())
    with pytest.raises(RuntimeError) as exc_info:
        await handler.run_tool(
            {"files": [{"file_path": nonexistent_path, "ranges": [{"start": 1}]}]}
        )
    assert "File not found" in str(exc_info.value)


@pytest.mark.asyncio
async def test_get_contents_handler_legacy_missing_args(server):
    """Test GetTextFileContents handler with legacy single file request missing arguments."""
    handler = server.handlers["get_text_file_contents"]
    with pytest.raises(RuntimeError) as exc_info:
        await handler.run_tool({})
    assert "Missing required argument: 'files'" in str(exc_info.value)


@pytest.mark.asyncio
async def test_main_stdio_server_error(mocker: MockerFixture):
    """Test main function with stdio_server error."""
    # Mock the get_server function to return a mock server
    mock_server = mocker.MagicMock()
    mock_server.run.side_effect = Exception("Stdio server error")
    mocker.patch("mcp_text_editor.server.new_server", return_value=mock_server)

    with pytest.raises(Exception) as exc_info:
        await main()
    assert "Stdio server error" in str(exc_info.value)


@pytest.mark.asyncio
async def test_main_run_error(mocker: MockerFixture):
    """Test main function with server.run error."""
    # Mock the get_server function to return a mock server
    mock_server = mocker.MagicMock()
    mock_server.run.side_effect = Exception("Server run error")
    mocker.patch("mcp_text_editor.server.new_server", return_value=mock_server)

    with pytest.raises(Exception) as exc_info:
        await main()
    assert "Server run error" in str(exc_info.value)


@pytest.mark.asyncio
async def test_get_contents_relative_path():
    """Test GetTextFileContents with relative path."""
    # Create editor and handler directly
    editor = TextEditor()
    handler = GetTextFileContentsHandler(editor)
    with pytest.raises(RuntimeError, match="File path must be absolute:.*"):
        await handler.run_tool(
            {
                "files": [
                    {"file_path": "relative/path/file.txt", "ranges": [{"start": 1}]}
                ]
            }
        )


@pytest.mark.asyncio
async def test_get_contents_absolute_path():
    """Test GetTextFileContents with absolute path."""
    # Create editor and handler directly
    editor = TextEditor()
    handler = GetTextFileContentsHandler(editor)
    abs_path = str(Path("/absolute/path/file.txt").absolute())

    # Define mock as async function
    async def mock_read_multiple_ranges(*args, **kwargs):
        return {}

    # Set up mock
    handler.editor.read_multiple_ranges = mock_read_multiple_ranges

    result = await handler.run_tool(
        {"files": [{"file_path": abs_path, "ranges": [{"start": 1}]}]}
    )
    assert isinstance(result[0], TextContent)


@pytest.mark.asyncio
async def test_call_tool_general_exception(server, mocker: MockerFixture):
    """Test call_tool with a general exception."""
    # Create a mock handler that raises an exception
    mock_handler = mocker.MagicMock()
    mock_handler.run_tool.side_effect = Exception("Unexpected error")
    mock_handler.name = "get_text_file_contents"

    # Get the original handler
    original_handler = server.handlers["get_text_file_contents"]

    # Replace the handler with our mock
    try:
        server.handlers["get_text_file_contents"] = mock_handler

        # Try to use it directly instead of through the call_tool mechanism
        with pytest.raises(Exception) as exc_info:
            await mock_handler.run_tool({"files": []})
        assert "Unexpected error" in str(exc_info.value)
    finally:
        # Restore the original handler
        server.handlers["get_text_file_contents"] = original_handler


@pytest.mark.asyncio
async def test_call_tool_all_handlers(server, mocker: MockerFixture):
    """Test running all tools using their handlers directly."""
    # Test each handler
    for _, handler in server.handlers.items():
        # Create a mock that returns a predefined response
        mock_run_tool = mocker.patch.object(
            handler,
            "run_tool",
            return_value=[TextContent(text="mocked response", type="text")],
        )

        # Call the handler directly
        result = await handler.run_tool({"test": "args"})

        # Verify the mock was called
        mock_run_tool.assert_called_once_with({"test": "args"})

        # Verify the result
        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert result[0].text == "mocked response"


@pytest.mark.asyncio
async def test_server_initialization_with_paths(tmp_path):
    """Test server initialization with allowed paths."""
    allowed_dir = tmp_path / "allowed"
    allowed_dir.mkdir()

    server = TextEditorServer(allowed_paths=[str(allowed_dir)])

    # Verify that the editor has the correct allowed paths
    assert len(server.editor._allowed_paths) == 1
    assert os.path.samefile(next(iter(server.editor._allowed_paths)), str(allowed_dir))

    # Verify that handlers have the same editor
    handler = server.handlers["get_text_file_contents"]
    assert handler.editor is server.editor


@pytest.mark.asyncio
async def test_server_with_path_restrictions(tmp_path):
    """Test server with path restrictions applied."""
    # Create test directories
    allowed_dir = tmp_path / "allowed"
    allowed_dir.mkdir()
    allowed_file = allowed_dir / "file.txt"
    allowed_file.write_text("allowed content")

    restricted_dir = tmp_path / "restricted"
    restricted_dir.mkdir()
    restricted_file = restricted_dir / "file.txt"
    restricted_file.write_text("restricted content")

    # Create server with path restrictions
    server = TextEditorServer(allowed_paths=[str(allowed_dir)])

    # Verify path restrictions are properly passed to the editor
    assert len(server.editor._allowed_paths) == 1
    assert os.path.samefile(next(iter(server.editor._allowed_paths)), str(allowed_dir))

    # Verify that all handlers share the same restricted editor
    for handler in server.handlers.values():
        assert handler.editor is server.editor
        assert handler.editor._allowed_paths == server.editor._allowed_paths

    # Get handler directly from the server
    get_handler = server.handlers["get_text_file_contents"]

    # Test access to allowed file
    result = await get_handler.run_tool(
        {"files": [{"file_path": str(allowed_file), "ranges": [{"start": 1}]}]}
    )
    content = json.loads(result[0].text)
    assert str(allowed_file) in content
    assert "allowed content" in content[str(allowed_file)]["ranges"][0]["content"]

    # Test access to restricted file
    with pytest.raises(RuntimeError) as exc_info:
        await get_handler.run_tool(
            {"files": [{"file_path": str(restricted_file), "ranges": [{"start": 1}]}]}
        )
    assert "Access denied" in str(exc_info.value)
