"""
QMS CLI Qualification Tests: Audit Event Completeness

Verifies all 16 audit event types defined in REQ-AUDIT-002 are logged
during comprehensive document lifecycle operations.

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


def collect_event_types(events):
    """Extract unique event type strings from a list of audit events."""
    return {e["event"] for e in events}


# ============================================================================
# Test: All 16 Audit Event Types (REQ-AUDIT-002)
# ============================================================================

def test_all_audit_event_types(temp_project):
    """
    Verify all 16 audit event types are logged during comprehensive lifecycle.

    Exercises two document types (SOP for EFFECTIVE/RETIRE, CR for executable
    workflow events) to cover every audit event type defined in REQ-AUDIT-002.

    The 16 event types:
    CREATE, CHECKOUT, CHECKIN, ROUTE_REVIEW, ROUTE_APPROVAL, ASSIGN,
    REVIEW, APPROVE, REJECT, EFFECTIVE, RELEASE, REVERT, CLOSE, RETIRE,
    STATUS_CHANGE, WITHDRAW

    Verifies: REQ-AUDIT-002
    """
    all_event_types = set()

    # --- SOP lifecycle: EFFECTIVE and RETIRE ---

    # Create SOP, get to EFFECTIVE
    result = run_qms(temp_project, "claude", "create", "SOP", "--title", "Audit SOP")
    assert result.returncode == 0, f"SOP create failed: {result.stderr}"
    run_qms(temp_project, "claude", "checkin", "SOP-001")
    run_qms(temp_project, "claude", "route", "SOP-001", "--review")
    run_qms(temp_project, "qa", "review", "SOP-001", "--recommend", "--comment", "OK")
    run_qms(temp_project, "claude", "route", "SOP-001", "--approval")
    result = run_qms(temp_project, "qa", "approve", "SOP-001")
    assert result.returncode == 0, f"SOP approve failed: {result.stderr}"

    # SOP-001 is now EFFECTIVE v1.0
    meta = read_meta(temp_project, "SOP-001", "SOP")
    assert meta["status"] == "EFFECTIVE"

    # Retire the SOP: checkout, review cycle, then approve with --retire
    run_qms(temp_project, "claude", "checkout", "SOP-001")
    run_qms(temp_project, "claude", "checkin", "SOP-001")
    run_qms(temp_project, "claude", "route", "SOP-001", "--review")
    run_qms(temp_project, "qa", "review", "SOP-001", "--recommend", "--comment", "Retirement OK")
    result = run_qms(temp_project, "claude", "route", "SOP-001", "--approval", "--retire")
    assert result.returncode == 0, f"SOP retire routing failed: {result.stderr}"
    result = run_qms(temp_project, "qa", "approve", "SOP-001")
    assert result.returncode == 0, f"SOP retire approve failed: {result.stderr}"

    sop_events = read_audit(temp_project, "SOP-001", "SOP")
    all_event_types.update(collect_event_types(sop_events))

    # --- CR lifecycle: ASSIGN, WITHDRAW, REJECT, RELEASE, REVERT, CLOSE ---

    result = run_qms(temp_project, "claude", "create", "CR", "--title", "Audit CR")
    assert result.returncode == 0, f"CR create failed: {result.stderr}"
    run_qms(temp_project, "claude", "checkin", "CR-001")

    # Route for review, assign additional reviewer, then withdraw
    run_qms(temp_project, "claude", "route", "CR-001", "--review")
    result = run_qms(temp_project, "qa", "assign", "CR-001", "--assignees", "tu_ui")
    assert result.returncode == 0, f"CR assign failed: {result.stderr}"
    result = run_qms(temp_project, "claude", "withdraw", "CR-001")
    assert result.returncode == 0, f"CR withdraw failed: {result.stderr}"

    # Route review again, complete review, route approval
    run_qms(temp_project, "claude", "route", "CR-001", "--review")
    run_qms(temp_project, "qa", "review", "CR-001", "--recommend", "--comment", "OK")
    run_qms(temp_project, "claude", "route", "CR-001", "--approval")

    # Reject from approval
    result = run_qms(temp_project, "qa", "reject", "CR-001", "--comment", "Needs changes")
    assert result.returncode == 0, f"CR reject failed: {result.stderr}"

    # Re-route for approval and approve
    run_qms(temp_project, "claude", "route", "CR-001", "--approval")
    run_qms(temp_project, "qa", "approve", "CR-001")

    # Release: PRE_APPROVED -> IN_EXECUTION
    result = run_qms(temp_project, "claude", "release", "CR-001")
    assert result.returncode == 0, f"CR release failed: {result.stderr}"

    # Post-review cycle to get POST_REVIEWED, then revert
    run_qms(temp_project, "claude", "checkout", "CR-001")
    run_qms(temp_project, "claude", "checkin", "CR-001")
    run_qms(temp_project, "claude", "route", "CR-001", "--review")
    run_qms(temp_project, "qa", "review", "CR-001", "--recommend", "--comment", "OK")

    # Revert: POST_REVIEWED -> IN_EXECUTION
    result = run_qms(temp_project, "claude", "revert", "CR-001", "--reason", "Need more execution work")
    assert result.returncode == 0, f"CR revert failed: {result.stderr}"

    # Complete post-review/post-approval cycle to CLOSE
    run_qms(temp_project, "claude", "checkout", "CR-001")
    run_qms(temp_project, "claude", "checkin", "CR-001")
    run_qms(temp_project, "claude", "route", "CR-001", "--review")
    run_qms(temp_project, "qa", "review", "CR-001", "--recommend", "--comment", "OK")
    run_qms(temp_project, "claude", "route", "CR-001", "--approval")
    run_qms(temp_project, "qa", "approve", "CR-001")

    # Close: POST_APPROVED -> CLOSED
    result = run_qms(temp_project, "claude", "close", "CR-001")
    assert result.returncode == 0, f"CR close failed: {result.stderr}"

    cr_events = read_audit(temp_project, "CR-001", "CR")
    all_event_types.update(collect_event_types(cr_events))

    # --- Verify all 16 event types present ---
    expected_events = {
        "CREATE", "CHECKOUT", "CHECKIN",
        "ROUTE_REVIEW", "ROUTE_APPROVAL",
        "ASSIGN", "REVIEW", "APPROVE", "REJECT",
        "EFFECTIVE", "RELEASE", "REVERT",
        "CLOSE", "RETIRE",
        "STATUS_CHANGE", "WITHDRAW",
    }

    missing = expected_events - all_event_types
    assert not missing, (
        f"Missing audit event types: {missing}\n"
        f"Found: {sorted(all_event_types)}\n"
        f"Expected: {sorted(expected_events)}"
    )
    assert len(expected_events) == 16, "REQ-AUDIT-002 requires exactly 16 event types"


def test_audit_event_constants_match_requirement(temp_project):
    """
    Verify qms_audit module defines exactly the 16 event types per REQ-AUDIT-002.

    Verifies: REQ-AUDIT-002
    """
    # Add qms-cli to path
    qms_cli_dir = Path(__file__).parent.parent.parent
    if str(qms_cli_dir) not in sys.path:
        sys.path.insert(0, str(qms_cli_dir))

    import qms_audit

    # Collect all EVENT_* constants
    event_constants = {
        name: getattr(qms_audit, name)
        for name in dir(qms_audit)
        if name.startswith("EVENT_")
    }

    expected = {
        "EVENT_CREATE": "CREATE",
        "EVENT_CHECKOUT": "CHECKOUT",
        "EVENT_CHECKIN": "CHECKIN",
        "EVENT_ROUTE_REVIEW": "ROUTE_REVIEW",
        "EVENT_ROUTE_APPROVAL": "ROUTE_APPROVAL",
        "EVENT_ASSIGN": "ASSIGN",
        "EVENT_REVIEW": "REVIEW",
        "EVENT_APPROVE": "APPROVE",
        "EVENT_REJECT": "REJECT",
        "EVENT_EFFECTIVE": "EFFECTIVE",
        "EVENT_RELEASE": "RELEASE",
        "EVENT_REVERT": "REVERT",
        "EVENT_CLOSE": "CLOSE",
        "EVENT_RETIRE": "RETIRE",
        "EVENT_STATUS_CHANGE": "STATUS_CHANGE",
        "EVENT_WITHDRAW": "WITHDRAW",
    }

    assert event_constants == expected, (
        f"Audit event constants mismatch.\n"
        f"Missing: {set(expected) - set(event_constants)}\n"
        f"Extra: {set(event_constants) - set(expected)}"
    )
