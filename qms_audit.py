"""
QMS Audit Module - Append-Only Audit Trail Management

Handles reading and appending to .audit/ JSONL files for document history.
These logs are append-only and provide complete audit trail for GMP compliance.
"""

import json
from pathlib import Path
from typing import Any, Dict, List, Optional
from datetime import datetime, timezone

from qms_paths import QMS_ROOT, require_project_root


def get_audit_root() -> Path:
    """Get the .audit root directory, ensuring project is initialized."""
    require_project_root()
    return QMS_ROOT / ".audit"


# Event types
EVENT_CREATE = "CREATE"
EVENT_CHECKOUT = "CHECKOUT"
EVENT_CHECKIN = "CHECKIN"
EVENT_ROUTE_REVIEW = "ROUTE_REVIEW"
EVENT_ROUTE_APPROVAL = "ROUTE_APPROVAL"
EVENT_ASSIGN = "ASSIGN"  # CR-036-VAR-005
EVENT_REVIEW = "REVIEW"
EVENT_APPROVE = "APPROVE"
EVENT_REJECT = "REJECT"
EVENT_EFFECTIVE = "EFFECTIVE"
EVENT_RELEASE = "RELEASE"
EVENT_REVERT = "REVERT"
EVENT_CLOSE = "CLOSE"
EVENT_RETIRE = "RETIRE"
EVENT_STATUS_CHANGE = "STATUS_CHANGE"


def get_audit_dir(doc_type: str) -> Path:
    """Get the .audit directory for a document type."""
    return get_audit_root() / doc_type


def get_audit_path(doc_id: str, doc_type: str) -> Path:
    """Get the .audit file path for a document."""
    audit_dir = get_audit_dir(doc_type)
    return audit_dir / f"{doc_id}.jsonl"


def ensure_audit_dir(doc_type: str) -> Path:
    """Ensure the .audit directory exists for a document type."""
    audit_dir = get_audit_dir(doc_type)
    audit_dir.mkdir(parents=True, exist_ok=True)
    return audit_dir


def get_timestamp() -> str:
    """Get current UTC timestamp in ISO format."""
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def append_audit_event(doc_id: str, doc_type: str, event: Dict[str, Any]) -> bool:
    """
    Append an audit event to the document's audit log.

    Args:
        doc_id: Document identifier
        doc_type: Document type
        event: Event data (will have timestamp added if not present)

    Returns True on success, False on failure.
    """
    ensure_audit_dir(doc_type)
    audit_path = get_audit_path(doc_id, doc_type)

    # Ensure timestamp is present
    if "ts" not in event:
        event["ts"] = get_timestamp()

    try:
        with open(audit_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(event, ensure_ascii=False) + "\n")
        return True
    except IOError as e:
        print(f"Error: Failed to append audit event to {audit_path}: {e}")
        return False


def read_audit_log(doc_id: str, doc_type: str) -> List[Dict[str, Any]]:
    """
    Read all audit events for a document.

    Returns empty list if file doesn't exist.
    """
    audit_path = get_audit_path(doc_id, doc_type)
    if not audit_path.exists():
        return []

    events = []
    try:
        with open(audit_path, "r", encoding="utf-8") as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                if not line:
                    continue
                try:
                    events.append(json.loads(line))
                except json.JSONDecodeError as e:
                    print(f"Warning: Invalid JSON on line {line_num} in {audit_path}: {e}")
    except IOError as e:
        print(f"Error: Failed to read audit log {audit_path}: {e}")

    return events


def get_comments(
    doc_id: str,
    doc_type: str,
    version: Optional[str] = None,
    event_types: Optional[List[str]] = None
) -> List[Dict[str, Any]]:
    """
    Get review/approval comments from audit log.

    Args:
        doc_id: Document identifier
        doc_type: Document type
        version: Filter by version (e.g., "0.1", "1.1"). None for all versions.
        event_types: Filter by event types. Default: REVIEW, REJECT

    Returns list of events that have comments.
    """
    if event_types is None:
        event_types = [EVENT_REVIEW, EVENT_REJECT]

    events = read_audit_log(doc_id, doc_type)
    comments = []

    for event in events:
        if event.get("event") not in event_types:
            continue
        if "comment" not in event or not event["comment"]:
            continue
        if version and event.get("version") != version:
            continue
        comments.append(event)

    return comments


def get_latest_version_comments(
    doc_id: str,
    doc_type: str,
    current_version: str
) -> List[Dict[str, Any]]:
    """
    Get comments for the current version only.

    Used by qms comments command.
    """
    return get_comments(doc_id, doc_type, version=current_version)


# Event creation helpers

def create_event(
    event_type: str,
    user: str,
    version: str,
    **kwargs
) -> Dict[str, Any]:
    """Create a base audit event."""
    event = {
        "ts": get_timestamp(),
        "event": event_type,
        "user": user,
        "version": version
    }
    event.update(kwargs)
    return event


def log_create(doc_id: str, doc_type: str, user: str, version: str, title: str) -> bool:
    """Log document creation."""
    event = create_event(EVENT_CREATE, user, version, title=title)
    return append_audit_event(doc_id, doc_type, event)


def log_checkout(doc_id: str, doc_type: str, user: str, version: str, from_version: Optional[str] = None) -> bool:
    """Log document checkout."""
    kwargs = {}
    if from_version:
        kwargs["from_version"] = from_version
    event = create_event(EVENT_CHECKOUT, user, version, **kwargs)
    return append_audit_event(doc_id, doc_type, event)


def log_checkin(doc_id: str, doc_type: str, user: str, version: str) -> bool:
    """Log document checkin."""
    event = create_event(EVENT_CHECKIN, user, version)
    return append_audit_event(doc_id, doc_type, event)


def log_route_review(
    doc_id: str,
    doc_type: str,
    user: str,
    version: str,
    assignees: List[str],
    review_type: str = "REVIEW"
) -> bool:
    """Log routing for review."""
    event = create_event(
        EVENT_ROUTE_REVIEW, user, version,
        assignees=assignees,
        review_type=review_type
    )
    return append_audit_event(doc_id, doc_type, event)


def log_route_approval(
    doc_id: str,
    doc_type: str,
    user: str,
    version: str,
    assignees: List[str],
    approval_type: str = "APPROVAL"
) -> bool:
    """Log routing for approval."""
    event = create_event(
        EVENT_ROUTE_APPROVAL, user, version,
        assignees=assignees,
        approval_type=approval_type
    )
    return append_audit_event(doc_id, doc_type, event)


def log_assign(
    doc_id: str,
    doc_type: str,
    user: str,
    version: str,
    assignees: List[str]
) -> bool:
    """Log reviewer assignment (CR-036-VAR-005)."""
    event = create_event(EVENT_ASSIGN, user, version, assignees=assignees)
    return append_audit_event(doc_id, doc_type, event)


def log_review(
    doc_id: str,
    doc_type: str,
    user: str,
    version: str,
    outcome: str,
    comment: str
) -> bool:
    """Log review completion."""
    event = create_event(
        EVENT_REVIEW, user, version,
        outcome=outcome,
        comment=comment
    )
    return append_audit_event(doc_id, doc_type, event)


def log_approve(doc_id: str, doc_type: str, user: str, version: str) -> bool:
    """Log approval."""
    event = create_event(EVENT_APPROVE, user, version)
    return append_audit_event(doc_id, doc_type, event)


def log_reject(doc_id: str, doc_type: str, user: str, version: str, comment: str) -> bool:
    """Log rejection."""
    event = create_event(EVENT_REJECT, user, version, comment=comment)
    return append_audit_event(doc_id, doc_type, event)


def log_effective(doc_id: str, doc_type: str, user: str, old_version: str, new_version: str) -> bool:
    """Log document becoming effective."""
    event = create_event(
        EVENT_EFFECTIVE, user, new_version,
        from_version=old_version
    )
    return append_audit_event(doc_id, doc_type, event)


def log_release(doc_id: str, doc_type: str, user: str, version: str) -> bool:
    """Log executable document release."""
    event = create_event(EVENT_RELEASE, user, version)
    return append_audit_event(doc_id, doc_type, event)


def log_revert(doc_id: str, doc_type: str, user: str, version: str, reason: str) -> bool:
    """Log revert to execution."""
    event = create_event(EVENT_REVERT, user, version, reason=reason)
    return append_audit_event(doc_id, doc_type, event)


def log_close(doc_id: str, doc_type: str, user: str, version: str) -> bool:
    """Log executable document closure."""
    event = create_event(EVENT_CLOSE, user, version)
    return append_audit_event(doc_id, doc_type, event)


def log_retire(doc_id: str, doc_type: str, user: str, from_version: str, to_version: str) -> bool:
    """Log document retirement."""
    event = create_event(EVENT_RETIRE, user, to_version, from_version=from_version)
    return append_audit_event(doc_id, doc_type, event)


def log_status_change(
    doc_id: str,
    doc_type: str,
    user: str,
    version: str,
    from_status: str,
    to_status: str
) -> bool:
    """Log generic status change."""
    event = create_event(
        EVENT_STATUS_CHANGE, user, version,
        from_status=from_status,
        to_status=to_status
    )
    return append_audit_event(doc_id, doc_type, event)


def format_audit_history(events: List[Dict[str, Any]]) -> str:
    """
    Format audit events for display.

    Returns human-readable history.
    """
    if not events:
        return "No audit history found."

    lines = []
    for event in events:
        ts = event.get("ts", "?")
        event_type = event.get("event", "?")
        user = event.get("user", "?")
        version = event.get("version", "?")

        # Format based on event type
        if event_type == EVENT_CREATE:
            title = event.get("title", "")
            lines.append(f"[{ts}] CREATE by {user} - v{version} - \"{title}\"")

        elif event_type == EVENT_CHECKOUT:
            from_ver = event.get("from_version")
            if from_ver:
                lines.append(f"[{ts}] CHECKOUT by {user} - v{version} (from v{from_ver})")
            else:
                lines.append(f"[{ts}] CHECKOUT by {user} - v{version}")

        elif event_type == EVENT_CHECKIN:
            lines.append(f"[{ts}] CHECKIN by {user} - v{version}")

        elif event_type == EVENT_ROUTE_REVIEW:
            assignees = ", ".join(event.get("assignees", []))
            review_type = event.get("review_type", "REVIEW")
            lines.append(f"[{ts}] ROUTE {review_type} by {user} - v{version} - to: {assignees}")

        elif event_type == EVENT_ROUTE_APPROVAL:
            assignees = ", ".join(event.get("assignees", []))
            approval_type = event.get("approval_type", "APPROVAL")
            lines.append(f"[{ts}] ROUTE {approval_type} by {user} - v{version} - to: {assignees}")

        elif event_type == EVENT_REVIEW:
            outcome = event.get("outcome", "?")
            comment = event.get("comment", "")
            lines.append(f"[{ts}] REVIEW by {user} - v{version} - {outcome}")
            if comment:
                # Indent comment
                for line in comment.split("\n"):
                    lines.append(f"    {line}")

        elif event_type == EVENT_APPROVE:
            lines.append(f"[{ts}] APPROVE by {user} - v{version}")

        elif event_type == EVENT_REJECT:
            comment = event.get("comment", "")
            lines.append(f"[{ts}] REJECT by {user} - v{version}")
            if comment:
                for line in comment.split("\n"):
                    lines.append(f"    {line}")

        elif event_type == EVENT_EFFECTIVE:
            from_ver = event.get("from_version", "?")
            lines.append(f"[{ts}] EFFECTIVE - v{from_ver} -> v{version}")

        elif event_type == EVENT_RELEASE:
            lines.append(f"[{ts}] RELEASE by {user} - v{version}")

        elif event_type == EVENT_REVERT:
            reason = event.get("reason", "")
            lines.append(f"[{ts}] REVERT by {user} - v{version}")
            if reason:
                lines.append(f"    Reason: {reason}")

        elif event_type == EVENT_CLOSE:
            lines.append(f"[{ts}] CLOSE by {user} - v{version}")

        elif event_type == EVENT_RETIRE:
            from_ver = event.get("from_version", "?")
            lines.append(f"[{ts}] RETIRE by {user} - v{from_ver} -> v{version} (RETIRED)")

        elif event_type == EVENT_STATUS_CHANGE:
            from_status = event.get("from_status", "?")
            to_status = event.get("to_status", "?")
            lines.append(f"[{ts}] STATUS by {user} - v{version} - {from_status} -> {to_status}")

        else:
            lines.append(f"[{ts}] {event_type} by {user} - v{version}")

    return "\n".join(lines)


def format_comments(comments: List[Dict[str, Any]]) -> str:
    """
    Format comments for display.

    Returns human-readable comment list.
    """
    if not comments:
        return "No comments found."

    lines = []
    for event in comments:
        ts = event.get("ts", "?")
        user = event.get("user", "?")
        version = event.get("version", "?")
        event_type = event.get("event", "?")
        outcome = event.get("outcome", "")
        comment = event.get("comment", "")

        header = f"[v{version}] {user}"
        if event_type == EVENT_REVIEW:
            header += f" ({outcome})"
        elif event_type == EVENT_REJECT:
            header += " (REJECTED)"

        lines.append(f"--- {header} - {ts} ---")
        lines.append(comment)
        lines.append("")

    return "\n".join(lines)
