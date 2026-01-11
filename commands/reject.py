"""
QMS Reject Command

Rejects a document.

Created as part of CR-026: QMS CLI Extensibility Refactoring
"""
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from registry import CommandRegistry
from qms_config import Status
from qms_paths import USERS_ROOT, get_doc_type, get_doc_path
from qms_auth import get_current_user, check_permission, verify_user_identity
from qms_meta import read_meta, write_meta, update_meta_approval
from qms_audit import log_reject, log_status_change
from workflow import get_workflow_engine


@CommandRegistry.register(
    name="reject",
    help="Reject a document",
    requires_doc_id=True,
    doc_id_help="Document ID to reject",
    arguments=[
        {"flags": ["--comment"], "help": "Rejection reason", "required": False},
    ],
)
def cmd_reject(args) -> int:
    """Reject a document."""
    doc_id = args.doc_id
    user = get_current_user(args)

    if not verify_user_identity(user):
        return 1

    # Permission check (group level)
    allowed, error = check_permission(user, "reject")
    if not allowed:
        print(error)
        return 1

    comment = args.comment

    if not comment:
        print(f"""
Error: Must provide --comment with rejection.

Usage:
  qms --user {user} reject DOC-ID --comment "Reason for rejection"

The comment should explain why the document is being rejected
and what changes are needed before re-submission.
""")
        return 1

    draft_path = get_doc_path(doc_id, draft=True)
    if not draft_path.exists():
        print(f"""
Error: No draft found for {doc_id}.

Check your inbox for assigned approval tasks: qms --user {user} inbox
Check document status: qms --user {user} status {doc_id}
""")
        return 1

    # Get workflow state from .meta (authoritative source)
    doc_type = get_doc_type(doc_id)
    meta = read_meta(doc_id, doc_type) or {}
    current_status = Status(meta.get("status", "DRAFT"))
    version = meta.get("version", "0.1")
    pending_assignees = meta.get("pending_assignees", [])

    # Use WorkflowEngine to verify document is in an approval state (CR-026)
    engine = get_workflow_engine()
    if not engine.is_approval_status(current_status):
        print(f"""
Error: {doc_id} is not in approval.

Current status: {current_status.value}

Documents can only be rejected when in an approval state.
Check document status: qms --user {user} status {doc_id}
""")
        return 1

    # Check if user is assigned to approve
    if user not in pending_assignees:
        print(f"Error: You are not assigned to approve {doc_id}")
        return 1

    # Log REJECT event to audit trail (comment goes here)
    log_reject(doc_id, doc_type, user, version, comment)

    # Transition back to REVIEWED state using WorkflowEngine (CR-026)
    new_status = engine.get_rejection_target(current_status)

    if new_status:
        print(f"Document rejected. Status: {current_status.value} -> {new_status.value}")
        # Log status change (CAPA-3: audit trail completeness)
        log_status_change(doc_id, doc_type, user, version, current_status.value, new_status.value)

    # Update .meta file
    meta = update_meta_approval(meta, new_status=new_status.value if new_status else None)
    meta["pending_assignees"] = []  # Clear pending assignees on rejection
    write_meta(doc_id, doc_type, meta)

    # Remove all pending approval tasks for this document
    for user_dir in USERS_ROOT.iterdir():
        if user_dir.is_dir():
            inbox = user_dir / "inbox"
            if inbox.exists():
                for task_file in inbox.glob(f"task-{doc_id}-*approval*.md"):
                    task_file.unlink()

    print(f"Rejected: {doc_id}")
    print(f"Reason: {comment}")

    return 0
