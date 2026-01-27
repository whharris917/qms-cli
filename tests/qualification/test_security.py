"""
QMS CLI Qualification Tests: Security and Access Control

Tests for user authorization and access control.
Verifies requirements: SEC-001, SEC-002, SEC-003, SEC-004, SEC-005, SEC-006
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
# Test: User Group Classification
# ============================================================================

def test_user_group_classification(temp_project):
    """
    Verify users are classified into correct groups with appropriate permissions.

    Verifies: REQ-SEC-001
    """
    # [REQ-SEC-001] Initiators (claude, lead) can create documents
    result = run_qms(temp_project, "claude", "create", "SOP", "--title", "Test by Claude")
    assert result.returncode == 0, "Initiator claude should be able to create"

    result = run_qms(temp_project, "lead", "create", "SOP", "--title", "Test by Lead")
    assert result.returncode == 0, "Initiator lead should be able to create"

    # [REQ-SEC-001] QA can assign reviewers
    run_qms(temp_project, "claude", "checkin", "SOP-001")
    run_qms(temp_project, "claude", "route", "SOP-001", "--review")
    result = run_qms(temp_project, "qa", "assign", "SOP-001", "--assignees", "lead")
    assert result.returncode == 0, "QA should be able to assign reviewers"

    # [REQ-SEC-001] Reviewers can review when assigned
    result = run_qms(temp_project, "lead", "review", "SOP-001",
                     "--recommend", "--comment", "Looks good")
    assert result.returncode == 0, "Assigned reviewer should be able to review"


# ============================================================================
# Test: Group-Based Action Authorization
# ============================================================================

def test_unauthorized_create(temp_project):
    """
    Non-initiators cannot create documents.

    Verifies: REQ-SEC-002
    """
    # [REQ-SEC-002] TU agents (reviewers) cannot create
    result = run_qms(temp_project, "tu_ui", "create", "SOP", "--title", "Unauthorized")
    assert result.returncode != 0, "Reviewer tu_ui should not be able to create"

    # Verify no document was created
    assert not (temp_project / "QMS" / "SOP" / "SOP-001-draft.md").exists()


def test_unauthorized_assign(temp_project):
    """
    Non-QA users cannot assign reviewers.

    Verifies: REQ-SEC-002
    """
    # Setup: Create and route a document
    run_qms(temp_project, "claude", "create", "SOP", "--title", "Test Assign")
    run_qms(temp_project, "claude", "checkin", "SOP-001")
    run_qms(temp_project, "claude", "route", "SOP-001", "--review")

    # [REQ-SEC-002] Initiators cannot assign
    result = run_qms(temp_project, "claude", "assign", "SOP-001", "--reviewers", "lead")
    assert result.returncode != 0, "Initiator claude should not be able to assign"

    # [REQ-SEC-002] Reviewers cannot assign
    result = run_qms(temp_project, "tu_ui", "assign", "SOP-001", "--reviewers", "lead")
    assert result.returncode != 0, "Reviewer tu_ui should not be able to assign"


def test_fix_authorization(temp_project):
    """
    Only administrators can use the fix command.

    Verifies: REQ-SEC-002 (fix command available to administrator group)
    """
    # Setup: Create an effective document
    run_qms(temp_project, "claude", "create", "SOP", "--title", "Test Fix")
    run_qms(temp_project, "claude", "checkin", "SOP-001")
    run_qms(temp_project, "claude", "route", "SOP-001", "--review")
    run_qms(temp_project, "qa", "review", "SOP-001", "--recommend", "--comment", "OK")
    run_qms(temp_project, "claude", "route", "SOP-001", "--approval")
    run_qms(temp_project, "qa", "approve", "SOP-001")

    # Now we have an EFFECTIVE document

    # [REQ-SEC-002] Administrator 'lead' can fix (hardcoded admin)
    result = run_qms(temp_project, "lead", "fix", "SOP-001")
    assert result.returncode == 0, "Administrator lead should be able to fix"

    # [REQ-SEC-002] Administrator 'claude' can fix (hardcoded admin)
    result = run_qms(temp_project, "claude", "fix", "SOP-001")
    assert result.returncode == 0, "Administrator claude should be able to fix"

    # [REQ-SEC-002] Quality user 'qa' cannot fix (not administrator)
    result = run_qms(temp_project, "qa", "fix", "SOP-001")
    assert result.returncode != 0, "Quality user qa should not be able to fix"
    assert "administrator" in result.stderr.lower(), "Error should mention administrator"

    # [REQ-SEC-002] Reviewer 'tu_ui' cannot fix (not administrator)
    result = run_qms(temp_project, "tu_ui", "fix", "SOP-001")
    assert result.returncode != 0, "Reviewer tu_ui should not be able to fix"


# ============================================================================
# Test: Owner-Only Restrictions
# ============================================================================

def test_owner_only_checkin(temp_project):
    """
    Only the document owner can checkin.

    Verifies: REQ-SEC-003
    """
    # Create document as claude
    run_qms(temp_project, "claude", "create", "SOP", "--title", "Owner Test")

    # Document is checked out to claude
    meta = read_meta(temp_project, "SOP-001", "SOP")
    assert meta["responsible_user"] == "claude"
    assert meta["checked_out"] == True

    # [REQ-SEC-003] Non-owner cannot checkin
    result = run_qms(temp_project, "lead", "checkin", "SOP-001")
    assert result.returncode != 0, "Non-owner should not be able to checkin"

    # [REQ-SEC-003] Owner can checkin
    result = run_qms(temp_project, "claude", "checkin", "SOP-001")
    assert result.returncode == 0, "Owner should be able to checkin"


def test_owner_only_route(temp_project):
    """
    Only the document owner can route for review/approval.

    Verifies: REQ-SEC-003
    """
    # Create and checkin as claude
    run_qms(temp_project, "claude", "create", "SOP", "--title", "Route Test")
    run_qms(temp_project, "claude", "checkin", "SOP-001")

    # [REQ-SEC-003] Non-owner cannot route
    result = run_qms(temp_project, "lead", "route", "SOP-001", "--review")
    assert result.returncode != 0, "Non-owner should not be able to route"

    # [REQ-SEC-003] Owner can route
    result = run_qms(temp_project, "claude", "route", "SOP-001", "--review")
    assert result.returncode == 0, "Owner should be able to route"


# ============================================================================
# Test: Assignment-Based Review Access
# ============================================================================

def test_unassigned_cannot_review(temp_project):
    """
    Users not in pending_assignees cannot submit reviews.

    Verifies: REQ-SEC-004
    """
    # Create and route for review (auto-assigns qa)
    run_qms(temp_project, "claude", "create", "SOP", "--title", "Review Access Test")
    run_qms(temp_project, "claude", "checkin", "SOP-001")
    run_qms(temp_project, "claude", "route", "SOP-001", "--review")

    meta = read_meta(temp_project, "SOP-001", "SOP")
    assert "qa" in meta["pending_assignees"]

    # [REQ-SEC-004] Unassigned user cannot review
    result = run_qms(temp_project, "tu_ui", "review", "SOP-001",
                     "--recommend", "--comment", "Unauthorized review")
    assert result.returncode != 0, "Unassigned user should not be able to review"

    # [REQ-SEC-004] Assigned user can review
    result = run_qms(temp_project, "qa", "review", "SOP-001",
                     "--recommend", "--comment", "Authorized review")
    assert result.returncode == 0, "Assigned user should be able to review"


def test_unassigned_cannot_approve(temp_project):
    """
    Users not in pending_assignees cannot approve.

    Verifies: REQ-SEC-004
    """
    # Create, review, and route for approval
    run_qms(temp_project, "claude", "create", "SOP", "--title", "Approve Access Test")
    run_qms(temp_project, "claude", "checkin", "SOP-001")
    run_qms(temp_project, "claude", "route", "SOP-001", "--review")
    run_qms(temp_project, "qa", "review", "SOP-001", "--recommend", "--comment", "OK")
    run_qms(temp_project, "claude", "route", "SOP-001", "--approval")

    meta = read_meta(temp_project, "SOP-001", "SOP")
    assert "qa" in meta["pending_assignees"]

    # [REQ-SEC-004] Unassigned user cannot approve
    result = run_qms(temp_project, "tu_ui", "approve", "SOP-001")
    assert result.returncode != 0, "Unassigned user should not be able to approve"

    # [REQ-SEC-004] Assigned user can approve
    result = run_qms(temp_project, "qa", "approve", "SOP-001")
    assert result.returncode == 0, "Assigned user should be able to approve"


# ============================================================================
# Test: Rejection Access
# ============================================================================

def test_rejection_access(temp_project):
    """
    Rejection follows same authorization rules as approve.

    Verifies: REQ-SEC-005
    """
    # Create and route for approval
    run_qms(temp_project, "claude", "create", "SOP", "--title", "Reject Access Test")
    run_qms(temp_project, "claude", "checkin", "SOP-001")
    run_qms(temp_project, "claude", "route", "SOP-001", "--review")
    run_qms(temp_project, "qa", "review", "SOP-001", "--recommend", "--comment", "OK")
    run_qms(temp_project, "claude", "route", "SOP-001", "--approval")

    meta = read_meta(temp_project, "SOP-001", "SOP")
    assert "qa" in meta["pending_assignees"]

    # [REQ-SEC-005] Unassigned user cannot reject
    result = run_qms(temp_project, "tu_ui", "reject", "SOP-001",
                     "--comment", "Unauthorized rejection")
    assert result.returncode != 0, "Unassigned user should not be able to reject"

    # [REQ-SEC-005] Assigned user can reject
    result = run_qms(temp_project, "qa", "reject", "SOP-001",
                     "--comment", "Authorized rejection")
    assert result.returncode == 0, "Assigned user should be able to reject"


# ============================================================================
# Test: Unknown User Rejection
# ============================================================================

def test_unknown_user_rejection(temp_project):
    """
    Commands with unknown user identifiers are rejected.

    Verifies: REQ-SEC-006
    """
    # [REQ-SEC-006] Unknown user cannot execute any command
    result = run_qms(temp_project, "nonexistent_user", "create", "SOP",
                     "--title", "Should Fail")
    assert result.returncode != 0, "Unknown user should be rejected"

    # Verify no state was modified
    assert not (temp_project / "QMS" / "SOP" / "SOP-001-draft.md").exists()

    # Try another command type
    result = run_qms(temp_project, "fake_qa", "inbox")
    assert result.returncode != 0, "Unknown user should be rejected for all commands"


# ============================================================================
# Test: Assignment Validation
# ============================================================================

def test_assignment_validation_review(temp_project):
    """
    Assignment validates that assignees are authorized for review workflows.

    Verifies: REQ-SEC-007
    """
    # Create and route for review
    run_qms(temp_project, "claude", "create", "SOP", "--title", "Assignment Validation Test")
    run_qms(temp_project, "claude", "checkin", "SOP-001")
    run_qms(temp_project, "claude", "route", "SOP-001", "--review")

    # [REQ-SEC-007] Assign valid reviewer (tu_ui is in reviewer group)
    result = run_qms(temp_project, "qa", "assign", "SOP-001", "--assignees", "tu_ui")
    assert result.returncode == 0, "Valid reviewer should be assignable"

    # Verify tu_ui is in pending_assignees
    meta = read_meta(temp_project, "SOP-001", "SOP")
    assert "tu_ui" in meta["pending_assignees"]


def test_assignment_validation_approval(temp_project):
    """
    Assignment for approval validates assignees are in quality or reviewer groups.

    Verifies: REQ-SEC-007
    """
    # Create and get to IN_APPROVAL
    run_qms(temp_project, "claude", "create", "SOP", "--title", "Approval Assignment Test")
    run_qms(temp_project, "claude", "checkin", "SOP-001")
    run_qms(temp_project, "claude", "route", "SOP-001", "--review")
    run_qms(temp_project, "qa", "review", "SOP-001", "--recommend", "--comment", "OK")
    run_qms(temp_project, "claude", "route", "SOP-001", "--approval")

    meta = read_meta(temp_project, "SOP-001", "SOP")
    assert meta["status"] == "IN_APPROVAL"

    # [REQ-SEC-007] Assign valid approver (tu_scene is in reviewer group, can approve)
    result = run_qms(temp_project, "qa", "assign", "SOP-001", "--assignees", "tu_scene")
    assert result.returncode == 0, "Valid approver should be assignable"


# ============================================================================
# Test: Workspace/Inbox Isolation
# ============================================================================

def test_workspace_isolation(temp_project):
    """
    Users cannot access other users' workspaces.

    Verifies: REQ-SEC-008
    """
    # Create document as claude (auto-checks out to claude's workspace)
    run_qms(temp_project, "claude", "create", "SOP", "--title", "Workspace Isolation Test")

    # Verify document is in claude's workspace
    workspace_path = temp_project / ".claude" / "users" / "claude" / "workspace" / "SOP-001.md"
    assert workspace_path.exists(), "Document should be in claude's workspace"

    # [REQ-SEC-008] qa should not be able to access claude's workspace
    result = run_qms(temp_project, "qa", "workspace")
    assert "SOP-001" not in result.stdout, "qa should not see claude's workspace documents"


def test_inbox_isolation(temp_project):
    """
    Users cannot access other users' inboxes.

    Verifies: REQ-SEC-008
    """
    # Create and route for review (assigns to qa)
    run_qms(temp_project, "claude", "create", "SOP", "--title", "Inbox Isolation Test")
    run_qms(temp_project, "claude", "checkin", "SOP-001")
    run_qms(temp_project, "claude", "route", "SOP-001", "--review")

    # Verify task is in qa's inbox
    result = run_qms(temp_project, "qa", "inbox")
    assert "SOP-001" in result.stdout, "Task should be in qa's inbox"

    # [REQ-SEC-008] tu_ui should not see qa's tasks
    result = run_qms(temp_project, "tu_ui", "inbox")
    assert "SOP-001" not in result.stdout, "tu_ui should not see qa's inbox tasks"


# ============================================================================
# Test: Group-Based Authorization - Additional Actions
# ============================================================================

def test_unauthorized_route(temp_project):
    """
    Non-initiators (reviewers) cannot route documents they don't own.

    Verifies: REQ-SEC-002
    """
    # Create document as claude
    run_qms(temp_project, "claude", "create", "SOP", "--title", "Route Auth Test")
    run_qms(temp_project, "claude", "checkin", "SOP-001")

    # [REQ-SEC-002] Reviewer cannot route (even aside from not being owner)
    result = run_qms(temp_project, "tu_ui", "route", "SOP-001", "--review")
    assert result.returncode != 0, "Reviewer should not be able to route"


def test_unauthorized_release(temp_project):
    """
    Non-initiators cannot release executable documents.

    Verifies: REQ-SEC-002
    """
    # Create CR and get to PRE_APPROVED
    run_qms(temp_project, "claude", "create", "CR", "--title", "Release Auth Test")
    run_qms(temp_project, "claude", "checkin", "CR-001")
    run_qms(temp_project, "claude", "route", "CR-001", "--review")
    run_qms(temp_project, "qa", "review", "CR-001", "--recommend", "--comment", "OK")
    run_qms(temp_project, "claude", "route", "CR-001", "--approval")
    run_qms(temp_project, "qa", "approve", "CR-001")

    meta = read_meta(temp_project, "CR-001", "CR")
    assert meta["status"] == "PRE_APPROVED"

    # [REQ-SEC-002] Reviewer cannot release
    result = run_qms(temp_project, "tu_ui", "release", "CR-001")
    assert result.returncode != 0, "Reviewer should not be able to release"


def test_unauthorized_revert(temp_project):
    """
    Non-initiators cannot revert executable documents.

    Verifies: REQ-SEC-002
    """
    # Create CR and get to POST_REVIEWED (revert requires POST_REVIEWED)
    run_qms(temp_project, "claude", "create", "CR", "--title", "Revert Auth Test")
    run_qms(temp_project, "claude", "checkin", "CR-001")
    run_qms(temp_project, "claude", "route", "CR-001", "--review")
    run_qms(temp_project, "qa", "review", "CR-001", "--recommend", "--comment", "OK")
    run_qms(temp_project, "claude", "route", "CR-001", "--approval")
    run_qms(temp_project, "qa", "approve", "CR-001")
    run_qms(temp_project, "claude", "release", "CR-001")
    run_qms(temp_project, "claude", "checkout", "CR-001")
    run_qms(temp_project, "claude", "checkin", "CR-001")
    run_qms(temp_project, "claude", "route", "CR-001", "--review")
    run_qms(temp_project, "qa", "review", "CR-001", "--recommend", "--comment", "OK")

    meta = read_meta(temp_project, "CR-001", "CR")
    assert meta["status"] == "POST_REVIEWED"

    # [REQ-SEC-002] Reviewer cannot revert
    result = run_qms(temp_project, "tu_ui", "revert", "CR-001", "--reason", "Test revert")
    assert result.returncode != 0, "Reviewer should not be able to revert"


def test_unauthorized_close(temp_project):
    """
    Non-initiators cannot close executable documents.

    Verifies: REQ-SEC-002
    """
    # Create CR and get to POST_APPROVED
    run_qms(temp_project, "claude", "create", "CR", "--title", "Close Auth Test")
    run_qms(temp_project, "claude", "checkin", "CR-001")
    run_qms(temp_project, "claude", "route", "CR-001", "--review")
    run_qms(temp_project, "qa", "review", "CR-001", "--recommend", "--comment", "OK")
    run_qms(temp_project, "claude", "route", "CR-001", "--approval")
    run_qms(temp_project, "qa", "approve", "CR-001")
    run_qms(temp_project, "claude", "release", "CR-001")
    run_qms(temp_project, "claude", "checkout", "CR-001")
    run_qms(temp_project, "claude", "checkin", "CR-001")
    run_qms(temp_project, "claude", "route", "CR-001", "--review")
    run_qms(temp_project, "qa", "review", "CR-001", "--recommend", "--comment", "OK")
    run_qms(temp_project, "claude", "route", "CR-001", "--approval")
    run_qms(temp_project, "qa", "approve", "CR-001")

    meta = read_meta(temp_project, "CR-001", "CR")
    assert meta["status"] == "POST_APPROVED"

    # [REQ-SEC-002] Reviewer cannot close
    result = run_qms(temp_project, "tu_ui", "close", "CR-001")
    assert result.returncode != 0, "Reviewer should not be able to close"


# ============================================================================
# Test: Owner-Only Revert
# ============================================================================

def test_owner_only_revert(temp_project):
    """
    Only the document owner can revert an executable document.

    Verifies: REQ-SEC-003
    """
    # Create CR and get to POST_REVIEWED (revert requires POST_REVIEWED status)
    run_qms(temp_project, "claude", "create", "CR", "--title", "Owner Revert Test")
    run_qms(temp_project, "claude", "checkin", "CR-001")
    run_qms(temp_project, "claude", "route", "CR-001", "--review")
    run_qms(temp_project, "qa", "review", "CR-001", "--recommend", "--comment", "OK")
    run_qms(temp_project, "claude", "route", "CR-001", "--approval")
    run_qms(temp_project, "qa", "approve", "CR-001")
    run_qms(temp_project, "claude", "release", "CR-001")
    # Get to POST_REVIEWED
    run_qms(temp_project, "claude", "checkout", "CR-001")
    run_qms(temp_project, "claude", "checkin", "CR-001")
    run_qms(temp_project, "claude", "route", "CR-001", "--review")
    run_qms(temp_project, "qa", "review", "CR-001", "--recommend", "--comment", "OK")

    meta = read_meta(temp_project, "CR-001", "CR")
    assert meta["status"] == "POST_REVIEWED"
    assert meta["responsible_user"] == "claude"

    # [REQ-SEC-003] Non-owner (lead, also initiator) cannot revert
    result = run_qms(temp_project, "lead", "revert", "CR-001", "--reason", "Test revert")
    assert result.returncode != 0, "Non-owner should not be able to revert"

    # Status should be unchanged
    meta = read_meta(temp_project, "CR-001", "CR")
    assert meta["status"] == "POST_REVIEWED"

    # Owner (claude) can revert
    result = run_qms(temp_project, "claude", "revert", "CR-001", "--reason", "Test revert")
    assert result.returncode == 0, f"Owner revert failed: {result.stderr}"

    meta = read_meta(temp_project, "CR-001", "CR")
    assert meta["status"] == "IN_EXECUTION"
