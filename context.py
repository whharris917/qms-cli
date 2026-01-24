"""
QMS Command Context

Provides a shared context object for command execution that encapsulates
common operations like authentication, permission checking, and document lookup.

Created as part of CR-026: QMS CLI Extensibility Refactoring
"""
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional, Dict, Any, List, Set, Tuple

from qms_config import Status, VALID_USERS
from qms_paths import get_doc_type, get_doc_path, get_workspace_path, get_inbox_path
from qms_auth import get_current_user, verify_user_identity, check_permission, get_user_group
from qms_io import parse_frontmatter, read_document
from qms_meta import read_meta


@dataclass
class CommandContext:
    """
    Shared context for command execution.

    Encapsulates common command operations and provides a clean interface
    for commands to access document state, user info, and validation helpers.

    Usage:
        ctx = CommandContext.from_args(args)
        if not ctx.is_valid:
            return 1  # Error already printed

        if not ctx.require_permission("approve"):
            return 1

        if not ctx.require_status({Status.IN_APPROVAL, Status.IN_PRE_APPROVAL}):
            return 1
    """
    # User information
    user: str = ""
    user_group: str = ""

    # Document information (populated by load_document)
    doc_id: str = ""
    doc_type: str = ""
    doc_path: Optional[Path] = None
    draft_path: Optional[Path] = None

    # Document state (from .meta)
    meta: Dict[str, Any] = field(default_factory=dict)
    status: Optional[Status] = None
    version: str = ""
    is_executable: bool = False
    execution_phase: Optional[str] = None
    checked_out: bool = False
    responsible_user: Optional[str] = None
    pending_assignees: List[str] = field(default_factory=list)

    # Frontmatter (from document)
    frontmatter: Dict[str, Any] = field(default_factory=dict)
    body: str = ""

    # Validation state
    is_valid: bool = True
    error_message: str = ""

    @classmethod
    def from_args(cls, args, doc_id: Optional[str] = None) -> "CommandContext":
        """
        Create a CommandContext from argparse args.

        Args:
            args: Parsed arguments from argparse
            doc_id: Optional document ID (uses args.doc_id if not provided)

        Returns:
            Initialized CommandContext
        """
        ctx = cls()

        # Extract user
        ctx.user = get_current_user(args)

        # Validate user identity
        if not verify_user_identity(ctx.user):
            ctx.is_valid = False
            ctx.error_message = f"Unknown user: {ctx.user}"
            return ctx

        ctx.user_group = get_user_group(ctx.user)

        # Load document if doc_id provided
        doc_id = doc_id or getattr(args, "doc_id", None)
        if doc_id:
            ctx.load_document(doc_id)

        return ctx

    def load_document(self, doc_id: str) -> bool:
        """
        Load document information from paths and metadata.

        Args:
            doc_id: Document ID to load

        Returns:
            True if document loaded successfully
        """
        self.doc_id = doc_id
        self.doc_type = get_doc_type(doc_id)

        # Get paths
        self.draft_path = get_doc_path(doc_id, draft=True)
        self.doc_path = get_doc_path(doc_id, draft=False)

        # Load metadata
        self.meta = read_meta(doc_id, self.doc_type) or {}

        # Extract common meta fields
        if self.meta:
            status_str = self.meta.get("status", "DRAFT")
            try:
                self.status = Status(status_str)
            except ValueError:
                self.status = Status.DRAFT

            self.version = self.meta.get("version", "0.1")
            self.is_executable = self.meta.get("executable", False)
            self.execution_phase = self.meta.get("execution_phase")
            self.checked_out = self.meta.get("checked_out", False)
            self.responsible_user = self.meta.get("responsible_user")
            self.pending_assignees = self.meta.get("pending_assignees", [])

        return True

    def load_document_content(self) -> bool:
        """
        Load document frontmatter and body content.

        Returns:
            True if content loaded successfully
        """
        if not self.draft_path:
            return False

        path = self.draft_path if self.draft_path.exists() else self.doc_path
        if not path or not path.exists():
            self.is_valid = False
            self.error_message = f"Document not found: {self.doc_id}"
            return False

        try:
            self.frontmatter, self.body = read_document(path)
            return True
        except Exception as e:
            self.is_valid = False
            self.error_message = f"Failed to read document: {e}"
            return False

    # =========================================================================
    # Permission Helpers
    # =========================================================================

    def require_permission(self, command: str, context: Optional[Dict[str, Any]] = None) -> bool:
        """
        Check if user has permission for a command.

        Args:
            command: Command name (e.g., "approve", "create")
            context: Optional context for permission check

        Returns:
            True if permitted, False if not (error printed)
        """
        allowed, error = check_permission(self.user, command, context)
        if not allowed:
            print(error)
            self.is_valid = False
            self.error_message = error
            return False
        return True

    def require_user_identity(self) -> bool:
        """
        Verify user is a valid QMS user.

        Returns:
            True if valid, False if not (error printed)
        """
        if not verify_user_identity(self.user):
            self.is_valid = False
            self.error_message = f"Unknown user: {self.user}"
            return False
        return True

    # =========================================================================
    # Document State Helpers
    # =========================================================================

    def require_draft_exists(self) -> bool:
        """
        Require that a draft version of the document exists.

        Returns:
            True if draft exists, False if not (error printed)
        """
        if not self.draft_path or not self.draft_path.exists():
            print(f"""
Error: No draft found for {self.doc_id}.

The document may not exist, or it may already be effective.
To create a new document: qms --user {self.user} create TYPE --title "Title"
To check out an effective document: qms --user {self.user} checkout {self.doc_id}
""")
            self.is_valid = False
            return False
        return True

    def require_effective_exists(self) -> bool:
        """
        Require that an effective version of the document exists.

        Returns:
            True if effective exists, False if not (error printed)
        """
        if not self.doc_path or not self.doc_path.exists():
            print(f"""
Error: No effective document found for {self.doc_id}.

The document may still be in draft, or may not exist.
Check document status: qms --user {self.user} status {self.doc_id}
""")
            self.is_valid = False
            return False
        return True

    def require_checked_in(self) -> bool:
        """
        Require that the document is checked in (not checked out).

        Returns:
            True if checked in, False if not (error printed)
        """
        if self.checked_out:
            print(f"""
Error: {self.doc_id} is still checked out by {self.responsible_user or 'unknown'}.

Documents must be checked in before this operation.
If you are the owner, check it in first:
  qms --user {self.responsible_user or self.user} checkin {self.doc_id}
""")
            self.is_valid = False
            return False
        return True

    def require_status(self, allowed_statuses: Set[Status], error_context: str = "") -> bool:
        """
        Require that the document is in one of the allowed statuses.

        Args:
            allowed_statuses: Set of allowed Status values
            error_context: Optional context for error message

        Returns:
            True if status is allowed, False if not (error printed)
        """
        if self.status not in allowed_statuses:
            status_names = ", ".join(s.value for s in allowed_statuses)
            context_msg = f" {error_context}" if error_context else ""
            print(f"""
Error: {self.doc_id} is not in a valid state for this operation{context_msg}.

Current status: {self.status.value if self.status else 'UNKNOWN'}

Valid statuses for this operation:
  {status_names}

Check document status: qms --user {self.user} status {self.doc_id}
""")
            self.is_valid = False
            return False
        return True

    def require_assignment(self) -> bool:
        """
        Require that the current user is assigned to the workflow.

        Returns:
            True if assigned, False if not (error printed)
        """
        if self.user not in self.pending_assignees:
            assignees_str = ", ".join(self.pending_assignees) if self.pending_assignees else "None"
            print(f"""
Error: You ({self.user}) are not assigned to {self.doc_id}.

Currently assigned: {assignees_str}

You can only perform this action on documents you are assigned to.
Check your inbox: qms --user {self.user} inbox

If you should be assigned, ask QA:
  qms --user qa assign {self.doc_id} --assignees {self.user}
""")
            self.is_valid = False
            return False
        return True

    def require_owner(self) -> bool:
        """
        Require that the current user is the document owner.

        Returns:
            True if owner, False if not (error printed)
        """
        if self.responsible_user and self.responsible_user != self.user:
            print(f"""
Error: You ({self.user}) are not the owner of {self.doc_id}.

Current owner: {self.responsible_user}

Only the document owner can perform this operation.
""")
            self.is_valid = False
            return False
        return True

    # =========================================================================
    # Convenience Properties
    # =========================================================================

    @property
    def is_review_status(self) -> bool:
        """Check if document is in a review status."""
        return self.status in {Status.IN_REVIEW, Status.IN_PRE_REVIEW, Status.IN_POST_REVIEW}

    @property
    def is_approval_status(self) -> bool:
        """Check if document is in an approval status."""
        return self.status in {Status.IN_APPROVAL, Status.IN_PRE_APPROVAL, Status.IN_POST_APPROVAL}

    @property
    def is_post_release(self) -> bool:
        """Check if document is in post-release phase."""
        if self.execution_phase == "post_release":
            return True
        if self.status in {Status.IN_EXECUTION, Status.IN_POST_REVIEW,
                          Status.POST_REVIEWED, Status.IN_POST_APPROVAL,
                          Status.POST_APPROVED, Status.CLOSED}:
            return True
        return False

    @property
    def workflow_type(self) -> Optional[str]:
        """Determine workflow type from current status."""
        if self.status == Status.IN_REVIEW:
            return "REVIEW"
        elif self.status == Status.IN_APPROVAL:
            return "APPROVAL"
        elif self.status == Status.IN_PRE_REVIEW:
            return "PRE_REVIEW"
        elif self.status == Status.IN_PRE_APPROVAL:
            return "PRE_APPROVAL"
        elif self.status == Status.IN_POST_REVIEW:
            return "POST_REVIEW"
        elif self.status == Status.IN_POST_APPROVAL:
            return "POST_APPROVAL"
        return None

    def get_reviewed_status(self) -> Optional[Status]:
        """Get the REVIEWED status for current review status."""
        status_map = {
            Status.IN_REVIEW: Status.REVIEWED,
            Status.IN_PRE_REVIEW: Status.PRE_REVIEWED,
            Status.IN_POST_REVIEW: Status.POST_REVIEWED,
        }
        return status_map.get(self.status)

    def get_approved_status(self) -> Optional[Status]:
        """Get the APPROVED status for current approval status."""
        status_map = {
            Status.IN_APPROVAL: Status.APPROVED,
            Status.IN_PRE_APPROVAL: Status.PRE_APPROVED,
            Status.IN_POST_APPROVAL: Status.POST_APPROVED,
        }
        return status_map.get(self.status)

    # =========================================================================
    # Display Helpers
    # =========================================================================

    def print_error(self, message: str) -> None:
        """Print an error message and mark context as invalid."""
        print(f"Error: {message}")
        self.is_valid = False
        self.error_message = message

    def print_success(self, message: str) -> None:
        """Print a success message."""
        print(message)
