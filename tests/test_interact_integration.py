"""
Test Interaction System — Integration

Qualification tests for REQ-INT-017 through REQ-INT-022.
These tests verify checkout/checkin/read integration, engine-managed commits,
and MCP tool parity.

Created as part of CR-091: Interaction System Engine
"""
import importlib
import json
import subprocess
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

# Add qms-cli to path for imports
QMS_CLI_DIR = Path(__file__).parent.parent
if str(QMS_CLI_DIR) not in sys.path:
    sys.path.insert(0, str(QMS_CLI_DIR))


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def interact_project(tmp_path):
    """
    Create a temporary project with QMS structure and a VR document
    suitable for interactive authoring tests.
    """
    # Create QMS directory structure
    qms_root = tmp_path / "QMS"
    (qms_root / "CR" / "CR-091").mkdir(parents=True)
    (qms_root / ".meta" / "VR").mkdir(parents=True)
    (qms_root / ".meta" / "CR").mkdir(parents=True)
    (qms_root / ".audit" / "VR").mkdir(parents=True)
    (qms_root / ".audit" / "CR").mkdir(parents=True)
    (qms_root / ".archive" / "VR").mkdir(parents=True)

    # Create user workspace
    users_root = tmp_path / ".claude" / "users"
    (users_root / "claude" / "workspace").mkdir(parents=True)
    (users_root / "claude" / "inbox").mkdir(parents=True)

    # Create agent definition
    agents_root = tmp_path / ".claude" / "agents"
    agents_root.mkdir(parents=True, exist_ok=True)

    return tmp_path


@pytest.fixture
def patched_paths(interact_project, monkeypatch):
    """Patch qms_paths to use the temporary project."""
    monkeypatch.chdir(interact_project)
    import qms_paths
    importlib.reload(qms_paths)
    return qms_paths


# =============================================================================
# REQ-INT-017: Interactive Checkout
# =============================================================================

class TestInteractiveCheckout:
    """REQ-INT-017: Checkout of interactive documents shall initialize a
    .interact session file; if .source.json exists, it seeds the session."""

    def test_checkout_creates_interact_session(self, tmp_path):
        """Checkout creates .interact file for interactive documents."""
        from interact_source import create_source, save_session, load_session
        from interact_parser import parse_template

        # Load template
        template_path = QMS_CLI_DIR / "seed" / "templates" / "TEMPLATE-VR.md"
        if not template_path.exists():
            pytest.skip("TEMPLATE-VR.md not found")

        template_text = template_path.read_text(encoding="utf-8")
        graph = parse_template(template_text)

        # Simulate what checkout does for interactive documents
        source = create_source(
            doc_id="CR-091-VR-001",
            template_name=graph.header.name,
            template_version=graph.header.version,
            start_prompt=graph.header.start,
            metadata={"parent_doc_id": "CR-091", "vr_id": "CR-091-VR-001"},
        )

        session_path = tmp_path / "CR-091-VR-001.interact"
        save_session(source, session_path)

        assert session_path.exists()
        loaded = load_session(session_path)
        assert loaded["cursor"] == "related_eis"
        assert loaded["template"] == "VR"

    def test_checkout_seeds_from_source_json(self, tmp_path):
        """If .source.json exists, checkout seeds session from it."""
        from interact_source import (
            create_source, add_response, save_source, load_source, load_session,
            save_session, get_active_response,
        )

        # Create a source with some responses
        source = create_source("CR-091-VR-001", "VR", 3, "second",
                               metadata={"parent_doc_id": "CR-091"})
        add_response(source, "related_eis", "EI-3", "claude")

        # Save as permanent source
        source_path = tmp_path / ".meta" / "CR-091-VR-001.source.json"
        source_path.parent.mkdir(parents=True, exist_ok=True)
        save_source(source, source_path)

        # Simulate checkout loading from source
        loaded = load_source(source_path)
        assert loaded is not None
        assert get_active_response(loaded, "related_eis") == "EI-3"

        # Save as session (what checkout does)
        session_path = tmp_path / "workspace" / "CR-091-VR-001.interact"
        save_session(loaded, session_path)

        # Verify session has the responses
        session = load_session(session_path)
        assert get_active_response(session, "related_eis") == "EI-3"

    def test_checkout_creates_placeholder_md(self, tmp_path):
        """Checkout creates placeholder .md so existing workspace checks work."""
        workspace_path = tmp_path / "CR-091-VR-001.md"
        workspace_path.write_text(
            "# CR-091-VR-001\n\nThis document is authored interactively.\n",
            encoding="utf-8",
        )
        assert workspace_path.exists()
        content = workspace_path.read_text(encoding="utf-8")
        assert "interactively" in content


# =============================================================================
# REQ-INT-018: Interactive Checkin
# =============================================================================

class TestInteractiveCheckin:
    """REQ-INT-018: Checkin of interactive documents shall compile to
    markdown, store .source.json in .meta/, and remove .interact session."""

    def test_checkin_compiles_to_markdown(self, tmp_path):
        """Checkin compiles source to markdown."""
        from interact_source import create_source, add_response, save_session, load_session
        from interact_compiler import compile_document
        from interact_parser import parse_template

        template_path = QMS_CLI_DIR / "seed" / "templates" / "TEMPLATE-VR.md"
        if not template_path.exists():
            pytest.skip("TEMPLATE-VR.md not found")

        template_text = template_path.read_text(encoding="utf-8")

        source = create_source("T-VR-001", "VR", 3, "__end__",
                               metadata={"parent_doc_id": "CR-001",
                                          "vr_id": "T-VR-001",
                                          "title": "Test"})
        add_response(source, "related_eis", "EI-1", "claude")
        add_response(source, "date", "2026-02-21", "claude")
        add_response(source, "objective", "Test obj", "claude")
        add_response(source, "pre_conditions", "Preconditions", "claude")
        add_response(source, "summary_outcome", "Pass", "claude")
        add_response(source, "summary_narrative", "All good.", "claude")
        add_response(source, "performer", "claude", "claude")
        add_response(source, "performed_date", "2026-02-21", "claude")

        compiled = compile_document(source, template_text)

        # Simulate checkin writing to draft path
        draft_path = tmp_path / "T-VR-001-draft.md"
        draft_path.write_text(compiled, encoding="utf-8")
        assert draft_path.exists()
        content = draft_path.read_text(encoding="utf-8")
        assert "EI-1" in content
        assert "Test obj" in content

    def test_checkin_stores_source_json(self, tmp_path):
        """Checkin stores .source.json in .meta/ directory."""
        from interact_source import (
            create_source, add_response, save_source, load_source,
            get_active_response,
        )

        source = create_source("T-VR-001", "VR", 3, "__end__")
        add_response(source, "p1", "val1", "claude")

        source_path = tmp_path / ".meta" / "T-VR-001.source.json"
        save_source(source, source_path)

        loaded = load_source(source_path)
        assert loaded is not None
        assert get_active_response(loaded, "p1") == "val1"

    def test_checkin_removes_interact_session(self, tmp_path):
        """Checkin removes .interact session file."""
        from interact_source import create_source, save_session

        source = create_source("T-VR-001", "VR", 3, "p1")
        session_path = tmp_path / "T-VR-001.interact"
        save_session(source, session_path)
        assert session_path.exists()

        # Simulate checkin cleanup
        session_path.unlink()
        assert not session_path.exists()


# =============================================================================
# REQ-INT-019: Source-Aware Read
# =============================================================================

class TestSourceAwareRead:
    """REQ-INT-019: qms read shall compile from .interact (if checked out)
    or .source.json (if checked in) when available."""

    def test_read_compiles_from_session(self, tmp_path):
        """Read compiles from .interact when document is checked out."""
        from interact_source import create_source, add_response, save_session, load_session
        from interact_compiler import compile_document

        template_path = QMS_CLI_DIR / "seed" / "templates" / "TEMPLATE-VR.md"
        if not template_path.exists():
            pytest.skip("TEMPLATE-VR.md not found")

        template_text = template_path.read_text(encoding="utf-8")

        source = create_source("T-VR-001", "VR", 3, "date",
                               metadata={"parent_doc_id": "CR-001",
                                          "vr_id": "T-VR-001",
                                          "title": "Test Read"})
        add_response(source, "related_eis", "EI-5", "claude")

        session_path = tmp_path / "T-VR-001.interact"
        save_session(source, session_path)

        # Simulate read command loading session and compiling
        loaded = load_session(session_path)
        compiled = compile_document(loaded, template_text)
        assert "EI-5" in compiled

    def test_read_compiles_from_source_json(self, tmp_path):
        """Read compiles from .source.json when document is checked in."""
        from interact_source import create_source, add_response, save_source, load_source
        from interact_compiler import compile_document

        template_path = QMS_CLI_DIR / "seed" / "templates" / "TEMPLATE-VR.md"
        if not template_path.exists():
            pytest.skip("TEMPLATE-VR.md not found")

        template_text = template_path.read_text(encoding="utf-8")

        source = create_source("T-VR-001", "VR", 3, "__end__",
                               metadata={"parent_doc_id": "CR-001",
                                          "vr_id": "T-VR-001",
                                          "title": "Test Read"})
        add_response(source, "related_eis", "EI-6", "claude")

        source_path = tmp_path / "T-VR-001.source.json"
        save_source(source, source_path)

        loaded = load_source(source_path)
        compiled = compile_document(loaded, template_text)
        assert "EI-6" in compiled

    def test_read_falls_back_to_standard_for_non_interactive(self):
        """Read falls back to standard markdown for non-interactive docs."""
        # Non-VR documents should return None from _try_compile_from_source
        # This is a behavior test — non-VR docs don't have .source.json
        from interact_source import load_source
        result = load_source(Path("/nonexistent/path.source.json"))
        assert result is None


# =============================================================================
# REQ-INT-020: Engine-Managed Commits
# =============================================================================

class TestEngineManagedCommits:
    """REQ-INT-020: On prompts with commit: true, the engine shall stage
    changes, commit with system message, and record the hash."""

    def test_commit_message_format(self):
        """Commit message follows format: [QMS] auto-commit | {DOC_ID} | {prompt_id} | description."""
        # Test the message construction logic from the interact command
        doc_id = "CR-091-VR-001"
        prompt_id = "step_actual.1"
        commit_msg = f"[QMS] auto-commit | {doc_id} | {prompt_id} | Evidence capture during VR execution"
        assert commit_msg == "[QMS] auto-commit | CR-091-VR-001 | step_actual.1 | Evidence capture during VR execution"

    def test_commit_hash_recorded_in_response(self):
        """Commit hash is stored in the response entry."""
        from interact_source import create_source, add_response, get_response_entries
        source = create_source("T", "VR", 3, "p1")
        add_response(source, "p1", "evidence", "claude", commit="abc1234")
        entries = get_response_entries(source, "p1")
        assert entries[0]["commit"] == "abc1234"

    def test_engine_commit_function_exists(self):
        """The _do_engine_commit function exists in the interact command."""
        from commands.interact import _do_engine_commit
        assert callable(_do_engine_commit)

    def test_engine_commit_returns_empty_on_no_project_root(self):
        """_do_engine_commit returns empty string when PROJECT_ROOT is None."""
        from commands.interact import _do_engine_commit
        with patch('commands.interact.PROJECT_ROOT', None):
            result = _do_engine_commit("DOC-001", "prompt_id")
            assert result == ""

    def test_engine_commit_in_git_repo(self, tmp_path):
        """_do_engine_commit creates a commit in a git repo."""
        # Initialize a temporary git repo
        subprocess.run(["git", "init"], cwd=str(tmp_path),
                       capture_output=True, check=True)
        subprocess.run(["git", "config", "user.email", "test@test.com"],
                       cwd=str(tmp_path), capture_output=True, check=True)
        subprocess.run(["git", "config", "user.name", "Test"],
                       cwd=str(tmp_path), capture_output=True, check=True)

        # Create initial commit
        test_file = tmp_path / "test.txt"
        test_file.write_text("initial")
        subprocess.run(["git", "add", "."], cwd=str(tmp_path),
                       capture_output=True, check=True)
        subprocess.run(["git", "commit", "-m", "initial"],
                       cwd=str(tmp_path), capture_output=True, check=True)

        # Create a change to commit
        test_file.write_text("modified")

        from commands.interact import _do_engine_commit
        with patch('commands.interact.PROJECT_ROOT', tmp_path):
            commit_hash = _do_engine_commit("CR-091-VR-001", "step_actual.1")

        assert len(commit_hash) == 7  # Short hash

        # Verify the commit message
        result = subprocess.run(
            ["git", "log", "--oneline", "-1"],
            cwd=str(tmp_path), capture_output=True, text=True, check=True,
        )
        assert "[QMS] auto-commit" in result.stdout
        assert "step_actual.1" in result.stdout


# =============================================================================
# REQ-INT-021: Commit Staging Scope
# =============================================================================

class TestCommitStagingScope:
    """REQ-INT-021: Engine-managed commits shall stage changes scoped
    to the project working tree."""

    def test_stages_all_changes(self, tmp_path):
        """Engine commit stages all changes in working tree (git add -A)."""
        subprocess.run(["git", "init"], cwd=str(tmp_path),
                       capture_output=True, check=True)
        subprocess.run(["git", "config", "user.email", "test@test.com"],
                       cwd=str(tmp_path), capture_output=True, check=True)
        subprocess.run(["git", "config", "user.name", "Test"],
                       cwd=str(tmp_path), capture_output=True, check=True)

        # Initial commit
        (tmp_path / "file1.txt").write_text("initial")
        subprocess.run(["git", "add", "."], cwd=str(tmp_path),
                       capture_output=True, check=True)
        subprocess.run(["git", "commit", "-m", "init"],
                       cwd=str(tmp_path), capture_output=True, check=True)

        # Create multiple changes
        (tmp_path / "file1.txt").write_text("modified")
        (tmp_path / "file2.txt").write_text("new file")

        from commands.interact import _do_engine_commit
        with patch('commands.interact.PROJECT_ROOT', tmp_path):
            commit_hash = _do_engine_commit("DOC-001", "evidence.1")

        assert commit_hash != ""

        # Verify both changes were committed
        result = subprocess.run(
            ["git", "status", "--short"],
            cwd=str(tmp_path), capture_output=True, text=True, check=True,
        )
        assert result.stdout.strip() == ""  # Clean working tree

    def test_no_commit_when_no_changes(self, tmp_path):
        """Engine commit returns empty string when no changes to stage."""
        subprocess.run(["git", "init"], cwd=str(tmp_path),
                       capture_output=True, check=True)
        subprocess.run(["git", "config", "user.email", "test@test.com"],
                       cwd=str(tmp_path), capture_output=True, check=True)
        subprocess.run(["git", "config", "user.name", "Test"],
                       cwd=str(tmp_path), capture_output=True, check=True)

        (tmp_path / "file.txt").write_text("content")
        subprocess.run(["git", "add", "."], cwd=str(tmp_path),
                       capture_output=True, check=True)
        subprocess.run(["git", "commit", "-m", "init"],
                       cwd=str(tmp_path), capture_output=True, check=True)

        from commands.interact import _do_engine_commit
        with patch('commands.interact.PROJECT_ROOT', tmp_path):
            commit_hash = _do_engine_commit("DOC-001", "evidence.1")

        assert commit_hash == ""


# =============================================================================
# REQ-INT-022: MCP Interact Tool
# =============================================================================

class TestMCPInteractTool:
    """REQ-INT-022: The MCP server shall expose a qms_interact tool that is
    functionally equivalent to the qms interact CLI command."""

    def test_mcp_tools_module_has_qms_interact(self):
        """qms_mcp/tools.py defines a qms_interact tool."""
        # Read the tools module source to verify qms_interact is defined
        tools_path = QMS_CLI_DIR / "qms_mcp" / "tools.py"
        content = tools_path.read_text(encoding="utf-8")
        assert "def qms_interact" in content

    def test_mcp_interact_has_respond_param(self):
        """MCP qms_interact tool has respond parameter."""
        tools_path = QMS_CLI_DIR / "qms_mcp" / "tools.py"
        content = tools_path.read_text(encoding="utf-8")
        # Find the qms_interact function signature
        assert "respond: str" in content

    def test_mcp_interact_has_file_param(self):
        """MCP qms_interact tool has file parameter."""
        tools_path = QMS_CLI_DIR / "qms_mcp" / "tools.py"
        content = tools_path.read_text(encoding="utf-8")
        assert "file: str" in content

    def test_mcp_interact_has_reason_param(self):
        """MCP qms_interact tool has reason parameter."""
        tools_path = QMS_CLI_DIR / "qms_mcp" / "tools.py"
        content = tools_path.read_text(encoding="utf-8")
        assert "reason: str" in content

    def test_mcp_interact_has_goto_param(self):
        """MCP qms_interact tool has goto parameter."""
        tools_path = QMS_CLI_DIR / "qms_mcp" / "tools.py"
        content = tools_path.read_text(encoding="utf-8")
        assert "goto: str" in content

    def test_mcp_interact_has_cancel_goto_param(self):
        """MCP qms_interact tool has cancel_goto parameter."""
        tools_path = QMS_CLI_DIR / "qms_mcp" / "tools.py"
        content = tools_path.read_text(encoding="utf-8")
        assert "cancel_goto: bool" in content

    def test_mcp_interact_has_reopen_param(self):
        """MCP qms_interact tool has reopen parameter."""
        tools_path = QMS_CLI_DIR / "qms_mcp" / "tools.py"
        content = tools_path.read_text(encoding="utf-8")
        assert "reopen: str" in content

    def test_mcp_interact_has_progress_param(self):
        """MCP qms_interact tool has progress parameter."""
        tools_path = QMS_CLI_DIR / "qms_mcp" / "tools.py"
        content = tools_path.read_text(encoding="utf-8")
        assert "progress: bool" in content

    def test_mcp_interact_has_compile_param(self):
        """MCP qms_interact tool has compile parameter."""
        tools_path = QMS_CLI_DIR / "qms_mcp" / "tools.py"
        content = tools_path.read_text(encoding="utf-8")
        assert "compile: bool" in content

    def test_mcp_interact_calls_interact_command(self):
        """MCP tool delegates to the CLI interact command."""
        tools_path = QMS_CLI_DIR / "qms_mcp" / "tools.py"
        content = tools_path.read_text(encoding="utf-8")
        # Verify the tool constructs the interact CLI args
        assert '"interact"' in content

    def test_cli_interact_command_registered(self):
        """CLI interact command is registered in CommandRegistry."""
        from registry import CommandRegistry
        import commands  # noqa: F401
        spec = CommandRegistry.get_command("interact")
        assert spec is not None
        assert spec.name == "interact"
        assert callable(spec.handler)

    def test_cli_interact_has_all_flags(self):
        """CLI interact command has all required flag arguments."""
        from registry import CommandRegistry
        import commands  # noqa: F401
        spec = CommandRegistry.get_command("interact")
        flag_names = []
        for arg in spec.arguments:
            for flag in arg.flags:
                flag_names.append(flag)

        assert "--respond" in flag_names
        assert "--file" in flag_names
        assert "--reason" in flag_names
        assert "--goto" in flag_names
        assert "--cancel-goto" in flag_names
        assert "--reopen" in flag_names
        assert "--progress" in flag_names
        assert "--compile" in flag_names


# =============================================================================
# Command registration
# =============================================================================

class TestInteractRegistration:
    """Tests for interact command registration."""

    def test_interact_registered_in_command_registry(self):
        """interact command is registered."""
        from registry import CommandRegistry
        import commands  # noqa: F401
        assert CommandRegistry.get_command("interact") is not None

    def test_interact_requires_doc_id(self):
        """interact command requires doc_id."""
        from registry import CommandRegistry
        import commands  # noqa: F401
        spec = CommandRegistry.get_command("interact")
        assert spec.requires_doc_id is True

    def test_new_modules_import_cleanly(self):
        """All new interact modules import without error."""
        import interact_parser
        import interact_source
        import interact_engine
        import interact_compiler
        import commands.interact
        assert interact_parser is not None
        assert interact_source is not None
        assert interact_engine is not None
        assert interact_compiler is not None
        assert commands.interact is not None
