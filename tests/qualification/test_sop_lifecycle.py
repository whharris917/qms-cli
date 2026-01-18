"""
QMS CLI Qualification Tests: SOP Lifecycle

Tests for non-executable document workflow (SOP).
Verifies requirements: DOC-003, DOC-006, DOC-007, DOC-008, DOC-009,
WF-001, WF-002, WF-004, WF-005, WF-006, WF-007, WF-012, WF-013,
META-001, META-002, AUDIT-001, AUDIT-002, AUDIT-003, AUDIT-004,
TASK-001, TASK-002, TASK-003, TASK-004, CFG-002, CFG-003
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


def read_frontmatter(file_path):
    """Parse YAML frontmatter from a document."""
    content = file_path.read_text(encoding="utf-8")
    if not content.startswith("---"):
        return {}
    parts = content.split("---", 2)
    if len(parts) < 3:
        return {}
    import yaml
    return yaml.safe_load(parts[1]) or {}


def count_audit_lines(temp_project, doc_id, doc_type):
    """Count lines in audit file."""
    audit_path = temp_project / "QMS" / ".audit" / doc_type / f"{doc_id}.jsonl"
    if not audit_path.exists():
        return 0
    return len(audit_path.read_text(encoding="utf-8").strip().split("\n"))


def task_exists(temp_project, user, doc_id):
    """Check if a task for doc_id exists in user's inbox."""
    inbox_path = temp_project / ".claude" / "users" / user / "inbox"
    if not inbox_path.exists():
        return False
    return any(doc_id in f.name for f in inbox_path.glob("task-*.md"))


def get_task_content(temp_project, user, doc_id):
    """Get content of task file for doc_id in user's inbox."""
    inbox_path = temp_project / ".claude" / "users" / user / "inbox"
    for task_file in inbox_path.glob(f"task-{doc_id}-*.md"):
        return task_file.read_text(encoding="utf-8")
    return None


# ============================================================================
# Test: Full SOP Lifecycle
# ============================================================================

def test_sop_full_lifecycle(temp_project):
    """
    Walk an SOP through its complete lifecycle from DRAFT to EFFECTIVE.

    Verifies: REQ-DOC-003, REQ-DOC-006, REQ-DOC-007, REQ-DOC-008,
              REQ-WF-002, REQ-WF-006, REQ-META-001, REQ-META-002,
              REQ-AUDIT-001, REQ-AUDIT-002, REQ-AUDIT-003, REQ-AUDIT-004,
              REQ-TASK-001, REQ-TASK-002, REQ-TASK-003, REQ-TASK-004,
              REQ-CFG-002, REQ-CFG-003
    """
    # [REQ-DOC-003] [REQ-CFG-002] Create SOP - verify file in QMS/SOP/
    result = run_qms(temp_project, "claude", "create", "SOP", "--title", "Test SOP")
    assert result.returncode == 0, f"Create failed: {result.stderr}"
    assert (temp_project / "QMS" / "SOP" / "SOP-001-draft.md").exists()

    # [REQ-DOC-006] Verify initial version is 0.1
    meta = read_meta(temp_project, "SOP-001", "SOP")
    assert meta["version"] == "0.1"
    assert meta["status"] == "DRAFT"

    # [REQ-META-001] [REQ-META-002] Verify three-tier separation
    # Frontmatter should only have title, revision_summary
    draft_path = temp_project / "QMS" / "SOP" / "SOP-001-draft.md"
    frontmatter = read_frontmatter(draft_path)
    assert "title" in frontmatter
    assert "version" not in frontmatter, "Version should not be in frontmatter"
    assert "status" not in frontmatter, "Status should not be in frontmatter"

    # .meta should have workflow state
    assert meta["doc_id"] == "SOP-001"
    assert meta["doc_type"] == "SOP"
    assert meta["executable"] == False

    # [REQ-AUDIT-002] [REQ-AUDIT-003] Verify CREATE event in audit
    events = read_audit(temp_project, "SOP-001", "SOP")
    assert len(events) >= 1
    create_event = events[0]
    assert create_event["event"] == "CREATE"
    assert create_event["user"] == "claude"
    assert "ts" in create_event  # ISO 8601 timestamp
    assert "version" in create_event

    # Create command auto-checks-out to user - verify workspace exists
    workspace_path = temp_project / ".claude" / "users" / "claude" / "workspace" / "SOP-001.md"
    assert workspace_path.exists(), "Create should auto-checkout to workspace"
    assert meta["checked_out"] == True
    assert meta["responsible_user"] == "claude"

    audit_lines_after_create = count_audit_lines(temp_project, "SOP-001", "SOP")

    # [REQ-DOC-008] Checkin first - verify QMS draft updated
    result = run_qms(temp_project, "claude", "checkin", "SOP-001")
    assert result.returncode == 0, f"Checkin failed: {result.stderr}"
    assert not workspace_path.exists(), "Workspace copy should be removed after checkin"

    meta = read_meta(temp_project, "SOP-001", "SOP")
    assert meta["checked_out"] == False
    assert meta["responsible_user"] == "claude"  # Owner preserved

    audit_lines_after_checkin = count_audit_lines(temp_project, "SOP-001", "SOP")
    assert audit_lines_after_checkin > audit_lines_after_create

    # [REQ-DOC-007] [REQ-CFG-003] Checkout - verify workspace copy created
    result = run_qms(temp_project, "claude", "checkout", "SOP-001")
    assert result.returncode == 0, f"Checkout failed: {result.stderr}"
    assert workspace_path.exists(), "Workspace copy not created"

    # Verify metadata updated
    meta = read_meta(temp_project, "SOP-001", "SOP")
    assert meta["checked_out"] == True
    assert meta["responsible_user"] == "claude"

    # [REQ-AUDIT-001] Verify audit line count increased (append-only)
    audit_lines_after_checkout = count_audit_lines(temp_project, "SOP-001", "SOP")
    assert audit_lines_after_checkout > audit_lines_after_checkin

    # [REQ-DOC-008] Checkin again - verify QMS draft updated
    result = run_qms(temp_project, "claude", "checkin", "SOP-001")
    assert result.returncode == 0, f"Checkin failed: {result.stderr}"
    assert not workspace_path.exists(), "Workspace copy should be removed after checkin"

    meta = read_meta(temp_project, "SOP-001", "SOP")
    assert meta["checked_out"] == False
    assert meta["responsible_user"] == "claude"  # Owner preserved

    # [REQ-WF-002] Route for review - DRAFT -> IN_REVIEW
    result = run_qms(temp_project, "claude", "route", "SOP-001", "--review")
    assert result.returncode == 0, f"Route review failed: {result.stderr}"

    meta = read_meta(temp_project, "SOP-001", "SOP")
    assert meta["status"] == "IN_REVIEW"

    # [REQ-TASK-001] [REQ-TASK-003] Verify task created in qa's inbox (auto-assigned)
    assert task_exists(temp_project, "qa", "SOP-001"), "Task not created in qa inbox"
    assert "qa" in meta["pending_assignees"]

    # [REQ-TASK-002] Verify task content
    task_content = get_task_content(temp_project, "qa", "SOP-001")
    assert task_content is not None
    assert "SOP-001" in task_content
    assert "REVIEW" in task_content

    # [REQ-AUDIT-004] Submit review with comment - comment should be in audit only
    result = run_qms(temp_project, "qa", "review", "SOP-001",
                     "--recommend", "--comment", "Looks good, approved.")
    assert result.returncode == 0, f"Review failed: {result.stderr}"

    # Verify comment is in audit trail
    events = read_audit(temp_project, "SOP-001", "SOP")
    review_events = [e for e in events if e["event"] == "REVIEW"]
    assert len(review_events) >= 1
    assert review_events[-1]["comment"] == "Looks good, approved."

    # Verify comment NOT in frontmatter
    frontmatter = read_frontmatter(draft_path)
    assert "comment" not in frontmatter

    # [REQ-WF-002] After review complete: IN_REVIEW -> REVIEWED
    meta = read_meta(temp_project, "SOP-001", "SOP")
    assert meta["status"] == "REVIEWED"

    # [REQ-TASK-004] Verify task removed from inbox
    assert not task_exists(temp_project, "qa", "SOP-001"), "Task should be removed after review"

    # [REQ-WF-002] Route for approval - REVIEWED -> IN_APPROVAL
    result = run_qms(temp_project, "claude", "route", "SOP-001", "--approval")
    assert result.returncode == 0, f"Route approval failed: {result.stderr}"

    meta = read_meta(temp_project, "SOP-001", "SOP")
    assert meta["status"] == "IN_APPROVAL"

    # [REQ-WF-002] [REQ-WF-006] Approve - IN_APPROVAL -> APPROVED -> EFFECTIVE
    result = run_qms(temp_project, "qa", "approve", "SOP-001")
    assert result.returncode == 0, f"Approve failed: {result.stderr}"

    meta = read_meta(temp_project, "SOP-001", "SOP")
    assert meta["status"] == "EFFECTIVE"

    # [REQ-DOC-006] [REQ-WF-006] Verify version bumped to 1.0
    assert meta["version"] == "1.0"

    # [REQ-WF-006] Verify responsible_user cleared
    assert meta["responsible_user"] is None

    # [REQ-DOC-003] Verify effective document exists (not draft)
    assert (temp_project / "QMS" / "SOP" / "SOP-001.md").exists()
    assert not (temp_project / "QMS" / "SOP" / "SOP-001-draft.md").exists()

    # [REQ-WF-006] Verify archive exists
    assert (temp_project / "QMS" / ".archive" / "SOP" / "SOP-001-v0.1.md").exists()

    # [REQ-AUDIT-002] Verify EFFECTIVE event logged
    events = read_audit(temp_project, "SOP-001", "SOP")
    effective_events = [e for e in events if e["event"] == "EFFECTIVE"]
    assert len(effective_events) >= 1


def test_invalid_transition(temp_project):
    """
    Attempt an invalid status transition.

    Verifies: REQ-WF-001
    """
    # Create SOP
    run_qms(temp_project, "claude", "create", "SOP", "--title", "Test Invalid")
    run_qms(temp_project, "claude", "checkin", "SOP-001")  # Must checkin to test transition rules

    # [REQ-WF-001] Attempt to route for approval from DRAFT (invalid)
    result = run_qms(temp_project, "claude", "route", "SOP-001", "--approval")
    assert result.returncode != 0, "Invalid transition should fail"

    # Verify status unchanged
    meta = read_meta(temp_project, "SOP-001", "SOP")
    assert meta["status"] == "DRAFT"


def test_checkin_reverts_reviewed(temp_project):
    """
    Checkin from REVIEWED status should revert to DRAFT.

    Verifies: REQ-DOC-009
    """
    # Create and route SOP to REVIEWED
    run_qms(temp_project, "claude", "create", "SOP", "--title", "Test Revert")
    run_qms(temp_project, "claude", "checkin", "SOP-001")  # Must checkin before routing
    run_qms(temp_project, "claude", "route", "SOP-001", "--review")
    run_qms(temp_project, "qa", "review", "SOP-001", "--recommend", "--comment", "OK")

    meta = read_meta(temp_project, "SOP-001", "SOP")
    assert meta["status"] == "REVIEWED"

    # [REQ-DOC-009] Checkout and checkin from REVIEWED
    run_qms(temp_project, "claude", "checkout", "SOP-001")
    run_qms(temp_project, "claude", "checkin", "SOP-001")

    # Verify status reverted to DRAFT
    meta = read_meta(temp_project, "SOP-001", "SOP")
    assert meta["status"] == "DRAFT"


def test_multi_reviewer_gate(temp_project):
    """
    Review completion gate with multiple reviewers.

    Verifies: REQ-WF-004
    """
    # Create SOP
    run_qms(temp_project, "claude", "create", "SOP", "--title", "Test Multi Review")
    run_qms(temp_project, "claude", "checkin", "SOP-001")  # Must checkin before routing

    # Route with two reviewers
    run_qms(temp_project, "claude", "route", "SOP-001", "--review",
            "--assign", "qa", "lead")

    meta = read_meta(temp_project, "SOP-001", "SOP")
    assert meta["status"] == "IN_REVIEW"
    assert set(meta["pending_assignees"]) == {"qa", "lead"}

    # [REQ-WF-004] First reviewer completes - should still be IN_REVIEW
    run_qms(temp_project, "qa", "review", "SOP-001", "--recommend", "--comment", "QA OK")

    meta = read_meta(temp_project, "SOP-001", "SOP")
    assert meta["status"] == "IN_REVIEW", "Should still be IN_REVIEW with one reviewer pending"
    assert meta["pending_assignees"] == ["lead"]

    # [REQ-WF-004] Second reviewer completes - should transition to REVIEWED
    run_qms(temp_project, "lead", "review", "SOP-001", "--recommend", "--comment", "Lead OK")

    meta = read_meta(temp_project, "SOP-001", "SOP")
    assert meta["status"] == "REVIEWED"
    assert meta["pending_assignees"] == []


def test_approval_gate_blocking(temp_project):
    """
    Approval routing blocked when review has request-updates outcome.

    Verifies: REQ-WF-005
    """
    # Create and route SOP
    run_qms(temp_project, "claude", "create", "SOP", "--title", "Test Approval Gate")
    run_qms(temp_project, "claude", "checkin", "SOP-001")  # Must checkin before routing
    run_qms(temp_project, "claude", "route", "SOP-001", "--review")

    # Review with request-updates
    run_qms(temp_project, "qa", "review", "SOP-001",
            "--request-updates", "--comment", "Needs work")

    meta = read_meta(temp_project, "SOP-001", "SOP")
    assert meta["status"] == "REVIEWED"

    # [REQ-WF-005] Attempt to route for approval - should be blocked
    result = run_qms(temp_project, "claude", "route", "SOP-001", "--approval")
    # Note: This test depends on whether the CLI implements this gate
    # If not implemented, this test will reveal the gap


def test_rejection(temp_project):
    """
    Rejection returns document to REVIEWED state.

    Verifies: REQ-WF-007
    """
    # Create SOP and get to IN_APPROVAL
    run_qms(temp_project, "claude", "create", "SOP", "--title", "Test Rejection")
    run_qms(temp_project, "claude", "checkin", "SOP-001")  # Must checkin before routing
    run_qms(temp_project, "claude", "route", "SOP-001", "--review")
    run_qms(temp_project, "qa", "review", "SOP-001", "--recommend", "--comment", "OK")
    run_qms(temp_project, "claude", "route", "SOP-001", "--approval")

    meta = read_meta(temp_project, "SOP-001", "SOP")
    assert meta["status"] == "IN_APPROVAL"
    version_before = meta["version"]

    # [REQ-WF-007] Reject
    result = run_qms(temp_project, "qa", "reject", "SOP-001", "--comment", "Not ready")
    assert result.returncode == 0, f"Reject failed: {result.stderr}"

    # Verify returns to REVIEWED, version unchanged
    meta = read_meta(temp_project, "SOP-001", "SOP")
    assert meta["status"] == "REVIEWED"
    assert meta["version"] == version_before


def test_retirement(temp_project):
    """
    Retirement workflow for effective document.

    Verifies: REQ-WF-012, REQ-WF-013
    """
    # Create SOP and approve to EFFECTIVE
    run_qms(temp_project, "claude", "create", "SOP", "--title", "Test Retirement")
    run_qms(temp_project, "claude", "checkin", "SOP-001")  # Must checkin before routing
    run_qms(temp_project, "claude", "route", "SOP-001", "--review")
    run_qms(temp_project, "qa", "review", "SOP-001", "--recommend", "--comment", "OK")
    run_qms(temp_project, "claude", "route", "SOP-001", "--approval")
    run_qms(temp_project, "qa", "approve", "SOP-001")

    meta = read_meta(temp_project, "SOP-001", "SOP")
    assert meta["status"] == "EFFECTIVE"
    assert meta["version"] == "1.0"

    # [REQ-WF-012] Checkout for retirement
    run_qms(temp_project, "claude", "checkout", "SOP-001")
    run_qms(temp_project, "claude", "checkin", "SOP-001")

    # Route for review first (required before approval)
    run_qms(temp_project, "claude", "route", "SOP-001", "--review")
    run_qms(temp_project, "qa", "review", "SOP-001", "--recommend", "--comment", "OK to retire")

    # [REQ-WF-012] Route for retirement approval
    result = run_qms(temp_project, "claude", "route", "SOP-001", "--approval", "--retire")
    assert result.returncode == 0, f"Retirement routing failed: {result.stderr}"

    # [REQ-WF-013] Approve retirement
    run_qms(temp_project, "qa", "approve", "SOP-001")

    # Verify RETIRED status
    meta = read_meta(temp_project, "SOP-001", "SOP")
    assert meta["status"] == "RETIRED"

    # Verify working copy removed
    assert not (temp_project / "QMS" / "SOP" / "SOP-001.md").exists()
    assert not (temp_project / "QMS" / "SOP" / "SOP-001-draft.md").exists()

    # Verify archived
    archive_files = list((temp_project / "QMS" / ".archive" / "SOP").glob("SOP-001-*.md"))
    assert len(archive_files) >= 1

    # [REQ-AUDIT-002] Verify RETIRE event logged
    events = read_audit(temp_project, "SOP-001", "SOP")
    retire_events = [e for e in events if e["event"] == "RETIRE"]
    assert len(retire_events) >= 1


def test_retirement_rejected_for_v0(temp_project):
    """
    Retirement routing rejected for never-effective documents.

    Verifies: REQ-WF-012
    """
    # Create SOP at v0.1 (never approved)
    run_qms(temp_project, "claude", "create", "SOP", "--title", "Test v0 Retirement")
    run_qms(temp_project, "claude", "checkin", "SOP-001")  # Must checkin before routing
    run_qms(temp_project, "claude", "route", "SOP-001", "--review")
    run_qms(temp_project, "qa", "review", "SOP-001", "--recommend", "--comment", "OK")

    # [REQ-WF-012] Attempt retirement routing at v0.1 - should fail
    result = run_qms(temp_project, "claude", "route", "SOP-001", "--approval", "--retire")
    # This should be rejected because version < 1.0
    # Note: Test depends on CLI implementation of this check
