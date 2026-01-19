"""
QMS CLI Configuration Module

Contains constants, enums, and configuration data for the QMS CLI.
"""
from enum import Enum


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
    SUPERSEDED = "SUPERSEDED"
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
    Status.EFFECTIVE: [Status.SUPERSEDED],

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
    Status.SUPERSEDED: [],
    Status.RETIRED: [],
}


# =============================================================================
# Document Types
# =============================================================================

DOCUMENT_TYPES = {
    "SOP": {"path": "SOP", "executable": False, "prefix": "SOP"},
    "CR": {"path": "CR", "executable": True, "prefix": "CR", "folder_per_doc": True},
    "INV": {"path": "INV", "executable": True, "prefix": "INV", "folder_per_doc": True},
    "CAPA": {"path": "INV", "executable": True, "prefix": "CAPA", "parent_type": "INV"},
    "TP": {"path": "CR", "executable": True, "prefix": "TP", "parent_type": "CR"},
    "ER": {"path": "CR", "executable": True, "prefix": "ER", "parent_type": "TP"},
    "VAR": {"path": "CR", "executable": True, "prefix": "VAR"},
    "RS": {"path": "SDLC-FLOW", "executable": False, "prefix": "SDLC-FLOW-RS", "singleton": True},
    "DS": {"path": "SDLC-FLOW", "executable": False, "prefix": "SDLC-FLOW-DS", "singleton": True},
    "CS": {"path": "SDLC-FLOW", "executable": False, "prefix": "SDLC-FLOW-CS", "singleton": True},
    "RTM": {"path": "SDLC-FLOW", "executable": False, "prefix": "SDLC-FLOW-RTM", "singleton": True},
    "OQ": {"path": "SDLC-FLOW", "executable": False, "prefix": "SDLC-FLOW-OQ", "singleton": True},
    # SDLC-QMS document types (QMS CLI qualification)
    "QMS-RS": {"path": "SDLC-QMS", "executable": False, "prefix": "SDLC-QMS-RS", "singleton": True},
    "QMS-RTM": {"path": "SDLC-QMS", "executable": False, "prefix": "SDLC-QMS-RTM", "singleton": True},
    # Named document types (name-based rather than numbered)
    "TEMPLATE": {"path": "TEMPLATE", "executable": False, "prefix": "TEMPLATE"},
}


# =============================================================================
# Users and Permissions
# =============================================================================

# Valid QMS users
VALID_USERS = {"lead", "claude", "qa", "bu", "tu_ui", "tu_scene", "tu_sketch", "tu_sim"}

# User group definitions
USER_GROUPS = {
    "initiators": {"lead", "claude"},       # Can create documents, initiate workflows
    "qa": {"qa"},                            # Can modify workflows, review, approve
    "reviewers": {"tu_ui", "tu_scene", "tu_sketch", "tu_sim", "bu"},  # Review/approve only
}

# Permission definitions by command
# "all" = any valid user, "assigned" = must be assigned to workflow
PERMISSIONS = {
    "create":    {"groups": ["initiators"]},
    "checkout":  {"groups": ["initiators"]},
    "checkin":   {"groups": ["initiators"], "owner_only": True},
    "route":     {"groups": ["initiators", "qa"], "owner_only": True},  # CR-032
    "assign":    {"groups": ["qa"]},
    "review":    {"groups": ["initiators", "qa", "reviewers"], "assigned_only": True},
    "approve":   {"groups": ["qa", "reviewers"], "assigned_only": True},
    "reject":    {"groups": ["qa", "reviewers"], "assigned_only": True},
    "release":   {"groups": ["initiators"], "owner_only": True},
    "revert":    {"groups": ["initiators"], "owner_only": True},
    "close":     {"groups": ["initiators"], "owner_only": True},
    "read":      {"groups": ["initiators", "qa", "reviewers"]},
    "status":    {"groups": ["initiators", "qa", "reviewers"]},
    "inbox":     {"groups": ["initiators", "qa", "reviewers"]},
    "workspace": {"groups": ["initiators", "qa", "reviewers"]},
}

# Helpful guidance messages for each group
GROUP_GUIDANCE = {
    "initiators": """
As an Initiator (lead, claude), you can:
  - Create new documents: qms --user {you} create SOP --title "Title"
  - Check out documents for editing: qms --user {you} checkout DOC-ID
  - Check in edited documents: qms --user {you} checkin DOC-ID
  - Route documents for review/approval: qms --user {you} route DOC-ID --review
  - Release/close executable documents you own

You cannot:
  - Assign additional reviewers (QA only)
  - Approve or reject documents
""",
    "qa": """
As QA, you can:
  - Assign reviewers to workflows: qms --user qa assign DOC-ID --assignees tu_ui tu_scene
  - Review documents: qms --user qa review DOC-ID --recommend --comment "..."
  - Approve documents: qms --user qa approve DOC-ID
  - Reject documents: qms --user qa reject DOC-ID --comment "..."

You cannot:
  - Create new documents (Initiators only)
  - Route documents for workflows (Initiators only)
""",
    "reviewers": """
As a Reviewer (TU/BU), you can:
  - Review documents when assigned: qms --user {you} review DOC-ID --recommend --comment "..."
  - Approve documents when assigned: qms --user {you} approve DOC-ID
  - Reject documents when assigned: qms --user {you} reject DOC-ID --comment "..."
  - Check your inbox: qms --user {you} inbox
  - Read any document: qms --user {you} read DOC-ID

You cannot:
  - Create documents (Initiators only)
  - Route documents (Initiators only)
  - Assign reviewers (QA only)
""",
}


# =============================================================================
# Frontmatter Configuration
# =============================================================================

# Author-maintained frontmatter fields (everything else comes from .meta)
AUTHOR_FRONTMATTER_FIELDS = {"title", "revision_summary"}
