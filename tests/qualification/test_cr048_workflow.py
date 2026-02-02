"""
Qualification Tests for CR-048: Workflow Improvements

Tests for REQ-WF-016 through REQ-WF-021.
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
    # Combine stdout and stderr for easier assertion checking
    result.stdout = result.stdout + result.stderr
    return result


def read_meta(temp_project, doc_id, doc_type):
    """Read .meta JSON file for a document."""
    meta_path = temp_project / "QMS" / ".meta" / doc_type / f"{doc_id}.json"
    if not meta_path.exists():
        return None
    return json.loads(meta_path.read_text(encoding="utf-8"))


# ============================================================================
# REQ-WF-016: Pre-Release Revision
# ============================================================================

def test_checkout_from_pre_approved_reverts_to_draft(temp_project):
    """
    [REQ-WF-016] Checkout from PRE_APPROVED transitions to DRAFT.

    This allows scope revision through re-review before execution begins.
    """
    # Create CR and get to PRE_APPROVED
    run_qms(temp_project, "claude", "create", "CR", "--title", "Pre-Release Revision Test")
    run_qms(temp_project, "claude", "checkin", "CR-001")
    run_qms(temp_project, "claude", "route", "CR-001", "--review")
    run_qms(temp_project, "qa", "review", "CR-001", "--recommend", "--comment", "OK")
    run_qms(temp_project, "claude", "route", "CR-001", "--approval")
    run_qms(temp_project, "qa", "approve", "CR-001")

    meta = read_meta(temp_project, "CR-001", "CR")
    assert meta["status"] == "PRE_APPROVED"

    # [REQ-WF-016] Checkout from PRE_APPROVED
    result = run_qms(temp_project, "claude", "checkout", "CR-001")
    assert result.returncode == 0
    assert "DRAFT" in result.stdout or "Transitioned" in result.stdout

    # Verify status is now DRAFT
    meta = read_meta(temp_project, "CR-001", "CR")
    assert meta["status"] == "DRAFT", "PRE_APPROVED checkout should transition to DRAFT"

    # Verify review tracking fields cleared
    assert meta.get("pending_assignees", []) == []
    assert meta.get("review_outcomes", {}) == {}


# ============================================================================
# REQ-WF-017: Post-Review Continuation
# ============================================================================

def test_checkout_from_post_reviewed_returns_to_execution(temp_project):
    """
    [REQ-WF-017] Checkout from POST_REVIEWED transitions to IN_EXECUTION.

    This allows continued execution work without intermediate DRAFT state.
    """
    # Create CR and get through full lifecycle to POST_REVIEWED
    run_qms(temp_project, "claude", "create", "CR", "--title", "Post-Review Continuation Test")
    run_qms(temp_project, "claude", "checkin", "CR-001")
    run_qms(temp_project, "claude", "route", "CR-001", "--review")
    run_qms(temp_project, "qa", "review", "CR-001", "--recommend", "--comment", "OK")
    run_qms(temp_project, "claude", "route", "CR-001", "--approval")
    run_qms(temp_project, "qa", "approve", "CR-001")
    run_qms(temp_project, "claude", "release", "CR-001")

    # Edit and route for post-review
    run_qms(temp_project, "claude", "checkout", "CR-001")
    run_qms(temp_project, "claude", "checkin", "CR-001")
    run_qms(temp_project, "claude", "route", "CR-001", "--review")
    run_qms(temp_project, "qa", "review", "CR-001", "--recommend", "--comment", "OK")

    meta = read_meta(temp_project, "CR-001", "CR")
    assert meta["status"] == "POST_REVIEWED"

    # [REQ-WF-017] Checkout from POST_REVIEWED
    result = run_qms(temp_project, "claude", "checkout", "CR-001")
    assert result.returncode == 0

    # Verify status is IN_EXECUTION (not DRAFT)
    meta = read_meta(temp_project, "CR-001", "CR")
    assert meta["status"] == "IN_EXECUTION", "POST_REVIEWED checkout should transition to IN_EXECUTION"


# ============================================================================
# REQ-WF-018: Withdraw Command
# ============================================================================

def test_withdraw_from_in_review_returns_to_draft(temp_project):
    """
    [REQ-WF-018] Withdraw from IN_REVIEW returns to DRAFT.
    """
    run_qms(temp_project, "claude", "create", "SOP", "--title", "Withdraw Test")
    run_qms(temp_project, "claude", "checkin", "SOP-001")
    run_qms(temp_project, "claude", "route", "SOP-001", "--review")

    meta = read_meta(temp_project, "SOP-001", "SOP")
    assert meta["status"] == "IN_REVIEW"

    # Withdraw
    result = run_qms(temp_project, "claude", "withdraw", "SOP-001")
    assert result.returncode == 0

    meta = read_meta(temp_project, "SOP-001", "SOP")
    assert meta["status"] == "DRAFT"
    assert meta["pending_assignees"] == []


def test_withdraw_from_in_pre_review_returns_to_draft(temp_project):
    """
    [REQ-WF-018] Withdraw from IN_PRE_REVIEW returns to DRAFT.
    """
    run_qms(temp_project, "claude", "create", "CR", "--title", "Withdraw Pre-Review Test")
    run_qms(temp_project, "claude", "checkin", "CR-001")
    run_qms(temp_project, "claude", "route", "CR-001", "--review")

    meta = read_meta(temp_project, "CR-001", "CR")
    assert meta["status"] == "IN_PRE_REVIEW"

    result = run_qms(temp_project, "claude", "withdraw", "CR-001")
    assert result.returncode == 0

    meta = read_meta(temp_project, "CR-001", "CR")
    assert meta["status"] == "DRAFT"


def test_withdraw_from_in_post_review_returns_to_execution(temp_project):
    """
    [REQ-WF-018] Withdraw from IN_POST_REVIEW returns to IN_EXECUTION.
    """
    # Get CR to IN_POST_REVIEW
    run_qms(temp_project, "claude", "create", "CR", "--title", "Withdraw Post-Review Test")
    run_qms(temp_project, "claude", "checkin", "CR-001")
    run_qms(temp_project, "claude", "route", "CR-001", "--review")
    run_qms(temp_project, "qa", "review", "CR-001", "--recommend", "--comment", "OK")
    run_qms(temp_project, "claude", "route", "CR-001", "--approval")
    run_qms(temp_project, "qa", "approve", "CR-001")
    run_qms(temp_project, "claude", "release", "CR-001")
    run_qms(temp_project, "claude", "checkout", "CR-001")
    run_qms(temp_project, "claude", "checkin", "CR-001")
    run_qms(temp_project, "claude", "route", "CR-001", "--review")

    meta = read_meta(temp_project, "CR-001", "CR")
    assert meta["status"] == "IN_POST_REVIEW"

    result = run_qms(temp_project, "claude", "withdraw", "CR-001")
    assert result.returncode == 0

    meta = read_meta(temp_project, "CR-001", "CR")
    assert meta["status"] == "IN_EXECUTION"


def test_withdraw_only_allowed_for_responsible_user(temp_project):
    """
    [REQ-WF-018] Only responsible_user may withdraw.
    """
    run_qms(temp_project, "claude", "create", "SOP", "--title", "Withdraw Owner Test")
    run_qms(temp_project, "claude", "checkin", "SOP-001")
    run_qms(temp_project, "claude", "route", "SOP-001", "--review")

    # Try to withdraw as qa (not the owner)
    result = run_qms(temp_project, "qa", "withdraw", "SOP-001")
    assert result.returncode != 0
    assert "owner" in result.stdout.lower() or "error" in result.stdout.lower()


def test_withdraw_clears_assignees_and_inbox(temp_project):
    """
    [REQ-WF-018] Withdraw clears pending_assignees and removes inbox tasks.
    """
    run_qms(temp_project, "claude", "create", "SOP", "--title", "Withdraw Cleanup Test")
    run_qms(temp_project, "claude", "checkin", "SOP-001")
    run_qms(temp_project, "claude", "route", "SOP-001", "--review")

    # Verify qa has inbox task
    qa_inbox = temp_project / ".claude" / "users" / "qa" / "inbox"
    inbox_tasks = list(qa_inbox.glob("task-SOP-001-*.md"))
    assert len(inbox_tasks) > 0, "QA should have inbox task"

    # Withdraw
    run_qms(temp_project, "claude", "withdraw", "SOP-001")

    # Verify inbox task removed
    inbox_tasks = list(qa_inbox.glob("task-SOP-001-*.md"))
    assert len(inbox_tasks) == 0, "Inbox task should be removed on withdraw"

    # Verify pending_assignees cleared
    meta = read_meta(temp_project, "SOP-001", "SOP")
    assert meta["pending_assignees"] == []


# ============================================================================
# REQ-WF-019: Revert Command Deprecation
# ============================================================================

def test_revert_shows_deprecation_warning(temp_project):
    """
    [REQ-WF-019] Revert command shows deprecation warning.
    """
    # Get CR to POST_REVIEWED
    run_qms(temp_project, "claude", "create", "CR", "--title", "Revert Deprecation Test")
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

    # Use revert - should show deprecation warning but still work
    result = run_qms(temp_project, "claude", "revert", "CR-001", "--reason", "Testing deprecation")
    assert "deprecated" in result.stdout.lower() or "WARNING" in result.stdout

    # Verify it still works (backward compatibility)
    meta = read_meta(temp_project, "CR-001", "CR")
    assert meta["status"] == "IN_EXECUTION"


# ============================================================================
# REQ-WF-021: Execution Version Tracking
# ============================================================================

def test_execution_checkout_creates_minor_version(temp_project):
    """
    [REQ-WF-021] Checkout during IN_EXECUTION increments minor version.
    """
    # Get CR to IN_EXECUTION at v1.0
    run_qms(temp_project, "claude", "create", "CR", "--title", "Execution Version Test")
    run_qms(temp_project, "claude", "checkin", "CR-001")
    run_qms(temp_project, "claude", "route", "CR-001", "--review")
    run_qms(temp_project, "qa", "review", "CR-001", "--recommend", "--comment", "OK")
    run_qms(temp_project, "claude", "route", "CR-001", "--approval")
    run_qms(temp_project, "qa", "approve", "CR-001")
    run_qms(temp_project, "claude", "release", "CR-001")

    meta = read_meta(temp_project, "CR-001", "CR")
    assert meta["status"] == "IN_EXECUTION"
    assert meta["version"] == "1.0"

    # First checkout during execution -> v1.1
    run_qms(temp_project, "claude", "checkout", "CR-001")

    meta = read_meta(temp_project, "CR-001", "CR")
    assert meta["version"] == "1.1", "First execution checkout should create v1.1"


def test_execution_checkin_archives_previous(temp_project):
    """
    [REQ-WF-021] Checkin during IN_EXECUTION archives previous version.
    """
    # Get CR to IN_EXECUTION
    run_qms(temp_project, "claude", "create", "CR", "--title", "Execution Archive Test")
    run_qms(temp_project, "claude", "checkin", "CR-001")
    run_qms(temp_project, "claude", "route", "CR-001", "--review")
    run_qms(temp_project, "qa", "review", "CR-001", "--recommend", "--comment", "OK")
    run_qms(temp_project, "claude", "route", "CR-001", "--approval")
    run_qms(temp_project, "qa", "approve", "CR-001")
    run_qms(temp_project, "claude", "release", "CR-001")

    # Checkout and checkin
    run_qms(temp_project, "claude", "checkout", "CR-001")
    result = run_qms(temp_project, "claude", "checkin", "CR-001")

    # Verify v1.0 was archived
    archive_path = temp_project / "QMS" / ".archive" / "CR" / "CR-001" / "CR-001-v1.0.md"
    assert archive_path.exists(), "v1.0 should be archived on checkin"


def test_closure_increments_major_version(temp_project):
    """
    [REQ-WF-021] Closure transitions to (N+1).0 POST_APPROVED then CLOSED.
    """
    # Full CR lifecycle
    run_qms(temp_project, "claude", "create", "CR", "--title", "Closure Version Test")
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
    # Version should have bumped to 2.0
    assert meta["version"] == "2.0", "Post-approval should bump to major version"

    # Close
    run_qms(temp_project, "claude", "close", "CR-001")

    meta = read_meta(temp_project, "CR-001", "CR")
    assert meta["status"] == "CLOSED"
