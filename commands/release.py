"""
QMS Release Command

Releases an executable document for execution.

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
from qms_audit import log_release, log_status_change


@CommandRegistry.register(
    name="release",
    help="Release an executable document for execution",
    requires_doc_id=True,
    doc_id_help="Document ID to release",
)
def cmd_release(args) -> int:
    """Release an executable document for execution."""
    doc_id = args.doc_id
    user = get_current_user(args)

    if not verify_user_identity(user):
        return 1

    # Permission check (group level)
    allowed, error = check_permission(user, "release")
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

Only executable documents (CR, INV, CAPA, TP, ER) can be released.
Non-executable documents (SOP, RS, DS, etc.) become EFFECTIVE after approval.
""")
        return 1

    # Check ownership
    doc_owner = meta.get("responsible_user")
    allowed, error = check_permission(user, "release", doc_owner=doc_owner)
    if not allowed:
        print(error)
        return 1

    if current_status != Status.PRE_APPROVED:
        print(f"""
Error: {doc_id} must be PRE_APPROVED to release.

Current status: {current_status.value}

Workflow for executable documents:
  DRAFT -> IN_PRE_REVIEW -> PRE_REVIEWED -> IN_PRE_APPROVAL -> PRE_APPROVED -> release -> IN_EXECUTION
""")
        return 1

    # Log RELEASE event to audit trail
    log_release(doc_id, doc_type, user, version)

    # Log status change (CAPA-3: audit trail completeness)
    log_status_change(doc_id, doc_type, user, version, Status.PRE_APPROVED.value, Status.IN_EXECUTION.value)

    # Update .meta file
    meta["status"] = Status.IN_EXECUTION.value
    # CAPA-4: Set execution_phase to post_release on release
    meta["execution_phase"] = "post_release"
    write_meta(doc_id, doc_type, meta)

    print(f"Released: {doc_id}")
    print(f"Status: PRE_APPROVED -> IN_EXECUTION")

    return 0
