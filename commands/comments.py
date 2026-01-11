"""
QMS Comments Command

Shows review/approval comments for a document.

Created as part of CR-026: QMS CLI Extensibility Refactoring
"""
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from registry import CommandRegistry
from qms_paths import get_doc_type, get_doc_path
from qms_io import read_document
from qms_auth import get_current_user, verify_user_identity
from qms_audit import get_comments, get_latest_version_comments, format_comments


@CommandRegistry.register(
    name="comments",
    help="Show review/approval comments for a document",
    requires_doc_id=True,
    doc_id_help="Document ID",
    arguments=[
        {"flags": ["--version", "-v"], "help": "Show comments for specific version"},
    ],
)
def cmd_comments(args) -> int:
    """Show review/approval comments for a document."""
    user = get_current_user(args)

    if not verify_user_identity(user):
        return 1

    doc_id = args.doc_id
    doc_type = get_doc_type(doc_id)

    # Get document status to enforce visibility rules
    draft_path = get_doc_path(doc_id, draft=True)
    effective_path = get_doc_path(doc_id, draft=False)

    if draft_path.exists():
        frontmatter, _ = read_document(draft_path)
    elif effective_path.exists():
        frontmatter, _ = read_document(effective_path)
    else:
        print(f"Document not found: {doc_id}")
        return 1

    status = frontmatter.get("status", "")
    version = frontmatter.get("version", "")

    # Enforce visibility rule: comments only visible after REVIEWED state
    review_states = {"IN_REVIEW", "IN_PRE_REVIEW", "IN_POST_REVIEW"}
    if status in review_states:
        print(f"Comments are not visible while document is in {status}.")
        print("Comments become visible after review phase completes.")
        return 1

    # Get comments
    if args.version:
        comments = get_comments(doc_id, doc_type, version=args.version)
        print(f"Comments for {doc_id} v{args.version}:")
    else:
        comments = get_latest_version_comments(doc_id, doc_type, version)
        print(f"Comments for {doc_id} (current version {version}):")

    print("=" * 70)

    if not comments:
        print("No comments found.")
        # Check if there's frontmatter history (pre-migration)
        if frontmatter.get("review_history") or frontmatter.get("approval_history"):
            print("\nNote: This document has legacy frontmatter comments.")
            print("Run 'qms migrate' to convert them to the new audit system.")
    else:
        print(format_comments(comments))

    return 0
