"""
QMS Checkin Command

Checks in a document from workspace.

Created as part of CR-026: QMS CLI Extensibility Refactoring
"""
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from registry import CommandRegistry
from qms_paths import get_doc_type, get_doc_path, get_workspace_path
from qms_io import read_document, write_document_minimal
from qms_auth import get_current_user, check_permission, verify_user_identity
from qms_meta import read_meta, write_meta, update_meta_checkin
from qms_audit import log_checkin


@CommandRegistry.register(
    name="checkin",
    help="Check in a document from workspace",
    requires_doc_id=True,
    doc_id_help="Document ID to check in",
)
def cmd_checkin(args) -> int:
    """Check in a document from workspace."""
    doc_id = args.doc_id
    user = get_current_user(args)

    if not verify_user_identity(user):
        return 1

    # Permission check (group level)
    allowed, error = check_permission(user, "checkin")
    if not allowed:
        print(error)
        return 1

    workspace_path = get_workspace_path(user, doc_id)
    if not workspace_path.exists():
        print(f"""
Error: {doc_id} not found in your workspace.

Your workspace contains documents you have checked out for editing.
To check out a document: qms --user {user} checkout {doc_id}
To see your workspace: qms --user {user} workspace
""")
        return 1

    draft_path = get_doc_path(doc_id, draft=True)
    doc_type = get_doc_type(doc_id)
    meta = read_meta(doc_id, doc_type) or {}

    # Verify user has it checked out (ownership check via .meta)
    doc_owner = meta.get("responsible_user")
    allowed, error = check_permission(user, "checkin", doc_owner=doc_owner)
    if not allowed:
        print(error)
        return 1

    # Read workspace version
    frontmatter, body = read_document(workspace_path)

    # Get version from .meta (authoritative source)
    version = meta.get("version", frontmatter.get("version", "0.1"))

    # Write content to QMS draft with minimal frontmatter
    write_document_minimal(draft_path, frontmatter, body)

    # Update .meta file
    meta = update_meta_checkin(meta)
    write_meta(doc_id, doc_type, meta)

    # Log CHECKIN event
    log_checkin(doc_id, doc_type, user, version)

    # Remove from workspace
    workspace_path.unlink()

    print(f"Checked in: {doc_id} (v{version})")

    return 0
