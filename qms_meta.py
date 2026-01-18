"""
QMS Metadata Module - Workflow State Management

Handles reading and writing .meta/ JSON files for document workflow state.
These files are managed entirely by the QMS CLI and never touched by humans.
"""

import json
from pathlib import Path
from typing import Any, Dict, List, Optional
from datetime import date

from qms_paths import QMS_ROOT

META_ROOT = QMS_ROOT / ".meta"


def get_meta_dir(doc_type: str) -> Path:
    """Get the .meta directory for a document type."""
    # Handle folder-per-doc types (CR, INV, CAPA, TP, ER)
    # and flat types (SOP, RS, DS, CS, RTM, OQ)
    return META_ROOT / doc_type


def get_meta_path(doc_id: str, doc_type: str) -> Path:
    """Get the .meta file path for a document."""
    meta_dir = get_meta_dir(doc_type)
    return meta_dir / f"{doc_id}.json"


def ensure_meta_dir(doc_type: str) -> Path:
    """Ensure the .meta directory exists for a document type."""
    meta_dir = get_meta_dir(doc_type)
    meta_dir.mkdir(parents=True, exist_ok=True)
    return meta_dir


def read_meta(doc_id: str, doc_type: str) -> Optional[Dict[str, Any]]:
    """
    Read workflow state from .meta file.

    Returns None if file doesn't exist (document may be pre-migration).
    """
    meta_path = get_meta_path(doc_id, doc_type)
    if not meta_path.exists():
        return None

    try:
        with open(meta_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError) as e:
        print(f"Warning: Failed to read meta file {meta_path}: {e}")
        return None


def write_meta(doc_id: str, doc_type: str, meta: Dict[str, Any]) -> bool:
    """
    Write workflow state to .meta file.

    Returns True on success, False on failure.
    """
    ensure_meta_dir(doc_type)
    meta_path = get_meta_path(doc_id, doc_type)

    try:
        with open(meta_path, "w", encoding="utf-8") as f:
            json.dump(meta, f, indent=2, ensure_ascii=False)
        return True
    except IOError as e:
        print(f"Error: Failed to write meta file {meta_path}: {e}")
        return False


def create_initial_meta(
    doc_id: str,
    doc_type: str,
    version: str,
    status: str,
    executable: bool,
    responsible_user: Optional[str] = None
) -> Dict[str, Any]:
    """
    Create initial metadata structure for a new document.

    Args:
        doc_id: Document identifier (e.g., "SOP-001")
        doc_type: Document type (e.g., "SOP", "CR")
        version: Initial version (e.g., "0.1")
        status: Initial status (e.g., "DRAFT")
        executable: Whether document is executable type
        responsible_user: User creating the document (becomes owner)

    Note on execution_phase (per CR-013 / INV-003-CAPA-4):
        - Non-executable documents: always null
        - Executable documents before release: "pre_release"
        - Executable documents after release: "post_release"
    """
    return {
        "doc_id": doc_id,
        "doc_type": doc_type,
        "version": version,
        "status": status,
        "executable": executable,
        "execution_phase": "pre_release" if executable else None,
        "responsible_user": responsible_user,
        "checked_out": True if responsible_user else False,
        "checked_out_date": str(date.today()) if responsible_user else None,
        "effective_version": None,
        "supersedes": None,
        "pending_assignees": []
    }


def update_meta_checkout(
    meta: Dict[str, Any],
    user: str,
    new_version: Optional[str] = None
) -> Dict[str, Any]:
    """
    Update metadata for checkout operation.

    Args:
        meta: Current metadata
        user: User checking out
        new_version: New version if creating draft from effective
    """
    meta = meta.copy()
    meta["responsible_user"] = user
    meta["checked_out"] = True
    meta["checked_out_date"] = str(date.today())
    if new_version:
        meta["version"] = new_version
    return meta


def update_meta_checkin(meta: Dict[str, Any]) -> Dict[str, Any]:
    """
    Update metadata for checkin operation.

    Note: responsible_user persists until approval (per lifecycle rules).

    When checking in from a reviewed state (REVIEWED, PRE_REVIEWED, POST_REVIEWED),
    the status reverts to DRAFT since the new version hasn't been reviewed yet.

    IMPORTANT (per CR-013 / INV-003-CAPA-4): execution_phase is ALWAYS preserved.
    This ensures documents in post_release phase stay in post_release workflow
    after checkout/checkin cycles.
    """
    meta = meta.copy()
    meta["checked_out"] = False
    meta["checked_out_date"] = None

    # execution_phase is preserved - do NOT modify it here
    # This is critical for CAPA-4: post-release documents must stay in post-release workflow

    # Revert reviewed states to DRAFT - new version needs review
    current_status = meta.get("status", "DRAFT")
    if current_status in ("REVIEWED", "PRE_REVIEWED", "POST_REVIEWED"):
        meta["status"] = "DRAFT"
        # Clear review-related fields since we're starting fresh
        meta["pending_reviewers"] = []
        meta["completed_reviewers"] = []
        meta["review_outcomes"] = {}

    return meta


def update_meta_route(
    meta: Dict[str, Any],
    new_status: str,
    assignees: List[str]
) -> Dict[str, Any]:
    """
    Update metadata for routing operation.

    Args:
        meta: Current metadata
        new_status: Target status (e.g., "IN_REVIEW")
        assignees: Users being assigned
    """
    meta = meta.copy()
    meta["status"] = new_status
    meta["pending_assignees"] = assignees
    return meta


def update_meta_review_complete(
    meta: Dict[str, Any],
    user: str,
    remaining_assignees: List[str],
    new_status: Optional[str] = None
) -> Dict[str, Any]:
    """
    Update metadata when a review is submitted.

    Args:
        meta: Current metadata
        user: Reviewer who completed
        remaining_assignees: Assignees still pending
        new_status: New status if all reviews complete
    """
    meta = meta.copy()
    meta["pending_assignees"] = remaining_assignees
    if new_status:
        meta["status"] = new_status
    return meta


def update_meta_approval(
    meta: Dict[str, Any],
    new_status: str,
    new_version: Optional[str] = None,
    clear_owner: bool = False
) -> Dict[str, Any]:
    """
    Update metadata for approval/rejection/effective transition.

    Args:
        meta: Current metadata
        new_status: New status
        new_version: New version if becoming effective
        clear_owner: True when becoming effective (vX.0)
    """
    meta = meta.copy()
    meta["status"] = new_status
    meta["pending_assignees"] = []

    if new_version:
        meta["version"] = new_version

    if clear_owner:
        # Document is becoming effective - clear draft-related fields
        meta["responsible_user"] = None
        meta["checked_out"] = False
        meta["checked_out_date"] = None
        # effective_version = version when document is effective
        meta["effective_version"] = meta["version"]

    return meta


def get_pending_assignees(doc_id: str, doc_type: str) -> List[str]:
    """Get list of pending assignees for a document."""
    meta = read_meta(doc_id, doc_type)
    if meta is None:
        return []
    return meta.get("pending_assignees", [])


def is_user_responsible(doc_id: str, doc_type: str, user: str) -> bool:
    """Check if user is the responsible user for the document."""
    meta = read_meta(doc_id, doc_type)
    if meta is None:
        return False
    return meta.get("responsible_user") == user


def can_user_modify(doc_id: str, doc_type: str, user: str) -> tuple[bool, str]:
    """
    Check if user can modify (checkout/checkin/route) the document.

    Returns (can_modify, reason).
    """
    meta = read_meta(doc_id, doc_type)

    if meta is None:
        # Pre-migration document - fall back to frontmatter check
        return True, "pre-migration"

    responsible = meta.get("responsible_user")

    if responsible is None:
        # Unclaimed document (effective version)
        return True, "unclaimed"

    if responsible == user:
        return True, "owner"

    return False, f"owned by {responsible}"
