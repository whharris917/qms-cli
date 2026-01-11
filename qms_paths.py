"""
QMS CLI Path Resolution Module

Contains functions for resolving document paths, workspace paths,
and other filesystem locations within the QMS structure.
"""
import re
from pathlib import Path

from qms_config import DOCUMENT_TYPES


# =============================================================================
# Project Root Discovery
# =============================================================================

def find_project_root() -> Path:
    """Find the project root by looking for QMS/ directory."""
    current = Path.cwd()
    while current != current.parent:
        if (current / "QMS").is_dir():
            return current
        current = current.parent
    # Fallback: assume we're in project root or .claude/
    if Path("QMS").is_dir():
        return Path.cwd()
    elif Path("../QMS").is_dir():
        return Path.cwd().parent
    raise FileNotFoundError("Cannot find QMS/ directory. Are you in the project?")


# Computed at module load time
PROJECT_ROOT = find_project_root()
QMS_ROOT = PROJECT_ROOT / "QMS"
ARCHIVE_ROOT = QMS_ROOT / ".archive"
USERS_ROOT = PROJECT_ROOT / ".claude" / "users"


# =============================================================================
# Document Type Resolution
# =============================================================================

def get_doc_type(doc_id: str) -> str:
    """Determine document type from doc_id."""
    if doc_id.startswith("SDLC-FLOW-"):
        suffix = doc_id.replace("SDLC-FLOW-", "")
        if suffix in ["RS", "DS", "CS", "RTM", "OQ"]:
            return suffix
    if doc_id.startswith("SOP-"):
        return "SOP"
    if doc_id.startswith("TEMPLATE-"):
        return "TEMPLATE"
    if "-TP-ER-" in doc_id:
        return "ER"
    if "-TP" in doc_id:
        return "TP"
    if "-CAPA-" in doc_id:
        return "CAPA"
    if doc_id.startswith("CR-"):
        return "CR"
    if doc_id.startswith("INV-"):
        return "INV"
    raise ValueError(f"Unknown document type for: {doc_id}")


# =============================================================================
# Path Resolution Functions
# =============================================================================

def get_doc_path(doc_id: str, draft: bool = False) -> Path:
    """Get the path to a document."""
    doc_type = get_doc_type(doc_id)
    config = DOCUMENT_TYPES[doc_type]

    base_path = QMS_ROOT / config["path"]

    # Handle folder-per-doc types (CR, INV)
    if config.get("folder_per_doc"):
        # Extract the parent folder (e.g., CR-001 from CR-001-TP)
        if doc_type in ["TP", "ER"]:
            # CR-001-TP -> CR-001, CR-001-TP-ER-001 -> CR-001
            match = re.match(r"(CR-\d+)", doc_id)
            if match:
                base_path = base_path / match.group(1)
        elif doc_type == "CAPA":
            # INV-001-CAPA-001 -> INV-001
            match = re.match(r"(INV-\d+)", doc_id)
            if match:
                base_path = base_path / match.group(1)
        else:
            base_path = base_path / doc_id

    filename = f"{doc_id}-draft.md" if draft else f"{doc_id}.md"
    return base_path / filename


def get_archive_path(doc_id: str, version: str) -> Path:
    """Get the archive path for a specific version."""
    doc_type = get_doc_type(doc_id)
    config = DOCUMENT_TYPES[doc_type]

    base_path = ARCHIVE_ROOT / config["path"]

    if config.get("folder_per_doc"):
        if doc_type in ["TP", "ER"]:
            match = re.match(r"(CR-\d+)", doc_id)
            if match:
                base_path = base_path / match.group(1)
        elif doc_type == "CAPA":
            match = re.match(r"(INV-\d+)", doc_id)
            if match:
                base_path = base_path / match.group(1)
        else:
            base_path = base_path / doc_id

    return base_path / f"{doc_id}-v{version}.md"


def get_workspace_path(user: str, doc_id: str) -> Path:
    """Get the workspace path for a user's checked-out document."""
    return USERS_ROOT / user / "workspace" / f"{doc_id}.md"


def get_inbox_path(user: str) -> Path:
    """Get the inbox directory for a user."""
    return USERS_ROOT / user / "inbox"


def get_next_number(doc_type: str) -> int:
    """Get the next available number for a document type."""
    config = DOCUMENT_TYPES[doc_type]
    base_path = QMS_ROOT / config["path"]

    if not base_path.exists():
        return 1

    pattern = re.compile(rf"^{config['prefix']}-(\d+)")
    max_num = 0

    # Check both files and directories
    for item in base_path.iterdir():
        name = item.stem if item.is_file() else item.name
        # Remove -draft suffix if present
        name = name.replace("-draft", "")
        match = pattern.match(name)
        if match:
            max_num = max(max_num, int(match.group(1)))

    return max_num + 1
