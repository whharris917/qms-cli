"""
QMS Revert Command

Reverts an executable document back to execution.

Created as part of CR-026: QMS CLI Extensibility Refactoring
"""
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from registry import CommandRegistry
from qms_config import Status
from qms_paths import get_doc_type, get_doc_path
from qms_auth import get_current_user, check_permission, verify_user_identity
from qms_meta import read_meta, write_meta
from qms_audit import log_revert


@CommandRegistry.register(
    name="revert",
    help="Revert an executable document back to execution",
    requires_doc_id=True,
    doc_id_help="Document ID to revert",
    arguments=[
        {"flags": ["--reason"], "help": "Reason for reverting"},
    ],
)
def cmd_revert(args) -> int:
    """Revert an executable document back to execution."""
    doc_id = args.doc_id
    user = get_current_user(args)

    if not verify_user_identity(user):
        return 1

    # Permission check (group level)
    allowed, error = check_permission(user, "revert")
    if not allowed:
        print(error)
        return 1

    reason = args.reason

    if not reason:
        print(f"""
Error: Must provide --reason for revert.

Usage:
  qms --user {user} revert DOC-ID --reason "Reason for reverting to execution"

The reason should explain why additional execution work is needed.
""")
        return 1

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

    # Check ownership
    doc_owner = meta.get("responsible_user")
    allowed, error = check_permission(user, "revert", doc_owner=doc_owner)
    if not allowed:
        print(error)
        return 1

    if current_status != Status.POST_REVIEWED:
        print(f"""
Error: {doc_id} must be POST_REVIEWED to revert.

Current status: {current_status.value}

Revert moves a document from POST_REVIEWED back to IN_EXECUTION
when additional execution work is discovered during post-review.
""")
        return 1

    # Log REVERT event to audit trail
    log_revert(doc_id, doc_type, user, version, reason)

    # Update .meta file
    meta["status"] = Status.IN_EXECUTION.value
    write_meta(doc_id, doc_type, meta)

    print(f"Reverted: {doc_id}")
    print(f"Status: POST_REVIEWED -> IN_EXECUTION")
    print(f"Reason: {reason}")

    return 0
