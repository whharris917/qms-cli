"""
QMS Checkout Command

Checks out a document for editing.

Created as part of CR-026: QMS CLI Extensibility Refactoring
Updated in CR-048: Status-aware transitions, effective version preservation
"""
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from registry import CommandRegistry
from qms_config import Status
from qms_paths import PROJECT_ROOT, USERS_ROOT, get_doc_type, get_doc_path, get_workspace_path
from qms_io import parse_frontmatter, write_document_minimal
from qms_auth import get_current_user, check_permission, verify_user_identity
from qms_meta import read_meta, write_meta, update_meta_checkout
from qms_audit import log_checkout, log_withdraw
from workflow import CHECKOUT_TRANSITIONS, WITHDRAW_TRANSITIONS
from interact_source import create_source, load_source, save_session
from interact_parser import parse_template


def clear_workflow_tracking(meta: dict) -> dict:
    """Clear review/approval tracking fields for fresh workflow cycle."""
    meta = meta.copy()
    meta["pending_assignees"] = []
    meta["completed_reviewers"] = []
    meta["review_outcomes"] = {}
    return meta


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
    current_status = meta.get("status", "DRAFT")

    # REQ-DOC-019: Terminal state checkout guard
    if current_status in ("CLOSED", "RETIRED"):
        print(f"Error: {doc_id} is {current_status} and cannot be checked out.")
        return 1

    if draft_path.exists():
        # REQ-WF-022: Auto-withdraw from active workflow states
        status_enum = Status(current_status)
        if status_enum in WITHDRAW_TRANSITIONS:
            doc_owner = meta.get("responsible_user")
            if doc_owner != user:
                print(f"Error: {doc_id} is in {current_status} and owned by {doc_owner or 'unknown'}")
                print(f"Only the document owner can checkout from an active workflow")
                return 1
            # Perform implicit withdraw
            old_status = current_status
            new_status = WITHDRAW_TRANSITIONS[status_enum]
            log_withdraw(doc_id, doc_type, user, meta.get("version", "0.1"), old_status, new_status.value)
            meta["status"] = new_status.value
            meta["pending_assignees"] = []
            meta["completed_reviewers"] = []
            meta["review_outcomes"] = {}
            write_meta(doc_id, doc_type, meta)
            # Clean up inbox tasks
            for user_dir in USERS_ROOT.iterdir():
                if user_dir.is_dir():
                    inbox = user_dir / "inbox"
                    if inbox.exists():
                        for keyword in ["review", "approval", "pre_review", "pre_approval", "post_review", "post_approval"]:
                            for task_file in inbox.glob(f"task-{doc_id}-{keyword}*.md"):
                                task_file.unlink()
            current_status = new_status.value
            print(f"Auto-withdrawn: {old_status} -> {current_status}")

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

        # CR-087: Central checkout transition lookup (REQ-WF-016, REQ-WF-017)
        checkout_status = Status(current_status)
        if checkout_status in CHECKOUT_TRANSITIONS:
            target_status = CHECKOUT_TRANSITIONS[checkout_status]
            meta = clear_workflow_tracking(meta)
            meta["status"] = target_status.value
            print(f"Transitioned from {current_status} to {target_status.value}")

        # REQ-WF-021: IN_EXECUTION checkout increments minor version
        # Create N.(X+1) in workspace while N.X remains current in QMS
        if current_status == "IN_EXECUTION":
            current_ver = meta.get("version", "1.0")
            major, minor = str(current_ver).split(".")
            new_version = f"{major}.{int(minor) + 1}"
            meta["version"] = new_version
            print(f"Execution checkout: creating v{new_version} (current: v{current_ver})")

        meta = update_meta_checkout(meta, user)
        write_meta(doc_id, doc_type, meta)

        # Log CHECKOUT event
        log_checkout(doc_id, doc_type, user, version)

        # Write content to workspace
        workspace_path = get_workspace_path(user, doc_id)
        workspace_path.parent.mkdir(parents=True, exist_ok=True)

        # CR-091 REQ-INT-017: Interactive checkout
        if _is_interactive_doc(doc_id, doc_type):
            _init_interactive_session(user, doc_id, doc_type, meta)
        else:
            write_document_minimal(workspace_path, frontmatter, body)

    elif effective_path.exists():
        # Create new draft from effective
        content = effective_path.read_text(encoding="utf-8")
        frontmatter, body = parse_frontmatter(content)

        current_version = meta.get("version", "1.0")
        major = int(str(current_version).split(".")[0])
        new_version = f"{major}.1"

        # REQ-WF-020: Effective version preservation
        # Do NOT archive on checkout - archival happens on approval
        # The effective version stays "in force" until superseded
        # (Removed: archive logic that was here)

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

        # CR-091 REQ-INT-017: Interactive checkout
        if _is_interactive_doc(doc_id, doc_type):
            _init_interactive_session(user, doc_id, doc_type, meta)
        else:
            write_document_minimal(workspace_path, frontmatter, body)

        print(f"Created draft v{new_version} from effective v{current_version}")
    else:
        print(f"Error: Document not found: {doc_id}")
        return 1

    print(f"Checked out: {doc_id}")
    print(f"Workspace: {workspace_path.relative_to(PROJECT_ROOT)}")

    return 0


def _is_interactive_doc(doc_id: str, doc_type: str) -> bool:
    """Check if a document should use interactive authoring."""
    # Currently only VR documents are interactive
    return doc_type == "VR"


def _init_interactive_session(user: str, doc_id: str, doc_type: str, meta: dict) -> None:
    """
    Initialize an interactive session for checkout (REQ-INT-017).

    Creates a .interact session file in the workspace. If a .source.json
    exists from a previous checkin, seeds the session from it.
    """
    from qms_meta import get_meta_path
    import re

    # Load template
    template_path = Path(__file__).parent.parent / "seed" / "templates" / f"TEMPLATE-{doc_type}.md"
    if not template_path.exists():
        raise FileNotFoundError(f"Interactive template not found: TEMPLATE-{doc_type}")

    template_text = template_path.read_text(encoding="utf-8")
    graph = parse_template(template_text)

    # Check for existing source file to resume
    meta_dir = get_meta_path(doc_id, doc_type).parent
    source_path = meta_dir / f"{doc_id}.source.json"
    source = load_source(source_path)

    if source is None:
        # Create new source
        # Extract parent_doc_id from doc_id pattern (e.g., CR-091-VR-001 -> CR-091)
        parent_doc_id = ""
        match = re.match(r"((?:CR|INV)-\d+(?:-VAR-\d+)?(?:-ADD-\d+)?)", doc_id)
        if match:
            # Remove the VR suffix to get parent
            parent = doc_id.rsplit("-VR-", 1)[0] if "-VR-" in doc_id else ""
            parent_doc_id = parent

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
        print(f"Interactive session initialized (new)")
    else:
        print(f"Interactive session resumed from source")

    # Save session file
    session_path = get_workspace_path(user, doc_id).parent / f"{doc_id}.interact"
    save_session(source, session_path)

    # Also create a placeholder workspace .md so existing workspace checks work
    workspace_path = get_workspace_path(user, doc_id)
    workspace_path.parent.mkdir(parents=True, exist_ok=True)
    workspace_path.write_text(
        f"# {doc_id}\n\nThis document is authored interactively.\n"
        f"Use `qms interact {doc_id}` to author.\n"
        f"Use `qms interact {doc_id} --compile` to preview.\n",
        encoding="utf-8",
    )
