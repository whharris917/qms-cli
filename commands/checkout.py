"""
QMS Checkout Command

Checks out a document for editing.

Created as part of CR-026: QMS CLI Extensibility Refactoring
"""
import shutil
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from registry import CommandRegistry
from qms_paths import PROJECT_ROOT, get_doc_type, get_doc_path, get_archive_path, get_workspace_path
from qms_io import parse_frontmatter, write_document_minimal
from qms_auth import get_current_user, check_permission, verify_user_identity
from qms_meta import read_meta, write_meta, update_meta_checkout
from qms_audit import log_checkout


@CommandRegistry.register(
    name="checkout",
    help="Check out a document for editing",
    requires_doc_id=True,
    doc_id_help="Document ID to check out",
)
def cmd_checkout(args) -> int:
    """Check out a document for editing."""
    doc_id = args.doc_id
    user = get_current_user(args)

    if not verify_user_identity(user):
        return 1

    # Permission check
    allowed, error = check_permission(user, "checkout")
    if not allowed:
        print(error)
        return 1

    # Find the document (effective or draft)
    effective_path = get_doc_path(doc_id, draft=False)
    draft_path = get_doc_path(doc_id, draft=True)

    doc_type = get_doc_type(doc_id)
    meta = read_meta(doc_id, doc_type) or {}

    if draft_path.exists():
        # Already a draft - check if already checked out (from .meta)
        if meta.get("checked_out"):
            current_owner = meta.get("responsible_user", "unknown")
            if current_owner == user:
                print(f"You already have {doc_id} checked out")
            else:
                print(f"Error: {doc_id} is checked out by {current_owner}")
            return 1

        # Read content for workspace
        content = draft_path.read_text(encoding="utf-8")
        frontmatter, body = parse_frontmatter(content)

        # Check out existing draft - update .meta
        version = meta.get("version", "0.1")
        meta = update_meta_checkout(meta, user)
        write_meta(doc_id, doc_type, meta)

        # Log CHECKOUT event
        log_checkout(doc_id, doc_type, user, version)

        # Write content to workspace
        workspace_path = get_workspace_path(user, doc_id)
        workspace_path.parent.mkdir(parents=True, exist_ok=True)
        write_document_minimal(workspace_path, frontmatter, body)

    elif effective_path.exists():
        # Create new draft from effective
        content = effective_path.read_text(encoding="utf-8")
        frontmatter, body = parse_frontmatter(content)

        current_version = meta.get("version", "1.0")
        major = int(str(current_version).split(".")[0])
        new_version = f"{major}.1"

        # Archive effective version before creating draft (per CR-005)
        archive_path = get_archive_path(doc_id, current_version)
        archive_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(effective_path, archive_path)
        print(f"Archived: v{current_version}")

        # Update .meta file for new draft
        meta = update_meta_checkout(meta, user, new_version=new_version)
        meta["status"] = "DRAFT"
        meta["effective_version"] = current_version
        write_meta(doc_id, doc_type, meta)

        # Log CHECKOUT event
        log_checkout(doc_id, doc_type, user, new_version, from_version=current_version)

        # Create draft from effective
        draft_path.parent.mkdir(parents=True, exist_ok=True)
        write_document_minimal(draft_path, frontmatter, body)

        # Write content to workspace
        workspace_path = get_workspace_path(user, doc_id)
        workspace_path.parent.mkdir(parents=True, exist_ok=True)
        write_document_minimal(workspace_path, frontmatter, body)

        print(f"Created draft v{new_version} from effective v{current_version}")
    else:
        print(f"Error: Document not found: {doc_id}")
        return 1

    print(f"Checked out: {doc_id}")
    print(f"Workspace: {workspace_path.relative_to(PROJECT_ROOT)}")

    return 0
