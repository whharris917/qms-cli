"""
QMS Read Command

Displays document content.

Created as part of CR-026: QMS CLI Extensibility Refactoring
"""
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from registry import CommandRegistry
from qms_paths import get_doc_path, get_archive_path


@CommandRegistry.register(
    name="read",
    help="Read a document",
    requires_doc_id=True,
    doc_id_help="Document ID",
    arguments=[
        {"flags": ["--version", "-v"], "help": "Specific version to read"},
        {"flags": ["--draft"], "help": "Read draft version", "action": "store_true"},
    ],
)
def cmd_read(args) -> int:
    """Read a document."""
    doc_id = args.doc_id

    try:
        if args.version:
            # Read specific archived version
            path = get_archive_path(doc_id, args.version)
        elif args.draft:
            path = get_doc_path(doc_id, draft=True)
        else:
            # Read effective version, fall back to draft
            path = get_doc_path(doc_id, draft=False)
            if not path.exists():
                path = get_doc_path(doc_id, draft=True)

        if not path.exists():
            print(f"Error: Document not found: {doc_id}")
            return 1

        content = path.read_text(encoding="utf-8")
        print(content)
        return 0

    except Exception as e:
        print(f"Error: {e}")
        return 1
