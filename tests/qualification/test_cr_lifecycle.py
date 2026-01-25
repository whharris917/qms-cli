"""
QMS CLI Qualification Tests: CR Lifecycle (Executable Documents)

Tests for executable document workflow (CR).
Verifies requirements: WF-003, WF-008, WF-009, WF-010, WF-011,
META-004, AUDIT-002
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


def get_events_by_type(events, event_type):
    """Filter audit events by event type."""
    return [e for e in events if e.get("event") == event_type]


# ============================================================================
# Test: Full CR Lifecycle
# ============================================================================

def test_cr_full_lifecycle(temp_project):
    """
    Walk a CR through its complete lifecycle from DRAFT to CLOSED.

    Verifies: REQ-WF-003, REQ-WF-008, REQ-WF-010, REQ-META-004, REQ-AUDIT-002
    """
    # [REQ-WF-003] Create CR - starts in DRAFT
    result = run_qms(temp_project, "claude", "create", "CR", "--title", "Test CR Lifecycle")
    assert result.returncode == 0, f"Create failed: {result.stderr}"

    # Verify CR folder structure created
    cr_folder = temp_project / "QMS" / "CR" / "CR-001"
    assert cr_folder.exists(), "CR folder not created"
    assert (cr_folder / "CR-001-draft.md").exists(), "CR draft not created"

    # [REQ-META-004] Verify initial execution_phase is pre_release
    meta = read_meta(temp_project, "CR-001", "CR")
    assert meta["status"] == "DRAFT"
    assert meta["executable"] == True
    assert meta["execution_phase"] == "pre_release", "Initial execution_phase should be pre_release"

    # Checkin before routing (create auto-checks out)
    run_qms(temp_project, "claude", "checkin", "CR-001")

    # [REQ-WF-003] Route for pre-review: DRAFT -> IN_PRE_REVIEW
    result = run_qms(temp_project, "claude", "route", "CR-001", "--review")
    assert result.returncode == 0, f"Route pre-review failed: {result.stderr}"

    meta = read_meta(temp_project, "CR-001", "CR")
    assert meta["status"] == "IN_PRE_REVIEW"

    # [REQ-WF-003] Complete pre-review: IN_PRE_REVIEW -> PRE_REVIEWED
    result = run_qms(temp_project, "qa", "review", "CR-001",
                     "--recommend", "--comment", "Pre-review complete")
    assert result.returncode == 0, f"Pre-review failed: {result.stderr}"

    meta = read_meta(temp_project, "CR-001", "CR")
    assert meta["status"] == "PRE_REVIEWED"

    # [REQ-WF-003] Route for pre-approval: PRE_REVIEWED -> IN_PRE_APPROVAL
    result = run_qms(temp_project, "claude", "route", "CR-001", "--approval")
    assert result.returncode == 0, f"Route pre-approval failed: {result.stderr}"

    meta = read_meta(temp_project, "CR-001", "CR")
    assert meta["status"] == "IN_PRE_APPROVAL"

    # [REQ-WF-003] Complete pre-approval: IN_PRE_APPROVAL -> PRE_APPROVED
    result = run_qms(temp_project, "qa", "approve", "CR-001")
    assert result.returncode == 0, f"Pre-approval failed: {result.stderr}"

    meta = read_meta(temp_project, "CR-001", "CR")
    assert meta["status"] == "PRE_APPROVED"
    assert meta["version"] == "1.0", "Version should bump to 1.0 on approval"

    # Still pre_release until explicitly released
    assert meta["execution_phase"] == "pre_release"

    # [REQ-WF-008] Release: PRE_APPROVED -> IN_EXECUTION
    result = run_qms(temp_project, "claude", "release", "CR-001")
    assert result.returncode == 0, f"Release failed: {result.stderr}"

    meta = read_meta(temp_project, "CR-001", "CR")
    assert meta["status"] == "IN_EXECUTION"

    # [REQ-META-004] Verify execution_phase changed to post_release
    assert meta["execution_phase"] == "post_release", "execution_phase should be post_release after release"

    # [REQ-AUDIT-002] Verify RELEASE event logged
    events = read_audit(temp_project, "CR-001", "CR")
    release_events = get_events_by_type(events, "RELEASE")
    assert len(release_events) >= 1, "RELEASE event not logged"
    assert release_events[-1]["user"] == "claude"

    # Checkout for post-execution updates
    result = run_qms(temp_project, "claude", "checkout", "CR-001")
    assert result.returncode == 0, f"Post-release checkout failed: {result.stderr}"

    result = run_qms(temp_project, "claude", "checkin", "CR-001")
    assert result.returncode == 0, f"Post-release checkin failed: {result.stderr}"

    # [REQ-WF-003] Route for post-review: IN_EXECUTION -> IN_POST_REVIEW
    result = run_qms(temp_project, "claude", "route", "CR-001", "--review")
    assert result.returncode == 0, f"Route post-review failed: {result.stderr}"

    meta = read_meta(temp_project, "CR-001", "CR")
    assert meta["status"] == "IN_POST_REVIEW"

    # [REQ-WF-003] Complete post-review: IN_POST_REVIEW -> POST_REVIEWED
    result = run_qms(temp_project, "qa", "review", "CR-001",
                     "--recommend", "--comment", "Post-review complete")
    assert result.returncode == 0, f"Post-review failed: {result.stderr}"

    meta = read_meta(temp_project, "CR-001", "CR")
    assert meta["status"] == "POST_REVIEWED"

    # [REQ-WF-003] Route for post-approval: POST_REVIEWED -> IN_POST_APPROVAL
    result = run_qms(temp_project, "claude", "route", "CR-001", "--approval")
    assert result.returncode == 0, f"Route post-approval failed: {result.stderr}"

    meta = read_meta(temp_project, "CR-001", "CR")
    assert meta["status"] == "IN_POST_APPROVAL"

    # [REQ-WF-003] Complete post-approval: IN_POST_APPROVAL -> POST_APPROVED
    result = run_qms(temp_project, "qa", "approve", "CR-001")
    assert result.returncode == 0, f"Post-approval failed: {result.stderr}"

    meta = read_meta(temp_project, "CR-001", "CR")
    assert meta["status"] == "POST_APPROVED"
    assert meta["version"] == "2.0", "Version should bump to 2.0 on post-approval"

    # [REQ-WF-010] Close: POST_APPROVED -> CLOSED
    result = run_qms(temp_project, "claude", "close", "CR-001")
    assert result.returncode == 0, f"Close failed: {result.stderr}"

    meta = read_meta(temp_project, "CR-001", "CR")
    assert meta["status"] == "CLOSED"

    # [REQ-AUDIT-002] Verify CLOSE event logged
    events = read_audit(temp_project, "CR-001", "CR")
    close_events = get_events_by_type(events, "CLOSE")
    assert len(close_events) >= 1, "CLOSE event not logged"
    assert close_events[-1]["user"] == "claude"

    # Verify document renamed from draft to final
    assert (cr_folder / "CR-001.md").exists(), "Final CR document should exist"
    assert not (cr_folder / "CR-001-draft.md").exists(), "Draft should be removed after close"


# ============================================================================
# Test: Revert Transition
# ============================================================================

def test_revert(temp_project):
    """
    Revert from POST_REVIEWED back to IN_EXECUTION.

    Verifies: REQ-WF-009, REQ-AUDIT-002
    """
    # Create CR and get to POST_REVIEWED
    run_qms(temp_project, "claude", "create", "CR", "--title", "Test Revert")
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
    run_qms(temp_project, "qa", "review", "CR-001", "--recommend", "--comment", "Post OK")

    meta = read_meta(temp_project, "CR-001", "CR")
    assert meta["status"] == "POST_REVIEWED"
    version_before = meta["version"]

    # [REQ-WF-009] Revert with reason
    result = run_qms(temp_project, "claude", "revert", "CR-001",
                     "--reason", "Found issue during execution")
    assert result.returncode == 0, f"Revert failed: {result.stderr}"

    # Verify returns to IN_EXECUTION
    meta = read_meta(temp_project, "CR-001", "CR")
    assert meta["status"] == "IN_EXECUTION"
    assert meta["version"] == version_before, "Version should not change on revert"
    assert meta["execution_phase"] == "post_release", "execution_phase should remain post_release"

    # [REQ-AUDIT-002] Verify REVERT event logged with reason
    events = read_audit(temp_project, "CR-001", "CR")
    revert_events = get_events_by_type(events, "REVERT")
    assert len(revert_events) >= 1, "REVERT event not logged"
    assert revert_events[-1]["reason"] == "Found issue during execution"


# ============================================================================
# Test: Terminal State Enforcement
# ============================================================================

def test_terminal_state(temp_project):
    """
    CLOSED state rejects all routing commands.

    Verifies: REQ-WF-011
    """
    # Create CR and get to CLOSED
    run_qms(temp_project, "claude", "create", "CR", "--title", "Test Terminal")
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
    run_qms(temp_project, "claude", "close", "CR-001")

    meta = read_meta(temp_project, "CR-001", "CR")
    assert meta["status"] == "CLOSED"

    # [REQ-WF-011] Attempt to route from CLOSED - should fail
    result = run_qms(temp_project, "claude", "route", "CR-001", "--review")
    assert result.returncode != 0, "Routing from CLOSED should fail"

    # Verify status unchanged
    meta = read_meta(temp_project, "CR-001", "CR")
    assert meta["status"] == "CLOSED"

    # Note: Checkout from CLOSED is allowed (creates new revision for amendment)
    # The terminal state enforcement applies to status transitions, not checkout


# ============================================================================
# Test: Execution Phase Preserved on Checkin
# ============================================================================

def test_execution_phase_preserved(temp_project):
    """
    Execution phase (post_release) is preserved through checkout/checkin cycles.

    Verifies: REQ-META-004
    """
    # Create CR and release to IN_EXECUTION
    run_qms(temp_project, "claude", "create", "CR", "--title", "Test Phase Preservation")
    run_qms(temp_project, "claude", "checkin", "CR-001")
    run_qms(temp_project, "claude", "route", "CR-001", "--review")
    run_qms(temp_project, "qa", "review", "CR-001", "--recommend", "--comment", "OK")
    run_qms(temp_project, "claude", "route", "CR-001", "--approval")
    run_qms(temp_project, "qa", "approve", "CR-001")
    run_qms(temp_project, "claude", "release", "CR-001")

    meta = read_meta(temp_project, "CR-001", "CR")
    assert meta["status"] == "IN_EXECUTION"
    assert meta["execution_phase"] == "post_release"

    # [REQ-META-004] Checkout and checkin - phase should be preserved
    run_qms(temp_project, "claude", "checkout", "CR-001")

    meta = read_meta(temp_project, "CR-001", "CR")
    assert meta["execution_phase"] == "post_release", "Phase should be preserved during checkout"

    run_qms(temp_project, "claude", "checkin", "CR-001")

    meta = read_meta(temp_project, "CR-001", "CR")
    assert meta["execution_phase"] == "post_release", "Phase should be preserved after checkin"

    # Multiple checkout/checkin cycles
    for i in range(3):
        run_qms(temp_project, "claude", "checkout", "CR-001")
        run_qms(temp_project, "claude", "checkin", "CR-001")

        meta = read_meta(temp_project, "CR-001", "CR")
        assert meta["execution_phase"] == "post_release", f"Phase lost on cycle {i+1}"


# ============================================================================
# Test: Owner-Only Release
# ============================================================================

def test_owner_only_release(temp_project):
    """
    Only the document owner can release an executable document.

    Verifies: REQ-WF-008
    """
    # Create CR as claude and get to PRE_APPROVED
    run_qms(temp_project, "claude", "create", "CR", "--title", "Test Owner Release")
    run_qms(temp_project, "claude", "checkin", "CR-001")
    run_qms(temp_project, "claude", "route", "CR-001", "--review")
    run_qms(temp_project, "qa", "review", "CR-001", "--recommend", "--comment", "OK")
    run_qms(temp_project, "claude", "route", "CR-001", "--approval")
    run_qms(temp_project, "qa", "approve", "CR-001")

    meta = read_meta(temp_project, "CR-001", "CR")
    assert meta["status"] == "PRE_APPROVED"

    # [REQ-WF-008] Non-owner (qa) attempts release - should fail
    result = run_qms(temp_project, "qa", "release", "CR-001")
    assert result.returncode != 0, "Non-owner should not be able to release"

    # Status should be unchanged
    meta = read_meta(temp_project, "CR-001", "CR")
    assert meta["status"] == "PRE_APPROVED"

    # Owner (claude) releases - should succeed
    result = run_qms(temp_project, "claude", "release", "CR-001")
    assert result.returncode == 0, f"Owner release failed: {result.stderr}"

    meta = read_meta(temp_project, "CR-001", "CR")
    assert meta["status"] == "IN_EXECUTION"


# ============================================================================
# Test: Owner-Only Close
# ============================================================================

def test_owner_only_close(temp_project):
    """
    Only the document owner can close an executable document.

    Verifies: REQ-WF-010
    """
    # Create CR and get to POST_APPROVED
    run_qms(temp_project, "claude", "create", "CR", "--title", "Test Owner Close")
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

    # [REQ-WF-010] Non-owner (qa) attempts close - should fail
    result = run_qms(temp_project, "qa", "close", "CR-001")
    assert result.returncode != 0, "Non-owner should not be able to close"

    # Status should be unchanged
    meta = read_meta(temp_project, "CR-001", "CR")
    assert meta["status"] == "POST_APPROVED"

    # Owner (claude) closes - should succeed
    result = run_qms(temp_project, "claude", "close", "CR-001")
    assert result.returncode == 0, f"Owner close failed: {result.stderr}"

    meta = read_meta(temp_project, "CR-001", "CR")
    assert meta["status"] == "CLOSED"


# ============================================================================
# Test: Pre-Approval Rejection
# ============================================================================

def test_pre_approval_rejection(temp_project):
    """
    Rejection in pre-approval returns to PRE_REVIEWED.

    Verifies: REQ-WF-007 (for executable documents)
    """
    # Create CR and get to IN_PRE_APPROVAL
    run_qms(temp_project, "claude", "create", "CR", "--title", "Test Pre-Rejection")
    run_qms(temp_project, "claude", "checkin", "CR-001")
    run_qms(temp_project, "claude", "route", "CR-001", "--review")
    run_qms(temp_project, "qa", "review", "CR-001", "--recommend", "--comment", "OK")
    run_qms(temp_project, "claude", "route", "CR-001", "--approval")

    meta = read_meta(temp_project, "CR-001", "CR")
    assert meta["status"] == "IN_PRE_APPROVAL"
    version_before = meta["version"]

    # [REQ-WF-007] Reject
    result = run_qms(temp_project, "qa", "reject", "CR-001",
                     "--comment", "Not ready for approval")
    assert result.returncode == 0, f"Reject failed: {result.stderr}"

    # Verify returns to PRE_REVIEWED
    meta = read_meta(temp_project, "CR-001", "CR")
    assert meta["status"] == "PRE_REVIEWED"
    assert meta["version"] == version_before, "Version should not change on rejection"


# ============================================================================
# Test: Post-Approval Rejection
# ============================================================================

def test_post_approval_rejection(temp_project):
    """
    Rejection in post-approval returns to POST_REVIEWED.

    Verifies: REQ-WF-007 (for executable documents in post-release)
    """
    # Create CR and get to IN_POST_APPROVAL
    run_qms(temp_project, "claude", "create", "CR", "--title", "Test Post-Rejection")
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

    meta = read_meta(temp_project, "CR-001", "CR")
    assert meta["status"] == "IN_POST_APPROVAL"
    version_before = meta["version"]

    # [REQ-WF-007] Reject
    result = run_qms(temp_project, "qa", "reject", "CR-001",
                     "--comment", "Execution incomplete")
    assert result.returncode == 0, f"Reject failed: {result.stderr}"

    # Verify returns to POST_REVIEWED
    meta = read_meta(temp_project, "CR-001", "CR")
    assert meta["status"] == "POST_REVIEWED"
    assert meta["version"] == version_before, "Version should not change on rejection"


# ============================================================================
# Test: Checkin Reverts PRE_REVIEWED Status
# ============================================================================

def test_checkin_reverts_pre_reviewed(temp_project):
    """
    Checkin from PRE_REVIEWED status should revert to DRAFT.

    Verifies: REQ-DOC-009 (for executable documents in pre-review phase)
    """
    # Create CR and get to PRE_REVIEWED
    run_qms(temp_project, "claude", "create", "CR", "--title", "Test Pre-Reviewed Revert")
    run_qms(temp_project, "claude", "checkin", "CR-001")
    run_qms(temp_project, "claude", "route", "CR-001", "--review")
    run_qms(temp_project, "qa", "review", "CR-001", "--recommend", "--comment", "OK")

    meta = read_meta(temp_project, "CR-001", "CR")
    assert meta["status"] == "PRE_REVIEWED"

    # [REQ-DOC-009] Checkout and checkin from PRE_REVIEWED
    run_qms(temp_project, "claude", "checkout", "CR-001")
    run_qms(temp_project, "claude", "checkin", "CR-001")

    # Verify status reverted to DRAFT
    meta = read_meta(temp_project, "CR-001", "CR")
    assert meta["status"] == "DRAFT", "PRE_REVIEWED should revert to DRAFT on checkin"

    # Verify review tracking fields cleared
    assert meta["pending_assignees"] == [], "pending_assignees should be cleared"


# ============================================================================
# Test: Checkin Reverts POST_REVIEWED Status
# ============================================================================

def test_checkin_reverts_post_reviewed(temp_project):
    """
    Checkin from POST_REVIEWED status should revert to IN_EXECUTION.

    Verifies: REQ-DOC-009 (for executable documents in post-review phase)
    """
    # Create CR and get to POST_REVIEWED
    run_qms(temp_project, "claude", "create", "CR", "--title", "Test Post-Reviewed Revert")
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

    # [REQ-DOC-009] Checkout and checkin from POST_REVIEWED
    run_qms(temp_project, "claude", "checkout", "CR-001")
    run_qms(temp_project, "claude", "checkin", "CR-001")

    # Verify status reverted to DRAFT per REQ-DOC-009
    # (the requirement says REVIEWED/PRE_REVIEWED/POST_REVIEWED all revert to DRAFT)
    meta = read_meta(temp_project, "CR-001", "CR")
    assert meta["status"] == "DRAFT", "POST_REVIEWED should revert to DRAFT on checkin per REQ-DOC-009"

    # Verify review tracking fields cleared
    assert meta["pending_assignees"] == [], "pending_assignees should be cleared"


# ============================================================================
# Test: Terminal State - RETIRED
# ============================================================================

def test_terminal_state_retired(temp_project):
    """
    RETIRED is a terminal state - no transitions allowed.

    Verifies: REQ-WF-011 (for RETIRED terminal state)
    """
    # Create SOP and get it to EFFECTIVE, then RETIRED
    run_qms(temp_project, "claude", "create", "SOP", "--title", "Test Retired Terminal")
    run_qms(temp_project, "claude", "checkin", "SOP-001")
    run_qms(temp_project, "claude", "route", "SOP-001", "--review")
    run_qms(temp_project, "qa", "review", "SOP-001", "--recommend", "--comment", "OK")
    run_qms(temp_project, "claude", "route", "SOP-001", "--approval")
    run_qms(temp_project, "qa", "approve", "SOP-001")

    meta = read_meta(temp_project, "SOP-001", "SOP")
    assert meta["status"] == "EFFECTIVE"

    # SOP is now EFFECTIVE - route for retirement (correct workflow)
    run_qms(temp_project, "claude", "checkout", "SOP-001")
    run_qms(temp_project, "claude", "checkin", "SOP-001")
    run_qms(temp_project, "claude", "route", "SOP-001", "--review")
    run_qms(temp_project, "qa", "review", "SOP-001", "--recommend", "--comment", "OK for retirement")
    # Route for approval with --retire flag
    run_qms(temp_project, "claude", "route", "SOP-001", "--approval", "--retire")
    run_qms(temp_project, "qa", "approve", "SOP-001")

    meta = read_meta(temp_project, "SOP-001", "SOP")
    assert meta["status"] == "RETIRED"

    # [REQ-WF-011] Attempt operations on RETIRED document - all should fail
    result = run_qms(temp_project, "claude", "checkout", "SOP-001")
    assert result.returncode != 0, "Checkout from RETIRED should fail"

    result = run_qms(temp_project, "claude", "route", "SOP-001", "--review")
    assert result.returncode != 0, "Route from RETIRED should fail"

    # Verify status unchanged
    meta = read_meta(temp_project, "SOP-001", "SOP")
    assert meta["status"] == "RETIRED", "Status should remain RETIRED"
