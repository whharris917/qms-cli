"""
QMS Withdraw Command

Withdraws a document from an in-progress review or approval workflow.

Created as part of CR-048: Workflow Improvements
"""
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from registry import CommandRegistry
from qms_config import Status
from qms_paths import USERS_ROOT, get_doc_type, get_doc_path
from qms_auth import get_current_user, verify_user_identity
from qms_meta import read_meta, write_meta
from qms_audit import log_withdraw


# REQ-WF-018: Withdraw status transitions
WITHDRAW_TRANSITIONS = {
    Status.IN_REVIEW: Status.DRAFT,
    Status.IN_APPROVAL: Status.REVIEWED,
    Status.IN_PRE_REVIEW: Status.DRAFT,
    Status.IN_PRE_APPROVAL: Status.PRE_REVIEWED,
    Status.IN_POST_REVIEW: Status.IN_EXECUTION,
    Status.IN_POST_APPROVAL: Status.POST_REVIEWED,
}


@CommandRegistry.register(
    name="withdraw",
    help="Withdraw a document from review or approval workflow",
    requires_doc_id=True,
    doc_id_help="Document ID to withdraw",
)
def cmd_withdraw(args) -> int:
    """Withdraw a document from an in-progress review or approval workflow."""
    doc_id = args.doc_id
    user = get_current_user(args)

    if not verify_user_identity(user):
        return 1

    # Note: REQ-WF-018 specifies that only the responsible_user may withdraw.
    # We check ownership directly rather than group permissions.

    draft_path = get_doc_path(doc_id, draft=True)
    if not draft_path.exists():
        print(f"""
Error: No draft found for {doc_id}.

Check document status: qms --user {user} status {doc_id}
""")
        return 1

    # Get workflow state from .meta (authoritative source)
    doc_type = get_doc_type(doc_id)
    meta = read_meta(doc_id, doc_type) or {}
    current_status = Status(meta.get("status", "DRAFT"))
    version = meta.get("version", "0.1")

    # Check ownership - only responsible_user may withdraw
    doc_owner = meta.get("responsible_user")
    if doc_owner != user:
        print(f"""
Error: Only the document owner can withdraw.

{doc_id} is owned by: {doc_owner or 'no one'}
You are: {user}
""")
        return 1

    # Verify document is in a withdrawable state
    if current_status not in WITHDRAW_TRANSITIONS:
        print(f"""
Error: {doc_id} is not in a withdrawable state.

Current status: {current_status.value}

Withdraw is only valid for documents in review or approval workflows:
- IN_REVIEW, IN_APPROVAL (non-executable)
- IN_PRE_REVIEW, IN_PRE_APPROVAL (executable pre-release)
- IN_POST_REVIEW, IN_POST_APPROVAL (executable post-release)
""")
        return 1

    # Get target status
    new_status = WITHDRAW_TRANSITIONS[current_status]

    # Get pending assignees before clearing (for inbox cleanup)
    pending_assignees = meta.get("pending_assignees", [])

    # Log WITHDRAW event to audit trail
    log_withdraw(doc_id, doc_type, user, version, current_status.value, new_status.value)

    # Update .meta file
    meta["status"] = new_status.value
    meta["pending_assignees"] = []
    # Clear review tracking fields
    meta["completed_reviewers"] = []
    meta["review_outcomes"] = {}
    write_meta(doc_id, doc_type, meta)

    # Remove inbox tasks for all assignees
    # Task naming pattern: task-{doc_id}-{workflow_type}-v{version}.md
    workflow_keywords = ["review", "approval", "pre_review", "pre_approval", "post_review", "post_approval"]
    for user_dir in USERS_ROOT.iterdir():
        if user_dir.is_dir():
            inbox = user_dir / "inbox"
            if inbox.exists():
                for keyword in workflow_keywords:
                    for task_file in inbox.glob(f"task-{doc_id}-{keyword}*.md"):
                        task_file.unlink()

    print(f"Withdrawn: {doc_id}")
    print(f"Status: {current_status.value} -> {new_status.value}")

    return 0
