"""
QMS CLI Configuration Module

Contains constants, enums, and configuration data for the QMS CLI.
"""
import json
from enum import Enum
from pathlib import Path


# =============================================================================
# Config File Discovery
# =============================================================================

CONFIG_FILE = "qms.config.json"


def find_config_file(start_path: Path = None) -> Path | None:
    """
    Find qms.config.json by walking up from start_path.

    Args:
        start_path: Starting directory (defaults to cwd)

    Returns:
        Path to qms.config.json if found, None otherwise
    """
    current = start_path or Path.cwd()
    current = current.resolve()

    while current != current.parent:
        config_path = current / CONFIG_FILE
        if config_path.is_file():
            return config_path
        current = current.parent

    # Check root
    config_path = current / CONFIG_FILE
    if config_path.is_file():
        return config_path

    return None


def load_config(config_path: Path) -> dict:
    """
    Load and parse a qms.config.json file.

    Args:
        config_path: Path to the config file

    Returns:
        Parsed config dictionary
    """
    with open(config_path, "r", encoding="utf-8") as f:
        return json.load(f)


def get_project_root_from_config(start_path: Path = None) -> Path | None:
    """
    Get project root by finding qms.config.json.

    Args:
        start_path: Starting directory (defaults to cwd)

    Returns:
        Project root path if config found, None otherwise
    """
    config_path = find_config_file(start_path)
    if config_path:
        return config_path.parent
    return None


# =============================================================================
# Status Enum
# =============================================================================

class Status(Enum):
    """Document workflow status values."""
    # Common
    DRAFT = "DRAFT"

    # Non-executable workflow
    IN_REVIEW = "IN_REVIEW"
    REVIEWED = "REVIEWED"
    IN_APPROVAL = "IN_APPROVAL"
    APPROVED = "APPROVED"
    EFFECTIVE = "EFFECTIVE"

    # Executable workflow
    IN_PRE_REVIEW = "IN_PRE_REVIEW"
    PRE_REVIEWED = "PRE_REVIEWED"
    IN_PRE_APPROVAL = "IN_PRE_APPROVAL"
    PRE_APPROVED = "PRE_APPROVED"
    IN_EXECUTION = "IN_EXECUTION"
    IN_POST_REVIEW = "IN_POST_REVIEW"
    POST_REVIEWED = "POST_REVIEWED"
    IN_POST_APPROVAL = "IN_POST_APPROVAL"
    POST_APPROVED = "POST_APPROVED"
    CLOSED = "CLOSED"

    # Terminal states
    RETIRED = "RETIRED"


# =============================================================================
# State Transitions
# =============================================================================

# Valid status transitions
TRANSITIONS = {
    # Non-executable
    # BUGFIX: Allow DRAFT -> IN_POST_REVIEW for post-release checkout/checkin cycle
    # The route command checks execution_phase before allowing this transition
    Status.DRAFT: [Status.IN_REVIEW, Status.IN_PRE_REVIEW, Status.IN_POST_REVIEW],
    Status.IN_REVIEW: [Status.REVIEWED],
    Status.REVIEWED: [Status.IN_REVIEW, Status.IN_APPROVAL],
    Status.IN_APPROVAL: [Status.APPROVED, Status.REVIEWED],  # REVIEWED on rejection
    Status.APPROVED: [Status.EFFECTIVE],
    Status.EFFECTIVE: [],

    # Executable
    Status.IN_PRE_REVIEW: [Status.PRE_REVIEWED],
    Status.PRE_REVIEWED: [Status.IN_PRE_REVIEW, Status.IN_PRE_APPROVAL],
    Status.IN_PRE_APPROVAL: [Status.PRE_APPROVED, Status.PRE_REVIEWED],  # PRE_REVIEWED on rejection
    Status.PRE_APPROVED: [Status.IN_EXECUTION],
    Status.IN_EXECUTION: [Status.IN_POST_REVIEW],
    Status.IN_POST_REVIEW: [Status.POST_REVIEWED],
    Status.POST_REVIEWED: [Status.IN_POST_REVIEW, Status.IN_POST_APPROVAL, Status.IN_EXECUTION],
    Status.IN_POST_APPROVAL: [Status.POST_APPROVED, Status.POST_REVIEWED],  # POST_REVIEWED on rejection
    Status.POST_APPROVED: [Status.CLOSED],
    Status.CLOSED: [],
    Status.RETIRED: [],
}


# =============================================================================
# Document Types
# =============================================================================

# Base document types (non-namespace specific)
DOCUMENT_TYPES = {
    "SOP": {"path": "SOP", "executable": False, "prefix": "SOP"},
    "CR": {"path": "CR", "executable": True, "prefix": "CR", "folder_per_doc": True},
    "INV": {"path": "INV", "executable": True, "prefix": "INV", "folder_per_doc": True},
    "TP": {"path": "CR", "executable": True, "prefix": "TP", "parent_type": "CR"},
    "ER": {"path": "CR", "executable": True, "prefix": "ER", "parent_type": "TP"},
    "VAR": {"path": "CR", "executable": True, "prefix": "VAR"},
    # Named document types (name-based rather than numbered)
    "TEMPLATE": {"path": "TEMPLATE", "executable": False, "prefix": "TEMPLATE"},
}


# =============================================================================
# SDLC Namespace Registry
# =============================================================================

# Registered SDLC namespaces - each gets RS and RTM document types
# Format: {namespace_name: {"path": folder_path}}
SDLC_NAMESPACES = {
    "FLOW": {"path": "SDLC-FLOW"},
    "QMS": {"path": "SDLC-QMS"},
}


def get_all_sdlc_namespaces() -> dict:
    """
    Get all SDLC namespaces (built-in + persisted).

    Merges the built-in SDLC_NAMESPACES with any custom namespaces
    stored in QMS/.meta/sdlc_namespaces.json.
    """
    import json
    from pathlib import Path

    namespaces = dict(SDLC_NAMESPACES)

    # Try to load persisted namespaces
    try:
        # Find QMS root (go up from this file's location)
        config_dir = Path(__file__).parent.parent / "QMS" / ".meta"
        config_path = config_dir / "sdlc_namespaces.json"
        if config_path.exists():
            with open(config_path, "r", encoding="utf-8") as f:
                persisted = json.load(f)
                namespaces.update(persisted)
    except (json.JSONDecodeError, IOError, FileNotFoundError):
        pass  # Use defaults if config is unavailable

    return namespaces


def get_all_document_types() -> dict:
    """
    Get all document types including dynamically generated SDLC namespace types.

    Returns the base DOCUMENT_TYPES plus RS/RTM types for each registered namespace.
    Example: FLOW namespace generates FLOW-RS and FLOW-RTM types.
    """
    all_types = dict(DOCUMENT_TYPES)

    for namespace, config in get_all_sdlc_namespaces().items():
        path = config["path"]
        # Generate RS type for this namespace
        all_types[f"{namespace}-RS"] = {
            "path": path,
            "executable": False,
            "prefix": f"SDLC-{namespace}-RS",
            "singleton": True,
        }
        # Generate RTM type for this namespace
        all_types[f"{namespace}-RTM"] = {
            "path": path,
            "executable": False,
            "prefix": f"SDLC-{namespace}-RTM",
            "singleton": True,
        }

    return all_types


# =============================================================================
# Users and Permissions
# =============================================================================

# Valid QMS users
VALID_USERS = {"lead", "claude", "qa", "bu", "tu_ui", "tu_scene", "tu_sketch", "tu_sim"}

# User group definitions (hierarchy: administrator > initiator > quality > reviewer)
USER_GROUPS = {
    "administrator": {"lead", "claude"},    # Full system access (inherits initiator + fix)
    "initiator": set(),                     # Placeholder for future non-admin initiators
    "quality": {"qa"},                      # Can modify workflows, review, approve
    "reviewer": {"tu_ui", "tu_scene", "tu_sketch", "tu_sim", "bu"},  # Review/approve only
}

# Group hierarchy for permission inheritance
GROUP_HIERARCHY = ["administrator", "initiator", "quality", "reviewer"]

# Permission definitions by command
# "all" = any valid user, "assigned" = must be assigned to workflow
# Note: administrator inherits all permissions via hierarchy check
PERMISSIONS = {
    "create":    {"groups": ["initiator"]},
    "checkout":  {"groups": ["initiator"]},
    "checkin":   {"groups": ["initiator"], "owner_only": True},
    "route":     {"groups": ["initiator"], "owner_only": True},  # CR-034: quality removed
    "assign":    {"groups": ["quality"]},
    "review":    {"groups": ["initiator", "quality", "reviewer"], "assigned_only": True},
    "approve":   {"groups": ["quality", "reviewer"], "assigned_only": True},
    "reject":    {"groups": ["quality", "reviewer"], "assigned_only": True},
    "release":   {"groups": ["initiator"], "owner_only": True},
    "revert":    {"groups": ["initiator"], "owner_only": True},
    "close":     {"groups": ["initiator"], "owner_only": True},
    "read":      {"groups": ["initiator", "quality", "reviewer"]},
    "status":    {"groups": ["initiator", "quality", "reviewer"]},
    "inbox":     {"groups": ["initiator", "quality", "reviewer"]},
    "workspace": {"groups": ["initiator", "quality", "reviewer"]},
}

# Helpful guidance messages for each group
GROUP_GUIDANCE = {
    "administrator": """
As an Administrator (lead), you have full system access:
  - All initiator capabilities (create, checkout, checkin, route, release, close)
  - All quality capabilities (assign, review, approve, reject)
  - System configuration and maintenance
""",
    "initiator": """
As an Initiator (claude), you can:
  - Create new documents: qms --user {you} create SOP --title "Title"
  - Check out documents for editing: qms --user {you} checkout DOC-ID
  - Check in edited documents: qms --user {you} checkin DOC-ID
  - Route documents for review/approval: qms --user {you} route DOC-ID --review
  - Release/close executable documents you own

You cannot:
  - Assign additional reviewers (Quality only)
  - Approve or reject documents
""",
    "quality": """
As Quality (qa), you can:
  - Assign reviewers to workflows: qms --user qa assign DOC-ID --assignees tu_ui tu_scene
  - Review documents: qms --user qa review DOC-ID --recommend --comment "..."
  - Approve documents: qms --user qa approve DOC-ID
  - Reject documents: qms --user qa reject DOC-ID --comment "..."

You cannot:
  - Create new documents (Initiator only)
  - Route documents for workflows (Initiator only)
""",
    "reviewer": """
As a Reviewer (TU/BU), you can:
  - Review documents when assigned: qms --user {you} review DOC-ID --recommend --comment "..."
  - Approve documents when assigned: qms --user {you} approve DOC-ID
  - Reject documents when assigned: qms --user {you} reject DOC-ID --comment "..."
  - Check your inbox: qms --user {you} inbox
  - Read any document: qms --user {you} read DOC-ID

You cannot:
  - Create documents (Initiator only)
  - Route documents (Initiator only)
  - Assign reviewers (Quality only)
""",
}


# =============================================================================
# Frontmatter Configuration
# =============================================================================

# Author-maintained frontmatter fields (everything else comes from .meta)
AUTHOR_FRONTMATTER_FIELDS = {"title", "revision_summary"}
