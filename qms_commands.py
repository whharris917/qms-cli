"""
QMS CLI Commands Module

This module provides backward compatibility by re-exporting commands
from the new commands/ package. Each command is now in its own file
under commands/ and uses the CommandRegistry pattern.

Created as part of CR-026: QMS CLI Extensibility Refactoring
"""
from typing import Dict, Any, Optional

from qms_io import filter_author_frontmatter
from qms_meta import read_meta

# Import all commands from commands/ package to trigger registration
# and make them available at this module level for backward compatibility
from commands.create import cmd_create
from commands.read import cmd_read
from commands.checkout import cmd_checkout
from commands.checkin import cmd_checkin
from commands.route import cmd_route
from commands.assign import cmd_assign
from commands.review import cmd_review
from commands.approve import cmd_approve
from commands.reject import cmd_reject
from commands.release import cmd_release
from commands.revert import cmd_revert
from commands.close import cmd_close
from commands.status import cmd_status
from commands.inbox import cmd_inbox
from commands.workspace import cmd_workspace
from commands.fix import cmd_fix
from commands.cancel import cmd_cancel
from commands.history import cmd_history
from commands.comments import cmd_comments
from commands.migrate import cmd_migrate
from commands.verify_migration import cmd_verify_migration


def build_full_frontmatter(
    minimal_fm: Dict[str, Any],
    doc_id: str,
    doc_type: str,
    meta: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Build full frontmatter by merging author fields with workflow state from .meta.

    Used when displaying documents (e.g., qms read).
    """
    if meta is None:
        meta = read_meta(doc_id, doc_type) or {}

    # Start with identity fields
    full_fm = {
        "doc_id": doc_id,
        "document_type": doc_type,
    }

    # Add workflow state from .meta
    if meta:
        full_fm["version"] = meta.get("version", "0.1")
        full_fm["status"] = meta.get("status", "DRAFT")
        full_fm["executable"] = meta.get("executable", False)
        full_fm["responsible_user"] = meta.get("responsible_user")
        full_fm["checked_out"] = meta.get("checked_out", False)
        if meta.get("effective_version"):
            full_fm["effective_version"] = meta["effective_version"]

    # Add author-maintained fields
    full_fm.update(filter_author_frontmatter(minimal_fm))

    return full_fm


# Export all commands for backward compatibility
__all__ = [
    "cmd_create",
    "cmd_read",
    "cmd_checkout",
    "cmd_checkin",
    "cmd_route",
    "cmd_assign",
    "cmd_review",
    "cmd_approve",
    "cmd_reject",
    "cmd_release",
    "cmd_revert",
    "cmd_close",
    "cmd_status",
    "cmd_inbox",
    "cmd_workspace",
    "cmd_fix",
    "cmd_cancel",
    "cmd_history",
    "cmd_comments",
    "cmd_migrate",
    "cmd_verify_migration",
    "build_full_frontmatter",
]
