"""Tests for path restriction functionality."""

import os

import pytest

from mcp_text_editor.text_editor import TextEditor


@pytest.fixture
def unrestricted_editor():
    """Create TextEditor without path restrictions."""
    return TextEditor()


@pytest.fixture
def restricted_editor(tmp_path):
    """Create TextEditor with path restrictions."""
    # Create a subdirectory for testing
    allowed_dir = tmp_path / "allowed"
    allowed_dir.mkdir()
    return TextEditor(allowed_paths=[str(allowed_dir)])


@pytest.mark.asyncio
async def test_unrestricted_access(unrestricted_editor, tmp_path):
    """Test that unrestricted editor allows access to any path."""
    # Create test files in different directories
    root_file = tmp_path / "root.txt"
    root_file.write_text("Root file content\n")

    subdir = tmp_path / "subdir"
    subdir.mkdir()
    subdir_file = subdir / "sub.txt"
    subdir_file.write_text("Subdir file content\n")

    # Verify access to root file is allowed
    content, _, _, _, _, _ = await unrestricted_editor.read_file_contents(
        str(root_file)
    )
    assert content == "Root file content\n"

    # Verify access to subdir file is allowed
    content, _, _, _, _, _ = await unrestricted_editor.read_file_contents(
        str(subdir_file)
    )
    assert content == "Subdir file content\n"


@pytest.mark.asyncio
async def test_restricted_access_allowed(restricted_editor, tmp_path):
    """Test that restricted editor allows access to files in allowed path."""
    # Create test file in allowed directory
    allowed_dir = tmp_path / "allowed"
    allowed_file = allowed_dir / "allowed.txt"
    allowed_file.write_text("Allowed file content\n")

    # Create nested directory inside allowed directory
    nested_dir = allowed_dir / "nested"
    nested_dir.mkdir()
    nested_file = nested_dir / "nested.txt"
    nested_file.write_text("Nested file content\n")

    # Verify access to allowed file is permitted
    content, _, _, _, _, _ = await restricted_editor.read_file_contents(
        str(allowed_file)
    )
    assert content == "Allowed file content\n"

    # Verify access to nested file is permitted
    content, _, _, _, _, _ = await restricted_editor.read_file_contents(
        str(nested_file)
    )
    assert content == "Nested file content\n"


@pytest.mark.asyncio
async def test_restricted_access_denied(restricted_editor, tmp_path):
    """Test that restricted editor denies access to files outside allowed path."""
    # Create test file outside allowed directory
    restricted_file = tmp_path / "restricted.txt"
    restricted_file.write_text("Restricted file content\n")

    # Create file in sibling directory
    sibling_dir = tmp_path / "sibling"
    sibling_dir.mkdir()
    sibling_file = sibling_dir / "sibling.txt"
    sibling_file.write_text("Sibling file content\n")

    # Verify access to restricted file is denied
    with pytest.raises(ValueError) as excinfo:
        await restricted_editor.read_file_contents(str(restricted_file))
    assert "Access denied" in str(excinfo.value)

    # Verify access to sibling file is denied
    with pytest.raises(ValueError) as excinfo:
        await restricted_editor.read_file_contents(str(sibling_file))
    assert "Access denied" in str(excinfo.value)


@pytest.mark.asyncio
async def test_multiple_allowed_paths(tmp_path):
    """Test editor with multiple allowed paths."""
    # Create multiple directories
    dir1 = tmp_path / "dir1"
    dir1.mkdir()
    dir1_file = dir1 / "file1.txt"
    dir1_file.write_text("Dir1 file content\n")

    dir2 = tmp_path / "dir2"
    dir2.mkdir()
    dir2_file = dir2 / "file2.txt"
    dir2_file.write_text("Dir2 file content\n")

    dir3 = tmp_path / "dir3"
    dir3.mkdir()
    dir3_file = dir3 / "file3.txt"
    dir3_file.write_text("Dir3 file content\n")

    # Create editor with multiple allowed paths
    editor = TextEditor(allowed_paths=[str(dir1), str(dir2)])

    # Verify access to allowed directories is permitted
    content, _, _, _, _, _ = await editor.read_file_contents(str(dir1_file))
    assert content == "Dir1 file content\n"

    content, _, _, _, _, _ = await editor.read_file_contents(str(dir2_file))
    assert content == "Dir2 file content\n"

    # Verify access to non-allowed directory is denied
    with pytest.raises(ValueError) as excinfo:
        await editor.read_file_contents(str(dir3_file))
    assert "Access denied" in str(excinfo.value)


@pytest.mark.asyncio
async def test_nonexistent_allowed_path(tmp_path):
    """Test that nonexistent allowed paths are ignored."""
    # Create a real directory and a file
    real_dir = tmp_path / "real"
    real_dir.mkdir()
    real_file = real_dir / "file.txt"
    real_file.write_text("Real file content\n")

    # Create a nonexistent path
    nonexistent_dir = tmp_path / "nonexistent"

    # Create editor with both real and nonexistent paths
    editor = TextEditor(allowed_paths=[str(real_dir), str(nonexistent_dir)])

    # Verify access to real directory is permitted
    content, _, _, _, _, _ = await editor.read_file_contents(str(real_file))
    assert content == "Real file content\n"

    # Verify the nonexistent path was ignored and not causing issues
    assert len(editor._allowed_paths) == 1
    assert os.path.samefile(next(iter(editor._allowed_paths)), str(real_dir))


@pytest.mark.asyncio
async def test_path_restrictions_write_operations(tmp_path):
    """Test path restrictions applied to write operations."""
    # Create directories
    allowed_dir = tmp_path / "allowed"
    allowed_dir.mkdir()
    allowed_file = allowed_dir / "file.txt"

    restricted_dir = tmp_path / "restricted"
    restricted_dir.mkdir()
    restricted_file = restricted_dir / "file.txt"

    # Create restricted editor
    editor = TextEditor(allowed_paths=[str(allowed_dir)])

    # Test writing to allowed path
    result = await editor.edit_file_contents(
        str(allowed_file),
        "",  # Empty hash for new file
        [{"start": 1, "contents": "Allowed content\n", "range_hash": ""}],
    )
    assert result["result"] == "ok"
    assert allowed_file.read_text() == "Allowed content\n"

    # Test writing to restricted path
    with pytest.raises(ValueError) as excinfo:
        await editor.edit_file_contents(
            str(restricted_file),
            "",
            [{"start": 1, "contents": "Restricted content\n", "range_hash": ""}],
        )
    assert "Access denied" in str(excinfo.value)
    assert not restricted_file.exists()


@pytest.mark.asyncio
async def test_path_traversal_attack(tmp_path):
    """Test protection against path traversal attacks."""
    # Create directories
    allowed_dir = tmp_path / "allowed"
    allowed_dir.mkdir()

    # Create file outside allowed directory
    outside_file = tmp_path / "outside.txt"
    outside_file.write_text("Outside content\n")

    # Path that tries to escape using ..
    traversal_path = str(allowed_dir / ".." / "outside.txt")

    # Create restricted editor
    editor = TextEditor(allowed_paths=[str(allowed_dir)])

    # Test reading with path traversal
    with pytest.raises(ValueError) as excinfo:
        await editor.read_file_contents(traversal_path)
    assert "Access denied" in str(excinfo.value)

    # Test writing with path traversal
    with pytest.raises(ValueError) as excinfo:
        await editor.edit_file_contents(
            traversal_path,
            "",
            [{"start": 1, "contents": "Traversal content\n", "range_hash": ""}],
        )
    assert "Access denied" in str(excinfo.value)


@pytest.mark.asyncio
async def test_symlink_handling(tmp_path):
    """Test handling of symlinks in path restrictions."""
    # Skip test on Windows which has different symlink behavior
    if os.name == "nt":
        pytest.skip("Skipping symlink test on Windows")

    # Create directories
    allowed_dir = tmp_path / "allowed"
    allowed_dir.mkdir()

    restricted_dir = tmp_path / "restricted"
    restricted_dir.mkdir()
    restricted_file = restricted_dir / "file.txt"
    restricted_file.write_text("Restricted content\n")

    # Create symlink from allowed to restricted
    symlink_path = allowed_dir / "symlink.txt"
    symlink_path.symlink_to(restricted_file)

    # Create restricted editor
    editor = TextEditor(allowed_paths=[str(allowed_dir)])

    # Test accessing file through symlink
    # This should not be allowed despite the symlink being within the allowed directory
    with pytest.raises(ValueError) as excinfo:
        await editor.read_file_contents(str(symlink_path))
    assert "Access denied" in str(excinfo.value)
