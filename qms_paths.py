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
    if doc_id.startswith("SDLC-QMS-"):
        suffix = doc_id.replace("SDLC-QMS-", "")
        if suffix in ["RS", "RTM"]:
            return f"QMS-{suffix}"
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
    if "-VAR-" in doc_id:
        return "VAR"
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

    # Handle nested document types that live in parent's folder
    if doc_type == "VAR":
        # CR-032 Gap 4: Derive path from parent type, not VAR config
        # CR-028-VAR-001 -> CR-028 (in CR/), INV-001-VAR-001 -> INV-001 (in INV/)
        match = re.match(r"((?:CR|INV)-\d+)", doc_id)
        if match:
            parent_id = match.group(1)
            parent_type = "CR" if parent_id.startswith("CR-") else "INV"
            parent_config = DOCUMENT_TYPES[parent_type]
            base_path = QMS_ROOT / parent_config["path"] / parent_id
    elif doc_type in ["TP", "ER"]:
        # CR-032 Gap 3: TP/ER live in parent CR folder
        # CR-001-TP -> CR-001, CR-001-TP-ER-001 -> CR-001
        match = re.match(r"(CR-\d+)", doc_id)
        if match:
            base_path = base_path / match.group(1)
    elif doc_type == "CAPA":
        # CAPA lives in parent INV folder
        # INV-001-CAPA-001 -> INV-001
        match = re.match(r"(INV-\d+)", doc_id)
        if match:
            base_path = base_path / match.group(1)
    # Handle folder-per-doc types (CR, INV)
    elif config.get("folder_per_doc"):
        base_path = base_path / doc_id

    filename = f"{doc_id}-draft.md" if draft else f"{doc_id}.md"
    return base_path / filename


def get_archive_path(doc_id: str, version: str) -> Path:
    """Get the archive path for a specific version."""
    doc_type = get_doc_type(doc_id)
    config = DOCUMENT_TYPES[doc_type]

    base_path = ARCHIVE_ROOT / config["path"]

    # CR-032 Gap 4: VAR path derived from parent type
    if doc_type == "VAR":
        match = re.match(r"((?:CR|INV)-\d+)", doc_id)
        if match:
            parent_id = match.group(1)
            parent_type = "CR" if parent_id.startswith("CR-") else "INV"
            parent_config = DOCUMENT_TYPES[parent_type]
            base_path = ARCHIVE_ROOT / parent_config["path"] / parent_id
    elif doc_type in ["TP", "ER"]:
        # CR-032 Gap 3: TP/ER live in parent CR folder
        match = re.match(r"(CR-\d+)", doc_id)
        if match:
            base_path = base_path / match.group(1)
    elif doc_type == "CAPA":
        match = re.match(r"(INV-\d+)", doc_id)
        if match:
            base_path = base_path / match.group(1)
    elif config.get("folder_per_doc"):
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


def get_next_nested_number(parent_id: str, child_type: str) -> int:
    """Get the next available number for a nested document type (e.g., CR-028-VAR-001)."""
    parent_type = get_doc_type(parent_id)
    parent_config = DOCUMENT_TYPES[parent_type]

    # Nested documents live in parent's folder
    if parent_config.get("folder_per_doc"):
        base_path = QMS_ROOT / parent_config["path"] / parent_id
    else:
        base_path = QMS_ROOT / parent_config["path"]

    if not base_path.exists():
        return 1

    # Pattern: {parent_id}-{child_type}-NNN
    pattern = re.compile(rf"^{re.escape(parent_id)}-{child_type}-(\d+)")
    max_num = 0

    for item in base_path.iterdir():
        name = item.stem if item.is_file() else item.name
        name = name.replace("-draft", "")
        match = pattern.match(name)
        if match:
            max_num = max(max_num, int(match.group(1)))

    return max_num + 1
