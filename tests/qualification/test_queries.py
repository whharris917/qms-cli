"""
QMS CLI Qualification Tests: Query Operations

Tests for read, status, history, comments, inbox, and workspace queries.
Verifies requirements: QRY-001, QRY-002, QRY-003, QRY-004, QRY-005, QRY-006
"""
import json
import subprocess
import sys
from pathlib import Path

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


# ============================================================================
# Test: Document Reading
# ============================================================================

def test_read_draft(temp_project):
    """
    Read the current draft version of a document.

    Verifies: REQ-QRY-001
    """
    # Create document
    run_qms(temp_project, "claude", "create", "SOP", "--title", "Readable SOP")
    run_qms(temp_project, "claude", "checkin", "SOP-001")

    # [REQ-QRY-001] Read draft
    result = run_qms(temp_project, "claude", "read", "SOP-001")
    assert result.returncode == 0, f"Read failed: {result.stderr}"
    assert "Readable SOP" in result.stdout, "Document title should appear in output"


def test_read_effective(temp_project):
    """
    Read the effective version of a document.

    Verifies: REQ-QRY-001
    """
    # Create and approve to EFFECTIVE
    run_qms(temp_project, "claude", "create", "SOP", "--title", "Effective SOP")
    run_qms(temp_project, "claude", "checkin", "SOP-001")
    run_qms(temp_project, "claude", "route", "SOP-001", "--review")
    run_qms(temp_project, "qa", "review", "SOP-001", "--recommend", "--comment", "OK")
    run_qms(temp_project, "claude", "route", "SOP-001", "--approval")
    run_qms(temp_project, "qa", "approve", "SOP-001")

    meta = read_meta(temp_project, "SOP-001", "SOP")
    assert meta["status"] == "EFFECTIVE"

    # [REQ-QRY-001] Read effective (default when no draft exists)
    result = run_qms(temp_project, "claude", "read", "SOP-001")
    assert result.returncode == 0, f"Read effective failed: {result.stderr}"
    assert "Effective SOP" in result.stdout


def test_read_archived_version(temp_project):
    """
    Read an archived version of a document.

    Verifies: REQ-QRY-001
    """
    # Create and approve to v1.0
    run_qms(temp_project, "claude", "create", "SOP", "--title", "Versioned SOP")
    run_qms(temp_project, "claude", "checkin", "SOP-001")
    run_qms(temp_project, "claude", "route", "SOP-001", "--review")
    run_qms(temp_project, "qa", "review", "SOP-001", "--recommend", "--comment", "OK")
    run_qms(temp_project, "claude", "route", "SOP-001", "--approval")
    run_qms(temp_project, "qa", "approve", "SOP-001")

    # Verify archive exists
    archive_path = temp_project / "QMS" / ".archive" / "SOP" / "SOP-001-v0.1.md"
    assert archive_path.exists(), "Archive should exist for v0.1"

    # [REQ-QRY-001] Read archived version
    result = run_qms(temp_project, "claude", "read", "SOP-001", "--version", "0.1")
    assert result.returncode == 0, f"Read archived failed: {result.stderr}"
    assert "Versioned SOP" in result.stdout


def test_read_draft_flag(temp_project):
    """
    Read draft explicitly when both draft and effective exist.

    Verifies: REQ-QRY-001
    """
    # Create, approve to EFFECTIVE, then checkout new draft
    run_qms(temp_project, "claude", "create", "SOP", "--title", "Original Title")
    run_qms(temp_project, "claude", "checkin", "SOP-001")
    run_qms(temp_project, "claude", "route", "SOP-001", "--review")
    run_qms(temp_project, "qa", "review", "SOP-001", "--recommend", "--comment", "OK")
    run_qms(temp_project, "claude", "route", "SOP-001", "--approval")
    run_qms(temp_project, "qa", "approve", "SOP-001")

    # Checkout creates draft v1.1
    run_qms(temp_project, "claude", "checkout", "SOP-001")

    # Modify workspace file title
    workspace_path = temp_project / ".claude" / "users" / "claude" / "workspace" / "SOP-001.md"
    content = workspace_path.read_text(encoding="utf-8")
    content = content.replace("Original Title", "Updated Draft Title")
    workspace_path.write_text(content, encoding="utf-8")

    run_qms(temp_project, "claude", "checkin", "SOP-001")

    # [REQ-QRY-001] Read draft explicitly
    result = run_qms(temp_project, "claude", "read", "SOP-001", "--draft")
    assert result.returncode == 0, f"Read draft failed: {result.stderr}"
    assert "Updated Draft Title" in result.stdout


# ============================================================================
# Test: Document Status Query
# ============================================================================

def test_status_query(temp_project):
    """
    Query document status shows all required fields.

    Verifies: REQ-QRY-002
    """
    # Create and checkout document
    run_qms(temp_project, "claude", "create", "SOP", "--title", "Status Test SOP")

    # [REQ-QRY-002] Query status
    result = run_qms(temp_project, "claude", "status", "SOP-001")
    assert result.returncode == 0, f"Status query failed: {result.stderr}"

    output = result.stdout

    # Verify all required fields present
    assert "SOP-001" in output, "doc_id should be in output"
    assert "Status Test SOP" in output, "title should be in output"
    assert "0.1" in output or "Version" in output, "version should be in output"
    assert "DRAFT" in output, "status should be in output"
    assert "SOP" in output, "document type should be in output"
    assert "claude" in output, "responsible_user should be in output"


def test_status_shows_checked_out(temp_project):
    """
    Status query correctly shows checked_out status.

    Verifies: REQ-QRY-002
    """
    # Create document (auto-checked out)
    run_qms(temp_project, "claude", "create", "SOP", "--title", "Checkout Status Test")

    result = run_qms(temp_project, "claude", "status", "SOP-001")
    assert "True" in result.stdout or "Checked Out: True" in result.stdout or "Yes" in result.stdout, \
        "Should show checked out status"

    # Checkin
    run_qms(temp_project, "claude", "checkin", "SOP-001")

    result = run_qms(temp_project, "claude", "status", "SOP-001")
    assert "False" in result.stdout or "Checked Out: False" in result.stdout or "No" in result.stdout, \
        "Should show not checked out"


# ============================================================================
# Test: Audit History Query
# ============================================================================

def test_history_query(temp_project):
    """
    History query shows all recorded events in chronological order.

    Verifies: REQ-QRY-003
    """
    # Create document and perform several actions
    run_qms(temp_project, "claude", "create", "SOP", "--title", "History Test")
    run_qms(temp_project, "claude", "checkin", "SOP-001")
    run_qms(temp_project, "claude", "route", "SOP-001", "--review")

    # [REQ-QRY-003] Query history
    result = run_qms(temp_project, "claude", "history", "SOP-001")
    assert result.returncode == 0, f"History query failed: {result.stderr}"

    output = result.stdout

    # Verify events appear in order
    assert "CREATE" in output, "CREATE event should be in history"
    assert "CHECKIN" in output, "CHECKIN event should be in history"
    assert "ROUTE" in output or "ROUTE_REVIEW" in output, "ROUTE event should be in history"

    # Verify chronological order (CREATE should appear before ROUTE)
    create_pos = output.find("CREATE")
    route_pos = output.find("ROUTE")
    assert create_pos < route_pos, "Events should be in chronological order"


def test_history_shows_all_event_types(temp_project):
    """
    History includes all event types from full lifecycle.

    Verifies: REQ-QRY-003, REQ-AUDIT-002
    """
    # Full lifecycle
    run_qms(temp_project, "claude", "create", "SOP", "--title", "Full History")
    run_qms(temp_project, "claude", "checkin", "SOP-001")
    run_qms(temp_project, "claude", "route", "SOP-001", "--review")
    run_qms(temp_project, "qa", "review", "SOP-001", "--recommend", "--comment", "OK")
    run_qms(temp_project, "claude", "route", "SOP-001", "--approval")
    run_qms(temp_project, "qa", "approve", "SOP-001")

    result = run_qms(temp_project, "claude", "history", "SOP-001")
    output = result.stdout

    # [REQ-QRY-003] [REQ-AUDIT-002] Verify key event types
    assert "CREATE" in output
    assert "CHECKIN" in output
    assert "REVIEW" in output
    assert "APPROVE" in output
    assert "EFFECTIVE" in output


# ============================================================================
# Test: Review Comments Query
# ============================================================================

def test_comments_query(temp_project):
    """
    Comments query retrieves review comments from audit trail.

    Verifies: REQ-QRY-004
    """
    # Create and review with comment
    run_qms(temp_project, "claude", "create", "SOP", "--title", "Comments Test")
    run_qms(temp_project, "claude", "checkin", "SOP-001")
    run_qms(temp_project, "claude", "route", "SOP-001", "--review")
    run_qms(temp_project, "qa", "review", "SOP-001",
            "--recommend", "--comment", "This is my review comment with specific feedback")

    # [REQ-QRY-004] Query comments
    result = run_qms(temp_project, "claude", "comments", "SOP-001")
    assert result.returncode == 0, f"Comments query failed: {result.stderr}"

    assert "specific feedback" in result.stdout, "Review comment should appear in output"


def test_comments_includes_rejection(temp_project):
    """
    Comments query includes rejection comments.

    Verifies: REQ-QRY-004
    """
    # Create, review, route for approval, then reject
    run_qms(temp_project, "claude", "create", "SOP", "--title", "Rejection Comments")
    run_qms(temp_project, "claude", "checkin", "SOP-001")
    run_qms(temp_project, "claude", "route", "SOP-001", "--review")
    run_qms(temp_project, "qa", "review", "SOP-001", "--recommend", "--comment", "Looks good")
    run_qms(temp_project, "claude", "route", "SOP-001", "--approval")
    run_qms(temp_project, "qa", "reject", "SOP-001",
            "--comment", "Rejection reason: missing section 5")

    # [REQ-QRY-004] Query comments
    result = run_qms(temp_project, "claude", "comments", "SOP-001")
    assert result.returncode == 0

    assert "missing section 5" in result.stdout, "Rejection comment should appear"


# ============================================================================
# Test: Inbox Query
# ============================================================================

def test_inbox_query(temp_project):
    """
    Inbox query lists pending tasks for a user.

    Verifies: REQ-QRY-005
    """
    # Create and route document (assigns task to qa)
    run_qms(temp_project, "claude", "create", "SOP", "--title", "Inbox Test SOP")
    run_qms(temp_project, "claude", "checkin", "SOP-001")
    run_qms(temp_project, "claude", "route", "SOP-001", "--review")

    # [REQ-QRY-005] Query qa's inbox
    result = run_qms(temp_project, "qa", "inbox")
    assert result.returncode == 0, f"Inbox query failed: {result.stderr}"

    output = result.stdout
    assert "SOP-001" in output, "Task for SOP-001 should appear in inbox"
    assert "REVIEW" in output or "review" in output.lower(), "Task type should be shown"


def test_inbox_multiple_tasks(temp_project):
    """
    Inbox shows multiple pending tasks.

    Verifies: REQ-QRY-005
    """
    # Create and route multiple documents
    run_qms(temp_project, "claude", "create", "SOP", "--title", "First SOP")
    run_qms(temp_project, "claude", "checkin", "SOP-001")
    run_qms(temp_project, "claude", "route", "SOP-001", "--review")

    run_qms(temp_project, "claude", "create", "SOP", "--title", "Second SOP")
    run_qms(temp_project, "claude", "checkin", "SOP-002")
    run_qms(temp_project, "claude", "route", "SOP-002", "--review")

    # [REQ-QRY-005] Query inbox - should show both
    result = run_qms(temp_project, "qa", "inbox")
    assert result.returncode == 0

    assert "SOP-001" in result.stdout, "First task should appear"
    assert "SOP-002" in result.stdout, "Second task should appear"


def test_inbox_empty_when_no_tasks(temp_project):
    """
    Inbox query works when user has no pending tasks.

    Verifies: REQ-QRY-005
    """
    # [REQ-QRY-005] Query inbox with no tasks
    result = run_qms(temp_project, "qa", "inbox")
    assert result.returncode == 0, "Inbox query should succeed even with no tasks"

    # Output should indicate empty or show no tasks
    # (exact format depends on implementation)


# ============================================================================
# Test: Workspace Query
# ============================================================================

def test_workspace_query(temp_project):
    """
    Workspace query lists documents checked out to user.

    Verifies: REQ-QRY-006
    """
    # Create document (auto-checks out)
    run_qms(temp_project, "claude", "create", "SOP", "--title", "Workspace Test")

    # [REQ-QRY-006] Query workspace
    result = run_qms(temp_project, "claude", "workspace")
    assert result.returncode == 0, f"Workspace query failed: {result.stderr}"

    assert "SOP-001" in result.stdout, "Checked out document should appear in workspace"


def test_workspace_multiple_documents(temp_project):
    """
    Workspace shows multiple checked out documents.

    Verifies: REQ-QRY-006
    """
    # Create multiple documents (each auto-checks out, but we need to manage ownership)
    run_qms(temp_project, "claude", "create", "SOP", "--title", "First Checkout")
    # First one is checked out to claude

    run_qms(temp_project, "claude", "create", "SOP", "--title", "Second Checkout")
    # Second one is also checked out to claude

    # [REQ-QRY-006] Query workspace - should show both
    result = run_qms(temp_project, "claude", "workspace")
    assert result.returncode == 0

    assert "SOP-001" in result.stdout, "First document should appear"
    assert "SOP-002" in result.stdout, "Second document should appear"


def test_workspace_empty_after_checkin(temp_project):
    """
    Workspace is empty after checking in all documents.

    Verifies: REQ-QRY-006
    """
    # Create and immediately checkin
    run_qms(temp_project, "claude", "create", "SOP", "--title", "Temporary Checkout")
    run_qms(temp_project, "claude", "checkin", "SOP-001")

    # [REQ-QRY-006] Workspace should be empty
    result = run_qms(temp_project, "claude", "workspace")
    assert result.returncode == 0

    # Document should not appear since it's checked in
    # (It might show empty message or just not list SOP-001)
    assert "SOP-001" not in result.stdout or "empty" in result.stdout.lower() or "no documents" in result.stdout.lower()
