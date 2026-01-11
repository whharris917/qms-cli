"""
QMS Status Command

Shows document status information.

Created as part of CR-026: QMS CLI Extensibility Refactoring
"""
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from registry import CommandRegistry
from qms_paths import get_doc_type, get_doc_path
from qms_io import read_document
from qms_meta import read_meta


@CommandRegistry.register(
    name="status",
    help="Show document status",
    requires_doc_id=True,
    doc_id_help="Document ID",
)
def cmd_status(args) -> int:
    """Show document status."""
    doc_id = args.doc_id

    # Try draft first, then effective
    draft_path = get_doc_path(doc_id, draft=True)
    effective_path = get_doc_path(doc_id, draft=False)

    if draft_path.exists():
        path = draft_path
        location = "draft"
    elif effective_path.exists():
        path = effective_path
        location = "effective"
    else:
        print(f"Error: Document not found: {doc_id}")
        return 1

    # Read title from document frontmatter
    frontmatter, _ = read_document(path)

    # Get workflow state from .meta (authoritative source)
    doc_type = get_doc_type(doc_id)
    meta = read_meta(doc_id, doc_type) or {}

    print(f"Document: {doc_id}")
    print(f"Title: {frontmatter.get('title', 'N/A')}")
    print(f"Version: {meta.get('version', 'N/A')}")
    print(f"Status: {meta.get('status', 'N/A')}")
    print(f"Location: {location}")
    print(f"Type: {doc_type}")
    print(f"Executable: {meta.get('executable', False)}")
    print(f"Responsible User: {meta.get('responsible_user') or 'N/A'}")
    print(f"Checked Out: {meta.get('checked_out', False)}")

    if meta.get("effective_version"):
        print(f"Effective Version: {meta.get('effective_version')}")

    # Show pending assignees from .meta
    pending_assignees = meta.get("pending_assignees", [])
    if pending_assignees:
        status = meta.get("status", "")
        if "REVIEW" in status:
            print(f"\nPending Reviewers: {', '.join(pending_assignees)}")
        elif "APPROVAL" in status:
            print(f"\nPending Approvers: {', '.join(pending_assignees)}")

    return 0
