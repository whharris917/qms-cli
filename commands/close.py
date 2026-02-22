"""
QMS Close Command

Closes an executable document.

Created as part of CR-026: QMS CLI Extensibility Refactoring
Updated by CR-095: Attachment auto-close, cascade close
"""
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from registry import CommandRegistry
from qms_config import Status, get_all_document_types
from qms_paths import PROJECT_ROOT, USERS_ROOT, get_doc_type, get_doc_path, get_workspace_path
from qms_io import read_document, write_document_minimal
from qms_auth import get_current_user, check_permission, verify_user_identity
from qms_meta import read_meta, write_meta, get_meta_dir
from qms_audit import log_close, log_status_change


@CommandRegistry.register(
    name="close",
    help="Close an executable document",
    requires_doc_id=True,
    doc_id_help="Document ID to close",
)
def cmd_close(args) -> int:
    """Close an executable document."""
    doc_id = args.doc_id
    user = get_current_user(args)

    if not verify_user_identity(user):
        return 1

    # Permission check (group level)
    allowed, error = check_permission(user, "close")
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

Only executable documents (CR, INV, CAPA, TP, ER, VAR, ADD) can be closed.
Non-executable documents (SOP, RS, DS, etc.) become EFFECTIVE after approval.
""")
        return 1

    # Check ownership
    doc_owner = meta.get("responsible_user")
    allowed, error = check_permission(user, "close", doc_owner=doc_owner)
    if not allowed:
        print(error)
        return 1

    # REQ-DOC-018: Attachments can close from any non-terminal status
    is_attachment = get_all_document_types().get(doc_type, {}).get("attachment", False)
    if is_attachment:
        if current_status in (Status.CLOSED, Status.RETIRED):
            print(f"Error: {doc_id} is already {current_status.value}.")
            return 1
    else:
        if current_status != Status.POST_APPROVED:
            print(f"""
Error: {doc_id} must be POST_APPROVED to close.

Current status: {current_status.value}

Workflow for executable documents:
  ... -> IN_POST_REVIEW -> POST_REVIEWED -> IN_POST_APPROVAL -> POST_APPROVED -> close -> CLOSED
""")
            return 1

    # Move to effective location with minimal frontmatter
    frontmatter, body = read_document(draft_path)
    effective_path = get_doc_path(doc_id, draft=False)
    write_document_minimal(effective_path, frontmatter, body)
    draft_path.unlink()

    # Log CLOSE event to audit trail
    log_close(doc_id, doc_type, user, version)

    # Log status change (CAPA-3: audit trail completeness)
    log_status_change(doc_id, doc_type, user, version, current_status.value, Status.CLOSED.value)

    # Update .meta file (clear ownership on close)
    meta["status"] = Status.CLOSED.value
    meta["responsible_user"] = None
    meta["checked_out"] = False
    meta["checked_out_date"] = None
    meta["pending_assignees"] = []
    write_meta(doc_id, doc_type, meta)

    # Remove from workspace
    workspace_path = get_workspace_path(user, doc_id)
    if workspace_path.exists():
        workspace_path.unlink()

    print(f"Closed: {doc_id}")
    print(f"Location: {effective_path.relative_to(PROJECT_ROOT)}")

    # REQ-DOC-020: Cascade close child attachment documents
    _cascade_close_attachments(doc_id, user)

    return 0


def _compile_interactive_attachment(doc_id: str, doc_type: str, meta: dict) -> str | None:
    """
    Compile an interactive attachment from source data.

    Checks for .interact session first, then .source.json. If neither
    exists, compiles from empty source (VR created but never authored).

    Returns compiled markdown or None on error.
    """
    from interact_source import load_session, load_source, create_source, save_source
    from interact_compiler import compile_document
    from interact_parser import parse_template
    from qms_meta import get_meta_path
    import re

    # Load template
    template_path = Path(__file__).parent.parent / "seed" / "templates" / f"TEMPLATE-{doc_type}.md"
    if not template_path.exists():
        return None
    template_text = template_path.read_text(encoding="utf-8")

    # Try to find source data
    source = None

    # 1. Check for .interact session in responsible user's workspace
    responsible_user = meta.get("responsible_user")
    if responsible_user:
        session_path = get_workspace_path(responsible_user, doc_id).parent / f"{doc_id}.interact"
        if session_path.exists():
            source = load_session(session_path)

    # 2. Fall back to .source.json in .meta/
    if source is None:
        meta_path = get_meta_path(doc_id, doc_type)
        source_path = meta_path.parent / f"{doc_id}.source.json"
        source = load_source(source_path)

    # 3. Neither exists — compile from empty source
    if source is None:
        graph = parse_template(template_text)
        parent_doc_id = ""
        if f"-{doc_type}-" in doc_id:
            parent_doc_id = doc_id.rsplit(f"-{doc_type}-", 1)[0]
        source = create_source(
            doc_id=doc_id,
            template_name=graph.header.name,
            template_version=graph.header.version,
            start_prompt=graph.header.start,
            metadata={
                "parent_doc_id": parent_doc_id,
                "vr_id": doc_id,
                "title": meta.get("title", ""),
            },
        )

    # Save source to .meta/
    meta_path = get_meta_path(doc_id, doc_type)
    source_path = meta_path.parent / f"{doc_id}.source.json"
    save_source(source, source_path)

    return compile_document(source, template_text)


def _cascade_close_attachments(parent_id: str, user: str) -> None:
    """
    Close child attachment documents when parent closes (REQ-DOC-020).

    Discovers attachment-type children by scanning .meta/ for matching IDs.
    For checked-out interactive attachments, auto-compiles before closing.
    """
    all_types = get_all_document_types()

    for type_name, type_config in all_types.items():
        if not type_config.get("attachment"):
            continue

        # Scan .meta/{type}/ for children matching {parent_id}-{prefix}-NNN
        meta_dir = get_meta_dir(type_name)
        if not meta_dir.exists():
            continue

        prefix = type_config.get("prefix", type_name)
        for meta_file in sorted(meta_dir.glob(f"{parent_id}-{prefix}-*.json")):
            child_id = meta_file.stem
            child_meta = read_meta(child_id, type_name)
            if child_meta is None:
                continue

            child_status = child_meta.get("status", "DRAFT")
            if child_status in ("CLOSED", "RETIRED"):
                continue  # Already terminal

            child_version = child_meta.get("version", "0.1")
            child_draft = get_doc_path(child_id, draft=True)
            child_effective = get_doc_path(child_id, draft=False)

            # Auto-compile if checked out and interactive
            if child_meta.get("checked_out"):
                compiled = _compile_interactive_attachment(child_id, type_name, child_meta)
                if compiled is not None:
                    child_draft.parent.mkdir(parents=True, exist_ok=True)
                    child_draft.write_text(compiled, encoding="utf-8")

                # Clean up workspace for the responsible user
                responsible = child_meta.get("responsible_user")
                if responsible:
                    ws_path = get_workspace_path(responsible, child_id)
                    if ws_path.exists():
                        ws_path.unlink()
                    # Clean up .interact session
                    interact_path = ws_path.parent / f"{child_id}.interact"
                    if interact_path.exists():
                        interact_path.unlink()

            # Promote draft to effective
            if child_draft.exists():
                frontmatter, body = read_document(child_draft)
                write_document_minimal(child_effective, frontmatter, body)
                child_draft.unlink()

            # Audit trail
            log_close(child_id, type_name, user, child_version)
            log_status_change(child_id, type_name, user, child_version,
                              child_status, Status.CLOSED.value)

            # Update meta
            child_meta["status"] = Status.CLOSED.value
            child_meta["responsible_user"] = None
            child_meta["checked_out"] = False
            child_meta["checked_out_date"] = None
            child_meta["pending_assignees"] = []
            write_meta(child_id, type_name, child_meta)

            # Clean up workspace across all users
            if USERS_ROOT and USERS_ROOT.exists():
                for user_dir in USERS_ROOT.iterdir():
                    if user_dir.is_dir():
                        ws = user_dir / "workspace" / f"{child_id}.md"
                        if ws.exists():
                            ws.unlink()
                        interact = user_dir / "workspace" / f"{child_id}.interact"
                        if interact.exists():
                            interact.unlink()

            print(f"  Cascade closed: {child_id}")
