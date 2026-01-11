"""
QMS History Command

Shows full audit history for a document.

Created as part of CR-026: QMS CLI Extensibility Refactoring
"""
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from registry import CommandRegistry
from qms_paths import get_doc_type, get_doc_path
from qms_auth import get_current_user, verify_user_identity
from qms_audit import read_audit_log, format_audit_history


@CommandRegistry.register(
    name="history",
    help="Show full audit history for a document",
    requires_doc_id=True,
    doc_id_help="Document ID",
)
def cmd_history(args) -> int:
    """Show full audit history for a document."""
    user = get_current_user(args)

    if not verify_user_identity(user):
        return 1

    doc_id = args.doc_id
    doc_type = get_doc_type(doc_id)

    # Read audit log
    events = read_audit_log(doc_id, doc_type)

    if not events:
        # Check if document exists but has no audit log (pre-migration)
        draft_path = get_doc_path(doc_id, draft=True)
        effective_path = get_doc_path(doc_id, draft=False)
        if draft_path.exists() or effective_path.exists():
            print(f"Document {doc_id} exists but has no audit log.")
            print("Run 'qms migrate' to generate audit logs from frontmatter history.")
        else:
            print(f"Document not found: {doc_id}")
        return 1

    print(f"Audit History: {doc_id}")
    print("=" * 70)
    print(format_audit_history(events))

    return 0
