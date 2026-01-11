"""
Pytest fixtures for QMS CLI tests.

These fixtures provide isolated test environments that don't affect
the real QMS directory structure.
"""
import pytest
import sys
import tempfile
from pathlib import Path


@pytest.fixture
def temp_project(tmp_path):
    """
    Create a temporary project structure with QMS directories.
    Returns the project root path.
    """
    # Create QMS directory structure
    qms_root = tmp_path / "QMS"
    qms_root.mkdir()

    # Create document type directories
    (qms_root / "SOP").mkdir()
    (qms_root / "CR").mkdir()
    (qms_root / "INV").mkdir()
    (qms_root / "SDLC-FLOW").mkdir()
    (qms_root / "TEMPLATE").mkdir()

    # Create meta and audit directories
    (qms_root / ".meta" / "SOP").mkdir(parents=True)
    (qms_root / ".meta" / "CR").mkdir(parents=True)
    (qms_root / ".meta" / "INV").mkdir(parents=True)
    (qms_root / ".archive" / "SOP").mkdir(parents=True)
    (qms_root / ".archive" / "CR").mkdir(parents=True)
    (qms_root / ".audit" / "SOP").mkdir(parents=True)
    (qms_root / ".audit" / "CR").mkdir(parents=True)

    # Create user directories
    users_root = tmp_path / ".claude" / "users"
    for user in ["claude", "lead", "qa", "tu_ui", "tu_scene", "tu_sketch", "tu_sim", "bu"]:
        (users_root / user / "workspace").mkdir(parents=True)
        (users_root / user / "inbox").mkdir(parents=True)

    return tmp_path


@pytest.fixture
def sample_frontmatter():
    """Sample frontmatter for testing."""
    return {
        "title": "Test Document",
        "revision_summary": "Initial draft"
    }


@pytest.fixture
def sample_document_content():
    """Sample document content with frontmatter."""
    return '''---
title: Test Document
revision_summary: Initial draft
---

# Test Document

This is the body content.
'''


@pytest.fixture
def sample_document_no_frontmatter():
    """Sample document content without frontmatter."""
    return '''# Test Document

This is a document without frontmatter.
'''


@pytest.fixture
def qms_module(temp_project, monkeypatch):
    """
    Import qms module with patched PROJECT_ROOT.

    This fixture patches the global path variables to use the temp project
    so tests don't affect the real QMS structure.
    """
    # Add qms-cli to path
    qms_cli_path = Path(__file__).parent.parent
    if str(qms_cli_path) not in sys.path:
        sys.path.insert(0, str(qms_cli_path))

    # Change to temp directory so find_project_root() works
    monkeypatch.chdir(temp_project)

    # Import fresh - reload in dependency order so path constants are recomputed
    import importlib
    import qms_config
    import qms_paths
    import qms_io
    import qms_auth
    import qms

    # Reload modules in dependency order
    import qms_templates
    import qms_commands
    importlib.reload(qms_paths)
    importlib.reload(qms_templates)
    importlib.reload(qms_io)
    importlib.reload(qms_auth)
    importlib.reload(qms_commands)
    importlib.reload(qms)

    return qms
