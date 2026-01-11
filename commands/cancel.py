"""
QMS Cancel Command

Cancels a never-effective document (version < 1.0).

Created as part of CR-026: QMS CLI Extensibility Refactoring
"""
import os
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from registry import CommandRegistry
from qms_config import USER_GROUPS
from qms_paths import PROJECT_ROOT, QMS_ROOT, get_doc_type, get_doc_path
from qms_auth import get_current_user
from qms_meta import read_meta, get_meta_path


@CommandRegistry.register(
    name="cancel",
    help="Cancel a never-effective document (version < 1.0)",
    requires_doc_id=True,
    doc_id_help="Document ID to cancel",
    arguments=[
        {"flags": ["--confirm"], "help": "Confirm deletion", "action": "store_true"},
    ],
)
def cmd_cancel(args) -> int:
    """Cancel a never-effective document (version < 1.0)."""
    user = get_current_user(args)

    # Only initiators can cancel
    if user not in USER_GROUPS["initiators"]:
        print("Error: Only initiators can cancel documents.", file=sys.stderr)
        return 1

    doc_id = args.doc_id
    doc_type = get_doc_type(doc_id)

    # Get document metadata
    meta = read_meta(doc_id, doc_type)
    if meta is None:
        print(f"Error: Document {doc_id} not found.", file=sys.stderr)
        return 1

    # Check version < 1.0 (never effective)
    version = meta.get("version", "0.1")
    major = int(version.split(".")[0])
    if major >= 1:
        print(f"Error: Cannot cancel {doc_id} - it was effective (v{version}).", file=sys.stderr)
        print("Use the retire workflow instead (checkout, edit, route --approval --retire).")
        return 1

    # Check not checked out by someone else
    if meta.get("checked_out"):
        responsible = meta.get("responsible_user", "unknown")
        print(f"Error: {doc_id} is checked out by {responsible}.", file=sys.stderr)
        print("Document must be checked in before canceling.")
        return 1

    # Require --confirm
    if not args.confirm:
        print(f"This will permanently delete {doc_id} (v{version}) and free the doc ID.")
        print("The following will be deleted:")
        print(f"  - Document file(s)")
        print(f"  - Metadata (.meta/{doc_type}/{doc_id}.json)")
        print(f"  - Audit trail (.audit/{doc_type}/{doc_id}.jsonl)")
        print()
        print("Run with --confirm to proceed.")
        return 1

    # Delete document file(s)
    draft_path = get_doc_path(doc_id, draft=True)
    effective_path = get_doc_path(doc_id, draft=False)

    deleted_files = []
    if draft_path.exists():
        draft_path.unlink()
        deleted_files.append(str(draft_path.relative_to(PROJECT_ROOT)))

    if effective_path.exists():
        effective_path.unlink()
        deleted_files.append(str(effective_path.relative_to(PROJECT_ROOT)))

    # For CR documents, also try to remove the directory if empty
    if doc_type == "CR":
        cr_dir = QMS_ROOT / "CR" / doc_id
        if cr_dir.exists() and not any(cr_dir.iterdir()):
            cr_dir.rmdir()
            deleted_files.append(str(cr_dir.relative_to(PROJECT_ROOT)))

    # Delete .meta file
    meta_path = get_meta_path(doc_id, doc_type)
    if meta_path.exists():
        meta_path.unlink()
        deleted_files.append(str(meta_path.relative_to(PROJECT_ROOT)))

    # Delete .audit file
    audit_dir = QMS_ROOT / ".audit" / doc_type
    audit_path = audit_dir / f"{doc_id}.jsonl"
    if audit_path.exists():
        audit_path.unlink()
        deleted_files.append(str(audit_path.relative_to(PROJECT_ROOT)))

    # Also clean up any workspace copies
    for username in ["lead", "claude", "qa"]:
        workspace_path = Path(f".claude/users/{username}/workspace/{doc_id}.md")
        full_workspace_path = PROJECT_ROOT / workspace_path
        if full_workspace_path.exists():
            full_workspace_path.unlink()
            deleted_files.append(str(workspace_path))

    # Clean up inbox tasks
    for username in os.listdir(PROJECT_ROOT / ".claude" / "users"):
        inbox_dir = PROJECT_ROOT / ".claude" / "users" / username / "inbox"
        if inbox_dir.exists():
            for task_file in inbox_dir.glob(f"task-{doc_id}-*.md"):
                task_file.unlink()
                deleted_files.append(str(task_file.relative_to(PROJECT_ROOT)))

    print(f"Canceled: {doc_id}")
    print("Deleted:")
    for f in deleted_files:
        print(f"  - {f}")

    return 0
