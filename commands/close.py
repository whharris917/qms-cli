"""
QMS Close Command

Closes an executable document.

Created as part of CR-026: QMS CLI Extensibility Refactoring
"""
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from registry import CommandRegistry
from qms_config import Status
from qms_paths import PROJECT_ROOT, get_doc_type, get_doc_path, get_workspace_path
from qms_io import read_document, write_document_minimal
from qms_auth import get_current_user, check_permission, verify_user_identity
from qms_meta import read_meta, write_meta
from qms_audit import log_close, log_status_change


@CommandRegistry.register(
    name="close",
    help="Close an executable document",
    requires_doc_id=True,
    doc_id_help="Document ID to close",
)
def cmd_close(args) -> int:
    """Close an executable document."""
    doc_id = args.doc_id
    user = get_current_user(args)

    if not verify_user_identity(user):
        return 1

    # Permission check (group level)
    allowed, error = check_permission(user, "close")
    if not allowed:
        print(error)
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
    is_executable = meta.get("executable", False)

    if not is_executable:
        print(f"""
Error: {doc_id} is not an executable document.

Only executable documents (CR, INV, CAPA, TP, ER) can be closed.
Non-executable documents (SOP, RS, DS, etc.) become EFFECTIVE after approval.
""")
        return 1

    # Check ownership
    doc_owner = meta.get("responsible_user")
    allowed, error = check_permission(user, "close", doc_owner=doc_owner)
    if not allowed:
        print(error)
        return 1

    if current_status != Status.POST_APPROVED:
        print(f"""
Error: {doc_id} must be POST_APPROVED to close.

Current status: {current_status.value}

Workflow for executable documents:
  ... -> IN_POST_REVIEW -> POST_REVIEWED -> IN_POST_APPROVAL -> POST_APPROVED -> close -> CLOSED
""")
        return 1

    # Move to effective location with minimal frontmatter
    frontmatter, body = read_document(draft_path)
    effective_path = get_doc_path(doc_id, draft=False)
    write_document_minimal(effective_path, frontmatter, body)
    draft_path.unlink()

    # Log CLOSE event to audit trail
    log_close(doc_id, doc_type, user, version)

    # Log status change (CAPA-3: audit trail completeness)
    log_status_change(doc_id, doc_type, user, version, current_status.value, Status.CLOSED.value)

    # Update .meta file (clear ownership on close)
    meta["status"] = Status.CLOSED.value
    meta["responsible_user"] = None
    meta["checked_out"] = False
    meta["checked_out_date"] = None
    meta["pending_assignees"] = []
    write_meta(doc_id, doc_type, meta)

    # Remove from workspace
    workspace_path = get_workspace_path(user, doc_id)
    if workspace_path.exists():
        workspace_path.unlink()

    print(f"Closed: {doc_id}")
    print(f"Location: {effective_path.relative_to(PROJECT_ROOT)}")

    return 0
