"""
QMS Checkin Command

Checks in a document from workspace.

Created as part of CR-026: QMS CLI Extensibility Refactoring
Updated in CR-048: Archive on commit for execution versioning
"""
import shutil
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from registry import CommandRegistry
from qms_paths import get_doc_type, get_doc_path, get_workspace_path, get_archive_path
from qms_io import read_document, write_document_minimal
from qms_auth import get_current_user, check_permission, verify_user_identity
from qms_meta import read_meta, write_meta, update_meta_checkin, get_meta_path
from qms_audit import log_checkin
from interact_source import load_session, save_source
from interact_compiler import compile_document


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

    # CR-091 REQ-INT-018: Check for interactive session
    session_path = workspace_path.parent / f"{doc_id}.interact"
    if session_path.exists():
        return _checkin_interactive(doc_id, user, doc_type, meta, session_path, workspace_path, draft_path)

    # Read workspace version
    frontmatter, body = read_document(workspace_path)

    # Get version from .meta (authoritative source)
    # Note: For IN_EXECUTION checkouts, version was already incremented on checkout
    version = meta.get("version", frontmatter.get("version", "0.1"))
    current_status = meta.get("status", "DRAFT")

    # REQ-WF-021: Archive on commit for IN_EXECUTION documents
    # Archive the previous version before writing the new one
    if current_status == "IN_EXECUTION" and draft_path.exists():
        # Calculate the previous version that's currently in draft_path
        # The meta version is already the NEW version (incremented on checkout)
        # So we need to determine what's being archived
        major, minor = str(version).split(".")
        if int(minor) > 0:
            # Previous version exists - archive it
            prev_version = f"{major}.{int(minor) - 1}"
            archive_path = get_archive_path(doc_id, prev_version)
            archive_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy(draft_path, archive_path)
            print(f"Archived: v{prev_version}")

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


def _checkin_interactive(doc_id, user, doc_type, meta, session_path, workspace_path, draft_path):
    """
    Check in an interactive document (REQ-INT-018).

    1. Compile source to markdown
    2. Store compiled markdown in QMS directory
    3. Store .source.json in .meta/
    4. Remove .interact session and workspace placeholder
    5. Standard checkin metadata update
    """
    # Load session
    source = load_session(session_path)
    if source is None:
        print(f"Error: Could not read interactive session for {doc_id}")
        return 1

    # Load template for compilation
    template_path = Path(__file__).parent.parent / "seed" / "templates" / f"TEMPLATE-{doc_type}.md"
    if not template_path.exists():
        print(f"Error: Template not found: TEMPLATE-{doc_type}")
        return 1
    template_text = template_path.read_text(encoding="utf-8")

    # Compile to markdown
    compiled = compile_document(source, template_text)

    # Archive previous version if IN_EXECUTION
    current_status = meta.get("status", "DRAFT")
    version = meta.get("version", "0.1")

    if current_status == "IN_EXECUTION" and draft_path.exists():
        major, minor = str(version).split(".")
        if int(minor) > 0:
            prev_version = f"{major}.{int(minor) - 1}"
            archive_path = get_archive_path(doc_id, prev_version)
            archive_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy(draft_path, archive_path)
            print(f"Archived: v{prev_version}")

    # Write compiled markdown to QMS draft path
    draft_path.parent.mkdir(parents=True, exist_ok=True)
    draft_path.write_text(compiled, encoding="utf-8")

    # Store source in .meta/
    meta_path = get_meta_path(doc_id, doc_type)
    source_path = meta_path.parent / f"{doc_id}.source.json"
    save_source(source, source_path)
    print(f"Source saved: {source_path.name}")

    # Update metadata
    meta = update_meta_checkin(meta)
    write_meta(doc_id, doc_type, meta)

    # Log CHECKIN event
    log_checkin(doc_id, doc_type, user, version)

    # Clean up workspace
    session_path.unlink()
    if workspace_path.exists():
        workspace_path.unlink()

    print(f"Checked in: {doc_id} (v{version}, interactive)")

    return 0
