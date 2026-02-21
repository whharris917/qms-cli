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
from qms_paths import get_doc_path, get_archive_path, get_doc_type, get_workspace_path, USERS_ROOT
from qms_meta import read_meta, get_meta_path
from interact_source import load_session, load_source
from interact_compiler import compile_document


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
            if not path.exists():
                print(f"Error: Document not found: {doc_id}")
                return 1
            content = path.read_text(encoding="utf-8")
            print(content)
            return 0

        # CR-091 REQ-INT-019: Source-aware read
        # Try to compile from interactive source if available
        compiled = _try_compile_from_source(doc_id, args.draft)
        if compiled is not None:
            print(compiled)
            return 0

        if args.draft:
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


def _try_compile_from_source(doc_id: str, draft: bool) -> str | None:
    """
    Try to compile from interactive source (REQ-INT-019).

    - If checked out: compile from .interact session file
    - If checked in: compile from .source.json
    - If no source: return None (fall back to standard)
    """
    try:
        doc_type = get_doc_type(doc_id)
    except ValueError:
        return None

    # Only VR is interactive currently
    if doc_type != "VR":
        return None

    meta = read_meta(doc_id, doc_type)
    if meta is None:
        return None

    template_path = Path(__file__).parent.parent / "seed" / "templates" / f"TEMPLATE-{doc_type}.md"
    if not template_path.exists():
        return None
    template_text = template_path.read_text(encoding="utf-8")

    # Check for active session (.interact in workspace)
    if meta.get("checked_out"):
        responsible_user = meta.get("responsible_user", "")
        if responsible_user and USERS_ROOT:
            session_path = USERS_ROOT / responsible_user / "workspace" / f"{doc_id}.interact"
            source = load_session(session_path)
            if source is not None:
                return compile_document(source, template_text)

    # Check for permanent source (.source.json in .meta/)
    meta_path = get_meta_path(doc_id, doc_type)
    source_path = meta_path.parent / f"{doc_id}.source.json"
    source = load_source(source_path)
    if source is not None:
        return compile_document(source, template_text)

    # No interactive source available
    return None
