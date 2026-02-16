"""
QMS CLI Qualification Tests: CR-087 Workflow Enforcement

Tests for checkout auto-withdraw (REQ-WF-022) and route auto-checkin (REQ-WF-023).

Created as part of CR-087: QMS CLI Quality, State Machine, and Workflow Enforcement
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


def read_audit(temp_project, doc_id, doc_type):
    """Read .audit JSONL file and return list of events."""
    audit_path = temp_project / "QMS" / ".audit" / doc_type / f"{doc_id}.jsonl"
    if not audit_path.exists():
        return []
    events = []
    for line in audit_path.read_text(encoding="utf-8").strip().split("\n"):
        if line:
            events.append(json.loads(line))
    return events


# ============================================================================
# REQ-WF-022: Checkout Auto-Withdraw
# ============================================================================

def test_checkout_auto_withdraws_from_in_pre_review(temp_project):
    """
    Checking out from IN_PRE_REVIEW auto-withdraws to DRAFT, then checks out.

    Verifies: REQ-WF-022
    """
    # Create CR and get to IN_PRE_REVIEW
    run_qms(temp_project, "claude", "create", "CR", "--title", "Auto-Withdraw Test")
    run_qms(temp_project, "claude", "checkin", "CR-001")
    run_qms(temp_project, "claude", "route", "CR-001", "--review")

    meta = read_meta(temp_project, "CR-001", "CR")
    assert meta["status"] == "IN_PRE_REVIEW"

    # Checkout from IN_PRE_REVIEW - should auto-withdraw first
    result = run_qms(temp_project, "claude", "checkout", "CR-001")
    assert result.returncode == 0, f"Checkout failed: {result.stderr}"
    assert "Auto-withdrawn" in result.stdout

    meta = read_meta(temp_project, "CR-001", "CR")
    assert meta["checked_out"] == True
    assert meta["status"] == "DRAFT"

    # Verify WITHDRAW event logged
    events = read_audit(temp_project, "CR-001", "CR")
    withdraw_events = [e for e in events if e["event"] == "WITHDRAW"]
    assert len(withdraw_events) >= 1, "WITHDRAW event not logged during auto-withdraw"


def test_checkout_auto_withdraws_from_in_pre_approval(temp_project):
    """
    Checking out from IN_PRE_APPROVAL auto-withdraws to PRE_REVIEWED, then checks out.

    Verifies: REQ-WF-022
    """
    # Create CR and get to IN_PRE_APPROVAL
    run_qms(temp_project, "claude", "create", "CR", "--title", "Auto-Withdraw Approval")
    run_qms(temp_project, "claude", "checkin", "CR-001")
    run_qms(temp_project, "claude", "route", "CR-001", "--review")
    run_qms(temp_project, "qa", "review", "CR-001", "--recommend", "--comment", "OK")
    run_qms(temp_project, "claude", "route", "CR-001", "--approval")

    meta = read_meta(temp_project, "CR-001", "CR")
    assert meta["status"] == "IN_PRE_APPROVAL"

    # Checkout from IN_PRE_APPROVAL - auto-withdraw to PRE_REVIEWED, then checkout transitions
    result = run_qms(temp_project, "claude", "checkout", "CR-001")
    assert result.returncode == 0, f"Checkout failed: {result.stderr}"
    assert "Auto-withdrawn" in result.stdout

    meta = read_meta(temp_project, "CR-001", "CR")
    assert meta["checked_out"] == True


def test_checkout_auto_withdraws_from_in_post_review(temp_project):
    """
    Checking out from IN_POST_REVIEW auto-withdraws to IN_EXECUTION, then checks out.

    Verifies: REQ-WF-022
    """
    # Create CR and get to IN_POST_REVIEW
    run_qms(temp_project, "claude", "create", "CR", "--title", "Post-Review Withdraw")
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

    # Checkout from IN_POST_REVIEW - auto-withdraw to IN_EXECUTION
    result = run_qms(temp_project, "claude", "checkout", "CR-001")
    assert result.returncode == 0, f"Checkout failed: {result.stderr}"
    assert "Auto-withdrawn" in result.stdout

    meta = read_meta(temp_project, "CR-001", "CR")
    assert meta["checked_out"] == True
    assert meta["status"] == "IN_EXECUTION"


def test_checkout_auto_withdraw_clears_inbox_tasks(temp_project):
    """
    Auto-withdraw during checkout clears inbox tasks for all assignees.

    Verifies: REQ-WF-022
    """
    # Create CR and get to IN_PRE_REVIEW with qa assigned
    run_qms(temp_project, "claude", "create", "CR", "--title", "Inbox Clear Test")
    run_qms(temp_project, "claude", "checkin", "CR-001")
    run_qms(temp_project, "claude", "route", "CR-001", "--review")

    # Verify qa has inbox task
    qa_inbox = temp_project / ".claude" / "users" / "qa" / "inbox"
    inbox_files = list(qa_inbox.glob("task-CR-001-*.md"))
    assert len(inbox_files) > 0, "QA should have inbox task"

    # Auto-withdraw via checkout
    run_qms(temp_project, "claude", "checkout", "CR-001")

    # Inbox should be cleared
    inbox_files = list(qa_inbox.glob("task-CR-001-*.md"))
    assert len(inbox_files) == 0, "Inbox tasks should be cleared after auto-withdraw"


def test_checkout_auto_withdraw_blocked_for_non_owner(temp_project):
    """
    Auto-withdraw is blocked when the checkout user is not the document owner.

    Verifies: REQ-WF-022
    """
    # Create CR (owned by claude) and get to IN_PRE_REVIEW
    run_qms(temp_project, "claude", "create", "CR", "--title", "Non-Owner Test")
    run_qms(temp_project, "claude", "checkin", "CR-001")
    run_qms(temp_project, "claude", "route", "CR-001", "--review")

    # lead tries to checkout - should fail (not the owner)
    result = run_qms(temp_project, "lead", "checkout", "CR-001")
    assert result.returncode != 0, "Non-owner checkout from workflow should fail"
    assert "owner" in result.stdout.lower() or "owned" in result.stdout.lower()


def test_checkout_auto_withdraws_from_non_executable_in_review(temp_project):
    """
    Checking out SOP from IN_REVIEW auto-withdraws to DRAFT.

    Verifies: REQ-WF-022 (non-executable path)
    """
    # Create SOP and get to IN_REVIEW
    run_qms(temp_project, "claude", "create", "SOP", "--title", "SOP Withdraw Test")
    run_qms(temp_project, "claude", "checkin", "SOP-001")
    run_qms(temp_project, "claude", "route", "SOP-001", "--review")

    meta = read_meta(temp_project, "SOP-001", "SOP")
    assert meta["status"] == "IN_REVIEW"

    # Checkout from IN_REVIEW
    result = run_qms(temp_project, "claude", "checkout", "SOP-001")
    assert result.returncode == 0, f"SOP checkout failed: {result.stderr}"
    assert "Auto-withdrawn" in result.stdout

    meta = read_meta(temp_project, "SOP-001", "SOP")
    assert meta["checked_out"] == True
    assert meta["status"] == "DRAFT"


# ============================================================================
# REQ-WF-023: Route Auto-Checkin
# ============================================================================

def test_route_auto_checkin_for_review(temp_project):
    """
    Routing for review while checked out auto-checks-in first.

    Verifies: REQ-WF-023
    """
    # Create CR (auto-checks out)
    run_qms(temp_project, "claude", "create", "CR", "--title", "Auto-Checkin Test")

    meta = read_meta(temp_project, "CR-001", "CR")
    assert meta["checked_out"] == True

    # Route for review while checked out - should auto-checkin
    result = run_qms(temp_project, "claude", "route", "CR-001", "--review")
    assert result.returncode == 0, f"Route failed: {result.stderr}"
    assert "Auto-checked-in" in result.stdout

    meta = read_meta(temp_project, "CR-001", "CR")
    assert meta["checked_out"] == False
    assert meta["status"] == "IN_PRE_REVIEW"

    # Verify CHECKIN event logged (auto-checkin produces audit trail)
    events = read_audit(temp_project, "CR-001", "CR")
    checkin_events = [e for e in events if e["event"] == "CHECKIN"]
    assert len(checkin_events) >= 1, "CHECKIN event not logged during auto-checkin"


def test_route_auto_checkin_blocked_for_non_owner(temp_project):
    """
    Non-owner cannot route a checked-out document (no auto-checkin).

    Verifies: REQ-WF-015, REQ-WF-023
    """
    # Create CR (owned and checked out by claude)
    run_qms(temp_project, "claude", "create", "CR", "--title", "Non-Owner Route Test")

    meta = read_meta(temp_project, "CR-001", "CR")
    assert meta["checked_out"] == True
    assert meta["responsible_user"] == "claude"

    # lead tries to route - should fail (checked out by claude)
    result = run_qms(temp_project, "lead", "route", "CR-001", "--review")
    assert result.returncode != 0, "Non-owner routing while checked out should fail"


def test_route_auto_checkin_for_sop(temp_project):
    """
    Routing SOP for review while checked out auto-checks-in.

    Verifies: REQ-WF-023 (non-executable path)
    """
    # Create SOP (auto-checks out)
    run_qms(temp_project, "claude", "create", "SOP", "--title", "SOP Auto-Checkin")

    meta = read_meta(temp_project, "SOP-001", "SOP")
    assert meta["checked_out"] == True

    # Route while checked out
    result = run_qms(temp_project, "claude", "route", "SOP-001", "--review")
    assert result.returncode == 0, f"Route failed: {result.stderr}"
    assert "Auto-checked-in" in result.stdout

    meta = read_meta(temp_project, "SOP-001", "SOP")
    assert meta["status"] == "IN_REVIEW"
    assert meta["checked_out"] == False


def test_route_auto_checkin_workspace_cleaned(temp_project):
    """
    Auto-checkin during route removes the workspace copy.

    Verifies: REQ-WF-023
    """
    # Create CR (auto-checks out, workspace copy exists)
    run_qms(temp_project, "claude", "create", "CR", "--title", "Workspace Clean Test")

    workspace_path = temp_project / ".claude" / "users" / "claude" / "workspace" / "CR-001.md"
    assert workspace_path.exists(), "Workspace copy should exist after create"

    # Route while checked out - auto-checkin should remove workspace
    run_qms(temp_project, "claude", "route", "CR-001", "--review")

    assert not workspace_path.exists(), "Workspace copy should be removed after auto-checkin"
