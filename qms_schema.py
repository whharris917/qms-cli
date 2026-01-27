"""
QMS Schema Module - Validation Definitions

Provides schema definitions and validation functions for QMS data structures.
Uses simple Python validation rather than external jsonschema dependency.
"""

import re
from typing import Any, Dict, List, Optional, Tuple


# Valid document types
DOC_TYPES = {"SOP", "CR", "INV", "CAPA", "TP", "ER", "VAR", "RS", "DS", "CS", "RTM", "OQ", "QMS-RS", "QMS-RTM", "TEMPLATE"}

# Document types that use folder-per-doc structure
FOLDER_DOC_TYPES = {"CR", "INV", "CAPA", "TP", "ER", "VAR"}

# Executable document types
EXECUTABLE_TYPES = {"CR", "INV", "CAPA", "TP", "ER", "VAR"}

# Valid statuses for non-executable documents
NON_EXECUTABLE_STATUSES = {
    "DRAFT", "IN_REVIEW", "REVIEWED", "IN_APPROVAL", "APPROVED", "EFFECTIVE", "RETIRED"
}

# Valid statuses for executable documents
EXECUTABLE_STATUSES = {
    "DRAFT", "IN_PRE_REVIEW", "PRE_REVIEWED", "IN_PRE_APPROVAL", "PRE_APPROVED",
    "IN_EXECUTION", "IN_POST_REVIEW", "POST_REVIEWED", "IN_POST_APPROVAL",
    "POST_APPROVED", "CLOSED"
}

# Review outcomes
REVIEW_OUTCOMES = {"RECOMMEND", "UPDATES_REQUIRED"}

# Version pattern: N.X where N and X are non-negative integers
VERSION_PATTERN = re.compile(r"^\d+\.\d+$")

# Doc ID patterns by type
DOC_ID_PATTERNS = {
    "SOP": re.compile(r"^SOP-\d{3}$"),
    "CR": re.compile(r"^CR-\d{3}$"),
    "INV": re.compile(r"^INV-\d{3}$"),
    "CAPA": re.compile(r"^CAPA-\d{3}$"),
    "TP": re.compile(r"^TP-\d{3}$"),
    "ER": re.compile(r"^ER-\d{3}$"),
    "VAR": re.compile(r"^(?:CR|INV)-\d{3}-VAR-\d{3}$"),
    # Singleton types (SDLC documents)
    "RS": re.compile(r"^SDLC-FLOW-RS$"),
    "DS": re.compile(r"^SDLC-FLOW-DS$"),
    "CS": re.compile(r"^SDLC-FLOW-CS$"),
    "RTM": re.compile(r"^SDLC-FLOW-RTM$"),
    "OQ": re.compile(r"^SDLC-FLOW-OQ$"),
    # SDLC-QMS document types
    "QMS-RS": re.compile(r"^SDLC-QMS-RS$"),
    "QMS-RTM": re.compile(r"^SDLC-QMS-RTM$"),
    # Named document types (name-based rather than numbered)
    "TEMPLATE": re.compile(r"^TEMPLATE-[A-Z]+$"),
}

# Valid users
VALID_USERS = {"lead", "claude", "qa", "bu", "tu_ui", "tu_scene", "tu_sketch", "tu_sim"}


def validate_version(version: str) -> Tuple[bool, Optional[str]]:
    """
    Validate version string format.

    Returns (is_valid, error_message).
    """
    if not isinstance(version, str):
        return False, f"Version must be string, got {type(version).__name__}"
    if not VERSION_PATTERN.match(version):
        return False, f"Version must be N.X format (e.g., '1.0'), got '{version}'"
    return True, None


def validate_doc_id(doc_id: str, doc_type: Optional[str] = None) -> Tuple[bool, Optional[str]]:
    """
    Validate document ID format.

    Args:
        doc_id: Document identifier to validate
        doc_type: Expected document type (optional, for stricter validation)

    Returns (is_valid, error_message).
    """
    if not isinstance(doc_id, str):
        return False, f"doc_id must be string, got {type(doc_id).__name__}"

    if doc_type and doc_type in DOC_ID_PATTERNS:
        pattern = DOC_ID_PATTERNS[doc_type]
        if not pattern.match(doc_id):
            return False, f"doc_id '{doc_id}' doesn't match pattern for {doc_type}"
        return True, None

    # Generic validation - must start with a valid type prefix
    for dtype, pattern in DOC_ID_PATTERNS.items():
        if pattern.match(doc_id):
            return True, None

    return False, f"doc_id '{doc_id}' doesn't match any known document type pattern"


def validate_status(status: str, executable: bool) -> Tuple[bool, Optional[str]]:
    """
    Validate status for document type.

    Returns (is_valid, error_message).
    """
    if not isinstance(status, str):
        return False, f"Status must be string, got {type(status).__name__}"

    valid_statuses = EXECUTABLE_STATUSES if executable else NON_EXECUTABLE_STATUSES

    if status not in valid_statuses:
        type_name = "executable" if executable else "non-executable"
        return False, f"Invalid status '{status}' for {type_name} document"

    return True, None


def validate_user(user: str) -> Tuple[bool, Optional[str]]:
    """
    Validate user identifier.

    Returns (is_valid, error_message).
    """
    if not isinstance(user, str):
        return False, f"User must be string, got {type(user).__name__}"
    if user not in VALID_USERS:
        return False, f"Unknown user '{user}'. Valid users: {', '.join(sorted(VALID_USERS))}"
    return True, None


def validate_meta(meta: Dict[str, Any]) -> List[str]:
    """
    Validate metadata structure.

    Returns list of error messages (empty if valid).
    """
    errors = []

    # Required fields
    required = ["doc_id", "doc_type", "version", "status", "executable"]
    for field in required:
        if field not in meta:
            errors.append(f"Missing required field: {field}")

    if errors:
        return errors  # Can't continue without required fields

    # Validate types
    doc_id = meta["doc_id"]
    doc_type = meta["doc_type"]
    version = meta["version"]
    status = meta["status"]
    executable = meta["executable"]

    # doc_type
    if doc_type not in DOC_TYPES:
        errors.append(f"Invalid doc_type: {doc_type}")

    # doc_id
    valid, err = validate_doc_id(doc_id, doc_type if doc_type in DOC_TYPES else None)
    if not valid:
        errors.append(err)

    # version
    valid, err = validate_version(version)
    if not valid:
        errors.append(err)

    # executable
    if not isinstance(executable, bool):
        errors.append(f"executable must be boolean, got {type(executable).__name__}")
    else:
        # Verify executable matches doc_type
        expected_executable = doc_type in EXECUTABLE_TYPES
        if executable != expected_executable:
            errors.append(f"executable={executable} doesn't match doc_type={doc_type}")

        # status
        valid, err = validate_status(status, executable)
        if not valid:
            errors.append(err)

    # Optional fields with type checks
    if "responsible_user" in meta and meta["responsible_user"] is not None:
        valid, err = validate_user(meta["responsible_user"])
        if not valid:
            errors.append(err)

    if "checked_out" in meta and not isinstance(meta["checked_out"], bool):
        errors.append(f"checked_out must be boolean, got {type(meta['checked_out']).__name__}")

    if "pending_assignees" in meta:
        assignees = meta["pending_assignees"]
        if not isinstance(assignees, list):
            errors.append(f"pending_assignees must be list, got {type(assignees).__name__}")
        else:
            for i, user in enumerate(assignees):
                valid, err = validate_user(user)
                if not valid:
                    errors.append(f"pending_assignees[{i}]: {err}")

    return errors


def validate_frontmatter(frontmatter: Dict[str, Any]) -> List[str]:
    """
    Validate minimal author-maintained frontmatter.

    Expected fields: title, revision_summary (optional for new docs)

    Returns list of error messages (empty if valid).
    """
    errors = []

    # title is required
    if "title" not in frontmatter:
        errors.append("Missing required field: title")
    elif not isinstance(frontmatter["title"], str):
        errors.append(f"title must be string, got {type(frontmatter['title']).__name__}")
    elif not frontmatter["title"].strip():
        errors.append("title cannot be empty")

    # revision_summary is optional but must be string if present
    if "revision_summary" in frontmatter:
        if not isinstance(frontmatter["revision_summary"], str):
            errors.append(f"revision_summary must be string, got {type(frontmatter['revision_summary']).__name__}")

    return errors


def validate_audit_event(event: Dict[str, Any]) -> List[str]:
    """
    Validate audit event structure.

    Returns list of error messages (empty if valid).
    """
    errors = []

    # Required fields for all events
    required = ["ts", "event", "user", "version"]
    for field in required:
        if field not in event:
            errors.append(f"Missing required field: {field}")

    if errors:
        return errors

    # Validate types
    if not isinstance(event["ts"], str):
        errors.append(f"ts must be string, got {type(event['ts']).__name__}")

    if not isinstance(event["event"], str):
        errors.append(f"event must be string, got {type(event['event']).__name__}")

    valid, err = validate_user(event["user"])
    if not valid:
        errors.append(err)

    valid, err = validate_version(event["version"])
    if not valid:
        errors.append(err)

    # Event-specific validation
    event_type = event.get("event")

    if event_type == "REVIEW":
        if "outcome" not in event:
            errors.append("REVIEW event requires outcome field")
        elif event["outcome"] not in REVIEW_OUTCOMES:
            errors.append(f"Invalid review outcome: {event['outcome']}")

        if "comment" not in event:
            errors.append("REVIEW event requires comment field")

    elif event_type == "REJECT":
        if "comment" not in event:
            errors.append("REJECT event requires comment field")

    elif event_type in ("ROUTE_REVIEW", "ROUTE_APPROVAL"):
        if "assignees" not in event:
            errors.append(f"{event_type} event requires assignees field")
        elif not isinstance(event["assignees"], list):
            errors.append("assignees must be list")

    return errors


def is_major_version(version: str) -> bool:
    """Check if version is a major version (X.0)."""
    if not VERSION_PATTERN.match(version):
        return False
    parts = version.split(".")
    return parts[1] == "0"


def increment_minor_version(version: str) -> str:
    """Increment minor version (N.X -> N.X+1)."""
    parts = version.split(".")
    major = int(parts[0])
    minor = int(parts[1]) + 1
    return f"{major}.{minor}"


def increment_major_version(version: str) -> str:
    """Increment major version (N.X -> N+1.0)."""
    parts = version.split(".")
    major = int(parts[0]) + 1
    return f"{major}.0"


def get_doc_type_from_id(doc_id: str) -> Optional[str]:
    """Extract document type from doc_id."""
    for doc_type, pattern in DOC_ID_PATTERNS.items():
        if pattern.match(doc_id):
            return doc_type
    return None
