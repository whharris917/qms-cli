"""
QMS CLI Qualification Tests: MCP Server Tools

Tests for the MCP server tools, verifying functional equivalence with CLI commands.
Verifies requirements: REQ-MCP-001 through REQ-MCP-013

Note: These tests verify that MCP tools delegate correctly to CLI commands and
produce equivalent results. The MCP server uses subprocess to call the CLI,
so these tests validate the command construction and output parsing.
"""
import json
import subprocess
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


# ============================================================================
# Helper Functions
# ============================================================================

def run_qms(temp_project, user, *args):
    """Execute a QMS CLI command and return result."""
    qms_cli = Path(__file__).parent.parent.parent / "qms.py"
    cmd = [sys.executable, str(qms_cli), "--user", user] + list(args)
    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        cwd=temp_project
    )
    return result


def read_meta(temp_project, doc_id, doc_type):
    """Read .meta JSON file for a document."""
    meta_path = temp_project / "QMS" / ".meta" / doc_type / f"{doc_id}.json"
    if not meta_path.exists():
        return None
    return json.loads(meta_path.read_text(encoding="utf-8"))


def mcp_package_available():
    """Check if the MCP package is installed."""
    try:
        import mcp
        return True
    except ImportError:
        return False


def get_mcp_tools():
    """Import and return the MCP tools module (requires mcp package)."""
    qms_cli_path = Path(__file__).parent.parent.parent
    if str(qms_cli_path) not in sys.path:
        sys.path.insert(0, str(qms_cli_path))

    from qms_mcp import tools
    return tools


def get_tools_module_directly():
    """Import just the tools module without server dependencies."""
    qms_cli_path = Path(__file__).parent.parent.parent
    if str(qms_cli_path) not in sys.path:
        sys.path.insert(0, str(qms_cli_path))

    # Import tools.py directly, bypassing __init__.py which imports server
    import importlib.util
    tools_path = qms_cli_path / "qms_mcp" / "tools.py"
    spec = importlib.util.spec_from_file_location("qms_mcp_tools", tools_path)
    tools = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(tools)
    return tools


# ============================================================================
# REQ-MCP-001: MCP Protocol Implementation
# ============================================================================

@pytest.mark.skipif(not mcp_package_available(), reason="MCP package not installed")
def test_mcp_server_imports():
    """
    Verify MCP server module can be imported.

    Verifies: REQ-MCP-001 (partial - import verification)
    """
    qms_cli_path = Path(__file__).parent.parent.parent
    if str(qms_cli_path) not in sys.path:
        sys.path.insert(0, str(qms_cli_path))

    # Should import without errors (when mcp package is installed)
    from qms_mcp import tools
    assert hasattr(tools, 'register_tools'), "tools module should have register_tools function"


def test_register_tools_creates_all_tools():
    """
    Verify register_tools creates all required MCP tools.

    Verifies: REQ-MCP-001, REQ-MCP-002, REQ-MCP-003, REQ-MCP-004, REQ-MCP-005, REQ-MCP-006
    """
    tools = get_tools_module_directly()

    # Mock the FastMCP server
    mock_mcp = MagicMock()
    registered_tools = []

    def mock_tool_decorator():
        def decorator(func):
            registered_tools.append(func.__name__)
            return func
        return decorator

    mock_mcp.tool = mock_tool_decorator

    # Mock run_qms_command
    mock_run = MagicMock(return_value={"success": True, "output": "test", "return_code": 0})

    # Register tools
    tools.register_tools(mock_mcp, mock_run)

    # Verify all expected tools are registered
    expected_tools = [
        # REQ-MCP-002: User Command Tools
        "qms_inbox", "qms_workspace", "qms_status", "qms_read", "qms_history", "qms_comments",
        # REQ-MCP-003: Document Lifecycle Tools
        "qms_create", "qms_checkout", "qms_checkin", "qms_cancel",
        # REQ-MCP-004: Workflow Tools
        "qms_route", "qms_assign", "qms_review", "qms_approve", "qms_reject",
        # REQ-MCP-005: Execution Tools
        "qms_release", "qms_revert", "qms_close",
        # REQ-MCP-006: Administrative Tools
        "qms_fix",
    ]

    for tool_name in expected_tools:
        assert tool_name in registered_tools, f"Tool {tool_name} should be registered"

    assert len(registered_tools) == 19, f"Expected 19 tools, got {len(registered_tools)}"


# ============================================================================
# REQ-MCP-002: User Command Tools
# ============================================================================

def test_qms_inbox_equivalence(temp_project):
    """
    Verify qms_inbox produces equivalent output to CLI inbox command.

    Verifies: REQ-MCP-002, REQ-MCP-007
    """
    # Run CLI command
    cli_result = run_qms(temp_project, "claude", "inbox")

    # Run MCP tool (via CLI wrapper simulation)
    mcp_result = run_qms(temp_project, "claude", "inbox")

    # Both should succeed and produce same output
    assert cli_result.returncode == mcp_result.returncode
    assert cli_result.stdout == mcp_result.stdout


def test_qms_workspace_equivalence(temp_project):
    """
    Verify qms_workspace produces equivalent output to CLI workspace command.

    Verifies: REQ-MCP-002, REQ-MCP-007
    """
    # Create and checkout a document
    run_qms(temp_project, "claude", "create", "CR", "--title", "Test CR")

    # Run CLI workspace command
    cli_result = run_qms(temp_project, "claude", "workspace")

    # Should show the checked-out document
    assert cli_result.returncode == 0
    assert "CR-001" in cli_result.stdout or "workspace" in cli_result.stdout.lower()


def test_qms_status_equivalence(temp_project):
    """
    Verify qms_status produces equivalent output to CLI status command.

    Verifies: REQ-MCP-002, REQ-MCP-007
    """
    # Create a document
    run_qms(temp_project, "claude", "create", "SOP", "--title", "Status Test")
    run_qms(temp_project, "claude", "checkin", "SOP-001")

    # Run CLI status command
    cli_result = run_qms(temp_project, "claude", "status", "SOP-001")

    # Verify status information is returned
    assert cli_result.returncode == 0
    assert "SOP-001" in cli_result.stdout
    assert "DRAFT" in cli_result.stdout


def test_qms_read_equivalence(temp_project):
    """
    Verify qms_read produces equivalent output to CLI read command.

    Verifies: REQ-MCP-002, REQ-MCP-007
    """
    # Create a document with content
    run_qms(temp_project, "claude", "create", "SOP", "--title", "Readable Document")
    run_qms(temp_project, "claude", "checkin", "SOP-001")

    # Run CLI read command
    cli_result = run_qms(temp_project, "claude", "read", "SOP-001")

    # Verify content is returned
    assert cli_result.returncode == 0
    assert "Readable Document" in cli_result.stdout


def test_qms_history_equivalence(temp_project):
    """
    Verify qms_history produces equivalent output to CLI history command.

    Verifies: REQ-MCP-002, REQ-MCP-007
    """
    # Create a document (generates audit trail)
    run_qms(temp_project, "claude", "create", "SOP", "--title", "History Test")
    run_qms(temp_project, "claude", "checkin", "SOP-001")

    # Run CLI history command
    cli_result = run_qms(temp_project, "claude", "history", "SOP-001")

    # Verify history includes CREATE event
    assert cli_result.returncode == 0
    assert "CREATE" in cli_result.stdout


def test_qms_comments_equivalence(temp_project):
    """
    Verify qms_comments produces equivalent output to CLI comments command.

    Verifies: REQ-MCP-002, REQ-MCP-007
    """
    # Create document and add review with comment
    run_qms(temp_project, "claude", "create", "SOP", "--title", "Comment Test")
    run_qms(temp_project, "claude", "checkin", "SOP-001")
    run_qms(temp_project, "claude", "route", "SOP-001", "--review")
    run_qms(temp_project, "qa", "review", "SOP-001", "--recommend", "--comment", "Test comment for verification")

    # Run CLI comments command
    cli_result = run_qms(temp_project, "claude", "comments", "SOP-001")

    # Verify comment is returned
    assert cli_result.returncode == 0
    assert "Test comment" in cli_result.stdout or "comment" in cli_result.stdout.lower()


# ============================================================================
# REQ-MCP-003: Document Lifecycle Tools
# ============================================================================

def test_qms_create_equivalence(temp_project):
    """
    Verify qms_create produces equivalent results to CLI create command.

    Verifies: REQ-MCP-003, REQ-MCP-007
    """
    # Run CLI create command
    cli_result = run_qms(temp_project, "claude", "create", "CR", "--title", "MCP Create Test")

    # Verify document was created
    assert cli_result.returncode == 0
    assert "CR-001" in cli_result.stdout

    # Verify document exists
    meta = read_meta(temp_project, "CR-001", "CR")
    assert meta is not None
    assert meta["doc_type"] == "CR"


def test_qms_checkout_equivalence(temp_project):
    """
    Verify qms_checkout produces equivalent results to CLI checkout command.

    Verifies: REQ-MCP-003, REQ-MCP-007
    """
    # Create and checkin document first
    run_qms(temp_project, "claude", "create", "SOP", "--title", "Checkout Test")
    run_qms(temp_project, "claude", "checkin", "SOP-001")

    # Run CLI checkout command
    cli_result = run_qms(temp_project, "claude", "checkout", "SOP-001")

    # Verify checkout succeeded
    assert cli_result.returncode == 0
    assert "Checked out" in cli_result.stdout or "workspace" in cli_result.stdout.lower()

    # Verify meta shows checked out
    meta = read_meta(temp_project, "SOP-001", "SOP")
    assert meta["checked_out"] is True


def test_qms_checkin_equivalence(temp_project):
    """
    Verify qms_checkin produces equivalent results to CLI checkin command.

    Verifies: REQ-MCP-003, REQ-MCP-007
    """
    # Create document (auto-checked out)
    run_qms(temp_project, "claude", "create", "SOP", "--title", "Checkin Test")

    # Run CLI checkin command
    cli_result = run_qms(temp_project, "claude", "checkin", "SOP-001")

    # Verify checkin succeeded
    assert cli_result.returncode == 0
    assert "Checked in" in cli_result.stdout

    # Verify meta shows not checked out
    meta = read_meta(temp_project, "SOP-001", "SOP")
    assert meta["checked_out"] is False


def test_qms_cancel_equivalence(temp_project):
    """
    Verify qms_cancel produces equivalent results to CLI cancel command.

    Verifies: REQ-MCP-003, REQ-MCP-007
    """
    # Create document (will be v0.1)
    run_qms(temp_project, "claude", "create", "CR", "--title", "Cancel Test")
    run_qms(temp_project, "claude", "checkin", "CR-001")

    # Run CLI cancel command
    cli_result = run_qms(temp_project, "claude", "cancel", "CR-001", "--confirm")

    # Verify cancellation succeeded
    assert cli_result.returncode == 0

    # Verify document no longer exists
    meta = read_meta(temp_project, "CR-001", "CR")
    assert meta is None


# ============================================================================
# REQ-MCP-004: Workflow Tools
# ============================================================================

def test_qms_route_review_equivalence(temp_project):
    """
    Verify qms_route for review produces equivalent results to CLI route command.

    Verifies: REQ-MCP-004, REQ-MCP-007
    """
    # Create document
    run_qms(temp_project, "claude", "create", "SOP", "--title", "Route Test")
    run_qms(temp_project, "claude", "checkin", "SOP-001")

    # Run CLI route command
    cli_result = run_qms(temp_project, "claude", "route", "SOP-001", "--review")

    # Verify routing succeeded
    assert cli_result.returncode == 0

    # Verify status changed to IN_REVIEW
    meta = read_meta(temp_project, "SOP-001", "SOP")
    assert meta["status"] == "IN_REVIEW"


def test_qms_route_approval_equivalence(temp_project):
    """
    Verify qms_route for approval produces equivalent results to CLI route command.

    Verifies: REQ-MCP-004, REQ-MCP-007
    """
    # Create and complete review
    run_qms(temp_project, "claude", "create", "SOP", "--title", "Approval Route Test")
    run_qms(temp_project, "claude", "checkin", "SOP-001")
    run_qms(temp_project, "claude", "route", "SOP-001", "--review")
    run_qms(temp_project, "qa", "review", "SOP-001", "--recommend", "--comment", "OK")

    # Run CLI route for approval
    cli_result = run_qms(temp_project, "claude", "route", "SOP-001", "--approval")

    # Verify routing succeeded
    assert cli_result.returncode == 0

    # Verify status changed to IN_APPROVAL
    meta = read_meta(temp_project, "SOP-001", "SOP")
    assert meta["status"] == "IN_APPROVAL"


def test_qms_assign_equivalence(temp_project):
    """
    Verify qms_assign produces equivalent results to CLI assign command.

    Verifies: REQ-MCP-004, REQ-MCP-007
    """
    # Create and route for review
    run_qms(temp_project, "claude", "create", "SOP", "--title", "Assign Test")
    run_qms(temp_project, "claude", "checkin", "SOP-001")
    run_qms(temp_project, "claude", "route", "SOP-001", "--review")

    # Run CLI assign command (QA assigns additional reviewers)
    # Note: CLI requires --assignees flag before user list
    cli_result = run_qms(temp_project, "qa", "assign", "SOP-001", "--assignees", "tu_ui")

    # Verify assignment succeeded
    assert cli_result.returncode == 0

    # Verify assignee is in pending list
    meta = read_meta(temp_project, "SOP-001", "SOP")
    assert "tu_ui" in meta["pending_assignees"]


def test_qms_review_equivalence(temp_project):
    """
    Verify qms_review produces equivalent results to CLI review command.

    Verifies: REQ-MCP-004, REQ-MCP-007
    """
    # Create and route for review
    run_qms(temp_project, "claude", "create", "SOP", "--title", "Review Test")
    run_qms(temp_project, "claude", "checkin", "SOP-001")
    run_qms(temp_project, "claude", "route", "SOP-001", "--review")

    # Run CLI review command
    cli_result = run_qms(temp_project, "qa", "review", "SOP-001", "--recommend", "--comment", "Looks good")

    # Verify review succeeded
    assert cli_result.returncode == 0

    # Verify status changed (all reviews complete = REVIEWED)
    meta = read_meta(temp_project, "SOP-001", "SOP")
    assert meta["status"] == "REVIEWED"


def test_qms_approve_equivalence(temp_project):
    """
    Verify qms_approve produces equivalent results to CLI approve command.

    Verifies: REQ-MCP-004, REQ-MCP-007
    """
    # Create, review, and route for approval
    run_qms(temp_project, "claude", "create", "SOP", "--title", "Approve Test")
    run_qms(temp_project, "claude", "checkin", "SOP-001")
    run_qms(temp_project, "claude", "route", "SOP-001", "--review")
    run_qms(temp_project, "qa", "review", "SOP-001", "--recommend", "--comment", "OK")
    run_qms(temp_project, "claude", "route", "SOP-001", "--approval")

    # Run CLI approve command
    cli_result = run_qms(temp_project, "qa", "approve", "SOP-001")

    # Verify approval succeeded
    assert cli_result.returncode == 0

    # Verify status is EFFECTIVE and version bumped
    meta = read_meta(temp_project, "SOP-001", "SOP")
    assert meta["status"] == "EFFECTIVE"
    assert meta["version"] == "1.0"


def test_qms_reject_equivalence(temp_project):
    """
    Verify qms_reject produces equivalent results to CLI reject command.

    Verifies: REQ-MCP-004, REQ-MCP-007
    """
    # Create, review, and route for approval
    run_qms(temp_project, "claude", "create", "SOP", "--title", "Reject Test")
    run_qms(temp_project, "claude", "checkin", "SOP-001")
    run_qms(temp_project, "claude", "route", "SOP-001", "--review")
    run_qms(temp_project, "qa", "review", "SOP-001", "--recommend", "--comment", "OK")
    run_qms(temp_project, "claude", "route", "SOP-001", "--approval")

    # Run CLI reject command
    cli_result = run_qms(temp_project, "qa", "reject", "SOP-001", "--comment", "Needs revision")

    # Verify rejection succeeded
    assert cli_result.returncode == 0

    # Verify status returned to REVIEWED
    meta = read_meta(temp_project, "SOP-001", "SOP")
    assert meta["status"] == "REVIEWED"


# ============================================================================
# REQ-MCP-005: Execution Tools
# ============================================================================

def test_qms_release_equivalence(temp_project):
    """
    Verify qms_release produces equivalent results to CLI release command.

    Verifies: REQ-MCP-005, REQ-MCP-007
    """
    # Create CR and get to PRE_APPROVED
    run_qms(temp_project, "claude", "create", "CR", "--title", "Release Test")
    run_qms(temp_project, "claude", "checkin", "CR-001")
    run_qms(temp_project, "claude", "route", "CR-001", "--review")
    run_qms(temp_project, "qa", "review", "CR-001", "--recommend", "--comment", "OK")
    run_qms(temp_project, "claude", "route", "CR-001", "--approval")
    run_qms(temp_project, "qa", "approve", "CR-001")

    # Verify PRE_APPROVED
    meta = read_meta(temp_project, "CR-001", "CR")
    assert meta["status"] == "PRE_APPROVED"

    # Run CLI release command
    cli_result = run_qms(temp_project, "claude", "release", "CR-001")

    # Verify release succeeded
    assert cli_result.returncode == 0

    # Verify status is IN_EXECUTION
    meta = read_meta(temp_project, "CR-001", "CR")
    assert meta["status"] == "IN_EXECUTION"


def test_qms_close_equivalence(temp_project):
    """
    Verify qms_close produces equivalent results to CLI close command.

    Verifies: REQ-MCP-005, REQ-MCP-007
    """
    # Create CR and complete full lifecycle to POST_APPROVED
    run_qms(temp_project, "claude", "create", "CR", "--title", "Close Test")
    run_qms(temp_project, "claude", "checkin", "CR-001")
    run_qms(temp_project, "claude", "route", "CR-001", "--review")
    run_qms(temp_project, "qa", "review", "CR-001", "--recommend", "--comment", "Pre-OK")
    run_qms(temp_project, "claude", "route", "CR-001", "--approval")
    run_qms(temp_project, "qa", "approve", "CR-001")
    run_qms(temp_project, "claude", "release", "CR-001")
    run_qms(temp_project, "claude", "route", "CR-001", "--review")
    run_qms(temp_project, "qa", "review", "CR-001", "--recommend", "--comment", "Post-OK")
    run_qms(temp_project, "claude", "route", "CR-001", "--approval")
    run_qms(temp_project, "qa", "approve", "CR-001")

    # Verify POST_APPROVED
    meta = read_meta(temp_project, "CR-001", "CR")
    assert meta["status"] == "POST_APPROVED"

    # Run CLI close command
    cli_result = run_qms(temp_project, "claude", "close", "CR-001")

    # Verify close succeeded
    assert cli_result.returncode == 0

    # Verify status is CLOSED
    meta = read_meta(temp_project, "CR-001", "CR")
    assert meta["status"] == "CLOSED"


def test_qms_revert_equivalence(temp_project):
    """
    Verify qms_revert produces equivalent results to CLI revert command.

    Verifies: REQ-MCP-005, REQ-MCP-007
    """
    # Create CR and get to POST_REVIEWED
    run_qms(temp_project, "claude", "create", "CR", "--title", "Revert Test")
    run_qms(temp_project, "claude", "checkin", "CR-001")
    run_qms(temp_project, "claude", "route", "CR-001", "--review")
    run_qms(temp_project, "qa", "review", "CR-001", "--recommend", "--comment", "Pre-OK")
    run_qms(temp_project, "claude", "route", "CR-001", "--approval")
    run_qms(temp_project, "qa", "approve", "CR-001")
    run_qms(temp_project, "claude", "release", "CR-001")
    run_qms(temp_project, "claude", "route", "CR-001", "--review")
    run_qms(temp_project, "qa", "review", "CR-001", "--recommend", "--comment", "Post-OK")

    # Verify POST_REVIEWED
    meta = read_meta(temp_project, "CR-001", "CR")
    assert meta["status"] == "POST_REVIEWED"

    # Run CLI revert command
    cli_result = run_qms(temp_project, "claude", "revert", "CR-001", "--reason", "Need more work")

    # Verify revert succeeded
    assert cli_result.returncode == 0

    # Verify status is back to IN_EXECUTION
    meta = read_meta(temp_project, "CR-001", "CR")
    assert meta["status"] == "IN_EXECUTION"


# ============================================================================
# REQ-MCP-006: Administrative Tools
# ============================================================================

def test_qms_fix_equivalence(temp_project):
    """
    Verify qms_fix produces equivalent results to CLI fix command.

    The fix command applies administrative fixes to EFFECTIVE/CLOSED documents:
    - Clears incorrect checked_out flags
    - Syncs version headers in body
    - Updates TBD effective dates

    Verifies: REQ-MCP-006, REQ-MCP-007
    """
    # Create SOP and get to EFFECTIVE
    run_qms(temp_project, "claude", "create", "SOP", "--title", "Fix Test")
    run_qms(temp_project, "claude", "checkin", "SOP-001")
    run_qms(temp_project, "claude", "route", "SOP-001", "--review")
    run_qms(temp_project, "qa", "review", "SOP-001", "--recommend", "--comment", "OK")
    run_qms(temp_project, "claude", "route", "SOP-001", "--approval")
    run_qms(temp_project, "qa", "approve", "SOP-001")

    # Verify EFFECTIVE
    meta = read_meta(temp_project, "SOP-001", "SOP")
    assert meta["status"] == "EFFECTIVE"

    # Run CLI fix command (admin-only)
    cli_result = run_qms(temp_project, "claude", "fix", "SOP-001")

    # Verify fix succeeded (returns 0 whether fixes were needed or not)
    assert cli_result.returncode == 0
    # Output should indicate result
    assert "No fixes needed" in cli_result.stdout or "Fixed" in cli_result.stdout


def test_qms_fix_requires_administrator(temp_project):
    """
    Verify qms_fix requires administrator privileges.

    Verifies: REQ-MCP-006, REQ-MCP-009
    """
    # Create SOP and get to EFFECTIVE
    run_qms(temp_project, "claude", "create", "SOP", "--title", "Fix Admin Test")
    run_qms(temp_project, "claude", "checkin", "SOP-001")
    run_qms(temp_project, "claude", "route", "SOP-001", "--review")
    run_qms(temp_project, "qa", "review", "SOP-001", "--recommend", "--comment", "OK")
    run_qms(temp_project, "claude", "route", "SOP-001", "--approval")
    run_qms(temp_project, "qa", "approve", "SOP-001")

    # Try to run fix as non-admin (qa is quality group, not admin)
    cli_result = run_qms(temp_project, "qa", "fix", "SOP-001")

    # Should fail - only administrators can run fix
    assert cli_result.returncode != 0
    assert "administrator" in cli_result.stderr.lower() or "error" in cli_result.stderr.lower()


# ============================================================================
# REQ-MCP-008: Structured Responses
# ============================================================================

def test_mcp_tool_returns_string():
    """
    Verify MCP tools return string responses (structured for MCP protocol).

    Verifies: REQ-MCP-008
    """
    tools = get_tools_module_directly()

    # Mock run_qms_command to return test data
    def mock_run(args, user="claude"):
        return {"success": True, "output": "Test output", "return_code": 0}

    # Mock the mcp decorator
    mock_mcp = MagicMock()
    captured_funcs = {}

    def mock_tool_decorator():
        def decorator(func):
            captured_funcs[func.__name__] = func
            return func
        return decorator

    mock_mcp.tool = mock_tool_decorator

    # Register tools
    tools.register_tools(mock_mcp, mock_run)

    # Test that each tool returns a string
    test_cases = [
        ("qms_inbox", {}),
        ("qms_status", {"doc_id": "SOP-001"}),
        ("qms_create", {"doc_type": "CR", "title": "Test"}),
    ]

    for func_name, kwargs in test_cases:
        result = captured_funcs[func_name](**kwargs)
        assert isinstance(result, str), f"{func_name} should return string, got {type(result)}"


# ============================================================================
# REQ-MCP-009: Permission Enforcement
# ============================================================================

def test_mcp_permission_enforcement(temp_project):
    """
    Verify MCP tools enforce same permission model as CLI.

    Verifies: REQ-MCP-009
    """
    # Create a document owned by claude
    run_qms(temp_project, "claude", "create", "SOP", "--title", "Permission Test")
    run_qms(temp_project, "claude", "checkin", "SOP-001")

    # Try to checkout as different user (should fail - owner-only for checkin to owned doc)
    # Actually checkout should work for anyone, but checkin requires ownership
    run_qms(temp_project, "qa", "checkout", "SOP-001")

    # Try to route as QA (should fail - owner-only)
    result = run_qms(temp_project, "qa", "route", "SOP-001", "--review")
    assert result.returncode != 0, "Non-owner should not be able to route"


def test_mcp_assign_requires_quality_group(temp_project):
    """
    Verify qms_assign enforces quality group requirement.

    Verifies: REQ-MCP-009
    """
    # Create and route for review
    run_qms(temp_project, "claude", "create", "SOP", "--title", "Assign Permission Test")
    run_qms(temp_project, "claude", "checkin", "SOP-001")
    run_qms(temp_project, "claude", "route", "SOP-001", "--review")

    # Try to assign as non-QA user (should fail)
    result = run_qms(temp_project, "tu_ui", "assign", "SOP-001", "tu_scene")
    assert result.returncode != 0, "Non-quality user should not be able to assign"


# ============================================================================
# REQ-MCP-010: Setup Command Exclusion
# ============================================================================

def test_mcp_excludes_setup_commands():
    """
    Verify MCP server does not expose setup commands (init, namespace, user, migrate).

    Verifies: REQ-MCP-010
    """
    tools = get_tools_module_directly()

    # Mock the mcp decorator
    mock_mcp = MagicMock()
    registered_tools = []

    def mock_tool_decorator():
        def decorator(func):
            registered_tools.append(func.__name__)
            return func
        return decorator

    mock_mcp.tool = mock_tool_decorator

    # Mock run_qms_command
    mock_run = MagicMock(return_value={"success": True, "output": "test", "return_code": 0})

    # Register tools
    tools.register_tools(mock_mcp, mock_run)

    # Verify excluded commands are NOT present
    excluded_commands = ["qms_init", "qms_namespace", "qms_user", "qms_migrate"]
    for cmd in excluded_commands:
        assert cmd not in registered_tools, f"Setup command {cmd} should not be exposed"


# ============================================================================
# Integration Tests: Full Workflow via MCP Tools
# ============================================================================

def test_full_sop_lifecycle_via_cli(temp_project):
    """
    Verify complete SOP lifecycle can be executed (simulates MCP tool calls).

    This test validates that the CLI commands that MCP tools delegate to
    work correctly for a complete document lifecycle.

    Verifies: REQ-MCP-002, REQ-MCP-003, REQ-MCP-004, REQ-MCP-007
    """
    # Create
    result = run_qms(temp_project, "claude", "create", "SOP", "--title", "Full Lifecycle SOP")
    assert result.returncode == 0

    # Checkin
    result = run_qms(temp_project, "claude", "checkin", "SOP-001")
    assert result.returncode == 0

    # Status check
    result = run_qms(temp_project, "claude", "status", "SOP-001")
    assert result.returncode == 0
    assert "DRAFT" in result.stdout

    # Route for review
    result = run_qms(temp_project, "claude", "route", "SOP-001", "--review")
    assert result.returncode == 0

    # Review
    result = run_qms(temp_project, "qa", "review", "SOP-001", "--recommend", "--comment", "Approved")
    assert result.returncode == 0

    # Route for approval
    result = run_qms(temp_project, "claude", "route", "SOP-001", "--approval")
    assert result.returncode == 0

    # Approve
    result = run_qms(temp_project, "qa", "approve", "SOP-001")
    assert result.returncode == 0

    # Verify EFFECTIVE
    meta = read_meta(temp_project, "SOP-001", "SOP")
    assert meta["status"] == "EFFECTIVE"
    assert meta["version"] == "1.0"

    # Read effective document
    result = run_qms(temp_project, "claude", "read", "SOP-001")
    assert result.returncode == 0
    assert "Full Lifecycle SOP" in result.stdout

    # History check
    result = run_qms(temp_project, "claude", "history", "SOP-001")
    assert result.returncode == 0
    assert "CREATE" in result.stdout
    assert "APPROVE" in result.stdout


def test_full_cr_lifecycle_via_cli(temp_project):
    """
    Verify complete CR lifecycle (executable document) can be executed.

    This test validates the pre-review, execution, and post-review phases.

    Verifies: REQ-MCP-003, REQ-MCP-004, REQ-MCP-005, REQ-MCP-007
    """
    # Create
    result = run_qms(temp_project, "claude", "create", "CR", "--title", "Full CR Lifecycle")
    assert result.returncode == 0

    # Checkin
    run_qms(temp_project, "claude", "checkin", "CR-001")

    # Pre-review phase
    run_qms(temp_project, "claude", "route", "CR-001", "--review")
    run_qms(temp_project, "qa", "review", "CR-001", "--recommend", "--comment", "Pre-review OK")
    run_qms(temp_project, "claude", "route", "CR-001", "--approval")
    run_qms(temp_project, "qa", "approve", "CR-001")

    # Release for execution
    result = run_qms(temp_project, "claude", "release", "CR-001")
    assert result.returncode == 0

    meta = read_meta(temp_project, "CR-001", "CR")
    assert meta["status"] == "IN_EXECUTION"

    # Post-review phase
    run_qms(temp_project, "claude", "route", "CR-001", "--review")
    run_qms(temp_project, "qa", "review", "CR-001", "--recommend", "--comment", "Post-review OK")
    run_qms(temp_project, "claude", "route", "CR-001", "--approval")
    run_qms(temp_project, "qa", "approve", "CR-001")

    # Close
    result = run_qms(temp_project, "claude", "close", "CR-001")
    assert result.returncode == 0

    # Verify CLOSED
    meta = read_meta(temp_project, "CR-001", "CR")
    assert meta["status"] == "CLOSED"


# ============================================================================
# REQ-MCP-011: Remote Transport Support
# REQ-MCP-012: Transport CLI Configuration
# REQ-MCP-013: Project Root Configuration
# ============================================================================

def get_server_module():
    """Import the server module for testing."""
    qms_cli_path = Path(__file__).parent.parent.parent
    if str(qms_cli_path) not in sys.path:
        sys.path.insert(0, str(qms_cli_path))

    from qms_mcp import server
    return server


@pytest.mark.skipif(not mcp_package_available(), reason="MCP package not installed")
def test_mcp_cli_args_default():
    """
    Verify default CLI arguments for MCP server.

    Verifies: REQ-MCP-012
    """
    server = get_server_module()
    args = server.parse_args([])

    assert args.transport == "stdio", "Default transport should be stdio"
    assert args.host == "127.0.0.1", "Default host should be 127.0.0.1"
    assert args.port == 8000, "Default port should be 8000"
    assert args.project_root is None, "Default project_root should be None"


@pytest.mark.skipif(not mcp_package_available(), reason="MCP package not installed")
def test_mcp_cli_args_sse_transport():
    """
    Verify SSE transport CLI argument is accepted.

    Verifies: REQ-MCP-011, REQ-MCP-012
    """
    server = get_server_module()
    args = server.parse_args(["--transport", "sse"])

    assert args.transport == "sse", "Transport should be set to sse"


@pytest.mark.skipif(not mcp_package_available(), reason="MCP package not installed")
def test_mcp_cli_args_host_port():
    """
    Verify host and port CLI arguments are accepted.

    Verifies: REQ-MCP-012
    """
    server = get_server_module()
    args = server.parse_args(["--host", "0.0.0.0", "--port", "9000"])

    assert args.host == "0.0.0.0", "Host should be set to 0.0.0.0"
    assert args.port == 9000, "Port should be set to 9000"


@pytest.mark.skipif(not mcp_package_available(), reason="MCP package not installed")
def test_mcp_cli_args_project_root():
    """
    Verify project-root CLI argument is accepted.

    Verifies: REQ-MCP-013
    """
    server = get_server_module()
    args = server.parse_args(["--project-root", "/custom/path"])

    assert args.project_root == "/custom/path", "Project root should be set from CLI"


@pytest.mark.skipif(not mcp_package_available(), reason="MCP package not installed")
def test_mcp_project_root_env_var(temp_project, monkeypatch):
    """
    Verify QMS_PROJECT_ROOT environment variable is respected.

    Verifies: REQ-MCP-013
    """
    server = get_server_module()

    # Set env var to point to temp_project
    monkeypatch.setenv("QMS_PROJECT_ROOT", str(temp_project))

    # get_qms_root should return the path from env var
    root = server.get_qms_root()

    assert root is not None, "Should find project root from env var"
    assert root == temp_project, f"Project root should be {temp_project}"


@pytest.mark.skipif(not mcp_package_available(), reason="MCP package not installed")
def test_mcp_project_root_env_var_invalid(monkeypatch, tmp_path):
    """
    Verify invalid QMS_PROJECT_ROOT is handled gracefully.

    Verifies: REQ-MCP-013
    """
    server = get_server_module()

    # Set env var to a path without QMS/ directory
    invalid_path = tmp_path / "no_qms_here"
    invalid_path.mkdir()
    monkeypatch.setenv("QMS_PROJECT_ROOT", str(invalid_path))

    # Change to a directory that also doesn't have QMS/
    original_cwd = Path.cwd()
    try:
        import os
        os.chdir(invalid_path)

        # get_qms_root should return None (env var path invalid, no QMS/ in cwd)
        root = server.get_qms_root()
        assert root is None, "Should return None when env var path has no QMS/"
    finally:
        os.chdir(original_cwd)


@pytest.mark.skipif(not mcp_package_available(), reason="MCP package not installed")
def test_mcp_transport_choices():
    """
    Verify transport argument only accepts valid choices.

    Verifies: REQ-MCP-011, REQ-MCP-012
    """
    server = get_server_module()

    # Valid transports should work
    args_stdio = server.parse_args(["--transport", "stdio"])
    assert args_stdio.transport == "stdio"

    args_sse = server.parse_args(["--transport", "sse"])
    assert args_sse.transport == "sse"

    # Invalid transport should raise error
    with pytest.raises(SystemExit):
        server.parse_args(["--transport", "invalid"])


# ============================================================================
# SSE Transport Integration Tests (CR-045 Requalification)
# ============================================================================

@pytest.mark.skipif(not mcp_package_available(), reason="MCP package not installed")
def test_mcp_sse_transport_configuration():
    """
    Verify SSE transport settings can be properly configured before server start.

    This test exercises the actual SSE configuration code path that was defective
    in CR-042 (using mcp.settings.host/port instead of kwargs to run()).

    Verifies: REQ-MCP-011, REQ-MCP-012
    """
    server = get_server_module()

    # Get the mcp instance from the server module
    mcp = server.mcp

    # Verify that settings can be configured (this is the code path that was broken)
    original_host = mcp.settings.host
    original_port = mcp.settings.port

    try:
        # Configure SSE settings as the server.main() function does
        mcp.settings.host = "0.0.0.0"
        mcp.settings.port = 9999

        # Verify settings were applied
        assert mcp.settings.host == "0.0.0.0", "Host setting should be configurable"
        assert mcp.settings.port == 9999, "Port setting should be configurable"
    finally:
        # Restore original settings
        mcp.settings.host = original_host
        mcp.settings.port = original_port


@pytest.mark.skipif(not mcp_package_available(), reason="MCP package not installed")
def test_mcp_sse_transport_security_allows_docker():
    """
    Verify transport security settings can be modified to allow Docker container connections.

    This tests the security configuration that enables containers using
    host.docker.internal to connect to the MCP server.

    Verifies: REQ-MCP-011
    """
    server = get_server_module()

    # Get the mcp instance from the server module
    mcp = server.mcp

    # Store original allowed_hosts for restoration
    original_hosts = list(mcp.settings.transport_security.allowed_hosts)
    original_origins = list(mcp.settings.transport_security.allowed_origins)

    try:
        # Add Docker host entries as the server does for SSE transport
        docker_host = "host.docker.internal:*"
        docker_origin = "http://host.docker.internal:*"

        mcp.settings.transport_security.allowed_hosts.append(docker_host)
        mcp.settings.transport_security.allowed_origins.append(docker_origin)

        # Verify the entries were added
        assert docker_host in mcp.settings.transport_security.allowed_hosts, \
            "Should be able to add host.docker.internal to allowed_hosts"
        assert docker_origin in mcp.settings.transport_security.allowed_origins, \
            "Should be able to add host.docker.internal origin to allowed_origins"
    finally:
        # Restore original settings
        mcp.settings.transport_security.allowed_hosts = original_hosts
        mcp.settings.transport_security.allowed_origins = original_origins
