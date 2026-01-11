"""
QMS Create Command

Creates a new document of specified type.

Created as part of CR-026: QMS CLI Extensibility Refactoring
"""
import shutil
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from registry import CommandRegistry
from qms_config import DOCUMENT_TYPES
from qms_paths import PROJECT_ROOT, QMS_ROOT, get_doc_path, get_workspace_path, get_next_number
from qms_io import write_document_minimal
from qms_auth import get_current_user, check_permission, verify_user_identity
from qms_templates import load_template_for_type
from qms_meta import create_initial_meta, write_meta
from qms_audit import log_create


@CommandRegistry.register(
    name="create",
    help="Create a new document",
    arguments=[
        {"flags": ["type"], "help": "Document type (SOP, CR, INV, etc.)"},
        {"flags": ["--title"], "help": "Document title"},
    ],
)
def cmd_create(args) -> int:
    """Create a new document."""
    user = get_current_user(args)

    if not verify_user_identity(user):
        return 1

    # Permission check
    allowed, error = check_permission(user, "create")
    if not allowed:
        print(error)
        return 1

    doc_type = args.type.upper()

    if doc_type not in DOCUMENT_TYPES:
        print(f"Error: Unknown document type '{doc_type}'")
        print(f"Valid types: {', '.join(DOCUMENT_TYPES.keys())}")
        return 1

    config = DOCUMENT_TYPES[doc_type]

    # Generate doc_id
    if config.get("singleton"):
        doc_id = config["prefix"]
    else:
        next_num = get_next_number(doc_type)
        doc_id = f"{config['prefix']}-{next_num:03d}"

    # Check if already exists
    effective_path = get_doc_path(doc_id, draft=False)
    draft_path = get_doc_path(doc_id, draft=True)

    if effective_path.exists() or draft_path.exists():
        print(f"Error: {doc_id} already exists")
        return 1

    # Create directory structure if needed
    if config.get("folder_per_doc"):
        folder_path = QMS_ROOT / config["path"] / doc_id
        folder_path.mkdir(parents=True, exist_ok=True)

    # Load template for document type (CR-019)
    # Falls back to minimal template if TEMPLATE-{type} doesn't exist
    title = args.title or f"{doc_type} - [Title]"
    frontmatter, body = load_template_for_type(doc_type, doc_id, title)

    # Write to draft path (minimal frontmatter only)
    write_document_minimal(draft_path, frontmatter, body)

    # DUAL-WRITE: Create .meta file
    meta = create_initial_meta(
        doc_id=doc_id,
        doc_type=doc_type,
        version="0.1",
        status="DRAFT",
        executable=config["executable"],
        responsible_user=user
    )
    write_meta(doc_id, doc_type, meta)

    # DUAL-WRITE: Log CREATE event to audit trail
    title = args.title or f"{doc_type} - [Title]"
    log_create(doc_id, doc_type, user, "0.1", title)

    # Copy to user's workspace
    workspace_path = get_workspace_path(user, doc_id)
    workspace_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy(draft_path, workspace_path)

    print(f"Created: {doc_id} (v0.1, DRAFT)")
    print(f"Location: {draft_path.relative_to(PROJECT_ROOT)}")
    print(f"Workspace: {workspace_path.relative_to(PROJECT_ROOT)}")
    print(f"Responsible User: {user}")

    return 0
