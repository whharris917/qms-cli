#!/usr/bin/env python3
# Environment Verified
"""
QMS - Quality Management System CLI

Document control system for the Flow State project.
See SOP-001 for complete documentation.

Usage:
    python qms-cli/qms.py <command> [options]

Commands:
    create, read, checkout, checkin, route, review, approve, reject,
    release, revert, close, status, inbox, workspace
"""

import argparse
import os
import sys
import shutil
import re
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any, Tuple
from enum import Enum
import yaml

# Import new metadata management modules
from qms_meta import (
    read_meta, write_meta, create_initial_meta,
    update_meta_checkout, update_meta_checkin, update_meta_route,
    update_meta_review_complete, update_meta_approval,
    get_pending_assignees, is_user_responsible, can_user_modify,
    get_meta_path, ensure_meta_dir
)
from qms_audit import (
    read_audit_log, get_comments, get_latest_version_comments,
    log_create, log_checkout, log_checkin, log_route_review, log_route_approval,
    log_review, log_approve, log_reject, log_effective, log_release, log_revert, log_close,
    log_retire, log_status_change, format_audit_history, format_comments
)
from qms_schema import get_doc_type_from_id, increment_minor_version, increment_major_version


# =============================================================================
# Configuration
# =============================================================================

# Find project root (directory containing QMS/)
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


PROJECT_ROOT = find_project_root()
QMS_ROOT = PROJECT_ROOT / "QMS"
ARCHIVE_ROOT = QMS_ROOT / ".archive"
USERS_ROOT = PROJECT_ROOT / ".claude" / "users"

# Document type configurations
DOCUMENT_TYPES = {
    "SOP": {"path": "SOP", "executable": False, "prefix": "SOP"},
    "CR": {"path": "CR", "executable": True, "prefix": "CR", "folder_per_doc": True},
    "INV": {"path": "INV", "executable": True, "prefix": "INV", "folder_per_doc": True},
    "CAPA": {"path": "INV", "executable": True, "prefix": "CAPA", "parent_type": "INV"},
    "TP": {"path": "CR", "executable": True, "prefix": "TP", "parent_type": "CR"},
    "ER": {"path": "CR", "executable": True, "prefix": "ER", "parent_type": "TP"},
    "RS": {"path": "SDLC-FLOW", "executable": False, "prefix": "SDLC-FLOW-RS", "singleton": True},
    "DS": {"path": "SDLC-FLOW", "executable": False, "prefix": "SDLC-FLOW-DS", "singleton": True},
    "CS": {"path": "SDLC-FLOW", "executable": False, "prefix": "SDLC-FLOW-CS", "singleton": True},
    "RTM": {"path": "SDLC-FLOW", "executable": False, "prefix": "SDLC-FLOW-RTM", "singleton": True},
    "OQ": {"path": "SDLC-FLOW", "executable": False, "prefix": "SDLC-FLOW-OQ", "singleton": True},
    # Named document types (name-based rather than numbered)
    "TEMPLATE": {"path": "TEMPLATE", "executable": False, "prefix": "TEMPLATE"},
}


# =============================================================================
# Status Enums
# =============================================================================

class Status(Enum):
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


# Valid transitions
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
# Utilities
# =============================================================================

def get_current_user(args) -> str:
    """Get the current QMS user from the --user command-line argument."""
    user = getattr(args, 'user', None)
    if not user:
        print("Error: --user argument is required.")
        print("Specify your identity with: --user <username>")
        print("Valid users: lead, claude, qa, bu, tu_ui, tu_scene, tu_sketch, tu_sim")
        sys.exit(1)
    return user


# Valid QMS users
VALID_USERS = {"lead", "claude", "qa", "bu", "tu_ui", "tu_scene", "tu_sketch", "tu_sim"}

# =============================================================================
# User Groups & Permissions
# =============================================================================

# User group definitions
USER_GROUPS = {
    "initiators": {"lead", "claude"},      # Can create documents, initiate workflows
    "qa": {"qa"},                           # Can modify workflows, review, approve
    "reviewers": {"tu_ui", "tu_scene", "tu_sketch", "tu_sim", "bu"},  # Review/approve only
}

# Permission definitions by command
# "all" = any valid user, "assigned" = must be assigned to workflow
PERMISSIONS = {
    "create":    {"groups": ["initiators"]},
    "checkout":  {"groups": ["initiators"]},
    "checkin":   {"groups": ["initiators"], "owner_only": True},
    "route":     {"groups": ["initiators", "qa"]},
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


def get_user_group(user: str) -> str:
    """Get the group a user belongs to."""
    for group_name, members in USER_GROUPS.items():
        if user in members:
            return group_name
    return "unknown"


def check_permission(user: str, command: str, doc_owner: str = None, assigned_users: List[str] = None) -> tuple[bool, str]:
    """
    Check if user has permission to execute a command.
    Returns (allowed, error_message).
    """
    if command not in PERMISSIONS:
        return True, ""  # Unknown command, let it through

    perm = PERMISSIONS[command]
    user_group = get_user_group(user)
    allowed_groups = perm.get("groups", [])

    # Check group membership
    if user_group not in allowed_groups:
        group_names = ", ".join(allowed_groups)
        error = f"""
Permission Denied: '{command}' command

Your role: {user_group} ({user})
Required role(s): {group_names}

{GROUP_GUIDANCE.get(user_group, '')}
"""
        return False, error

    # Check owner requirement
    if perm.get("owner_only") and doc_owner and doc_owner != user:
        # For initiators, any initiator can act on behalf of documents
        if user_group == "initiators" and doc_owner in USER_GROUPS.get("initiators", set()):
            pass  # Allow initiators to act on each other's documents
        else:
            error = f"""
Permission Denied: '{command}' command

You ({user}) are not the responsible user for this document.
Responsible user: {doc_owner}

Only the document owner or another Initiator can perform this action.
"""
            return False, error

    # Check assignment requirement
    if perm.get("assigned_only") and assigned_users is not None:
        if user not in assigned_users:
            error = f"""
Permission Denied: '{command}' command

You ({user}) are not assigned to this workflow.
Assigned users: {', '.join(assigned_users) if assigned_users else 'None'}

You can only {command} documents you are assigned to.
Check your inbox for assigned tasks: qms --user {user} inbox
"""
            return False, error

    return True, ""


def verify_user_identity(user: str) -> bool:
    """Verify that the user is a valid QMS user."""
    if user not in VALID_USERS:
        print(f"""
Error: '{user}' is not a valid QMS user.

Valid users by group:
  Initiators: {', '.join(sorted(USER_GROUPS['initiators']))}
  QA:         {', '.join(sorted(USER_GROUPS['qa']))}
  Reviewers:  {', '.join(sorted(USER_GROUPS['reviewers']))}

Specify your identity with: qms --user <username> <command>
""")
        return False
    return True


def verify_folder_access(user: str, target_user: str, operation: str) -> bool:
    """Verify that user has access to target_user's folder."""
    if user != target_user:
        print(f"""
Error: Access denied.

User '{user}' cannot {operation} for user '{target_user}'.
You can only access your own inbox and workspace.

Commands:
  qms --user {user} inbox      - View your pending tasks
  qms --user {user} workspace  - View your checked-out documents
""")
        return False
    return True


def parse_frontmatter(content: str) -> tuple[Dict[str, Any], str]:
    """Parse YAML frontmatter from markdown content."""
    if not content.startswith("---"):
        return {}, content

    parts = content.split("---", 2)
    if len(parts) < 3:
        return {}, content

    try:
        frontmatter = yaml.safe_load(parts[1])
        body = parts[2].lstrip("\n")
        return frontmatter or {}, body
    except yaml.YAMLError:
        return {}, content


def serialize_frontmatter(frontmatter: Dict[str, Any], body: str) -> str:
    """Serialize frontmatter and body back to markdown."""
    yaml_str = yaml.dump(frontmatter, default_flow_style=False, sort_keys=False, allow_unicode=True)
    return f"---\n{yaml_str}---\n\n{body}"


def read_document(path: Path) -> tuple[Dict[str, Any], str]:
    """Read a document and parse its frontmatter."""
    if not path.exists():
        raise FileNotFoundError(f"Document not found: {path}")
    content = path.read_text(encoding="utf-8")
    return parse_frontmatter(content)


def write_document(path: Path, frontmatter: Dict[str, Any], body: str):
    """Write a document with frontmatter."""
    path.parent.mkdir(parents=True, exist_ok=True)
    content = serialize_frontmatter(frontmatter, body)
    path.write_text(content, encoding="utf-8")


# Author-maintained frontmatter fields (everything else comes from .meta)
AUTHOR_FRONTMATTER_FIELDS = {"title", "revision_summary"}


def filter_author_frontmatter(frontmatter: Dict[str, Any]) -> Dict[str, Any]:
    """Extract only author-maintained fields from frontmatter."""
    return {k: v for k, v in frontmatter.items() if k in AUTHOR_FRONTMATTER_FIELDS}


def write_document_minimal(path: Path, frontmatter: Dict[str, Any], body: str):
    """Write a document with minimal (author-maintained only) frontmatter."""
    minimal_fm = filter_author_frontmatter(frontmatter)
    write_document(path, minimal_fm, body)


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


def today() -> str:
    """Get today's date as YYYY-MM-DD."""
    return datetime.now().strftime("%Y-%m-%d")


# =============================================================================
# Review Task Content Generation (CR-012: QA Review Safeguards)
# =============================================================================

def generate_review_task_content(
    doc_id: str,
    version: str,
    workflow_type: str,
    assignee: str,
    assigned_by: str,
    task_id: str
) -> str:
    """Generate enhanced review task content with mandatory checklist."""
    return f"""---
task_id: {task_id}
task_type: REVIEW
workflow_type: {workflow_type}
doc_id: {doc_id}
assigned_by: {assigned_by}
assigned_date: {today()}
version: {version}
---

# REVIEW REQUEST: {doc_id}

**Workflow:** {workflow_type}
**Version:** {version}
**Assigned By:** {assigned_by}
**Date:** {today()}

---

## MANDATORY VERIFICATION CHECKLIST

**YOU MUST verify each item below. ANY failure = REJECT.**

Before submitting your review, complete this checklist:

### Frontmatter Verification

| Item | Status | Evidence (quote actual value) |
|------|--------|-------------------------------|
| `title:` field present and non-empty | PASS / FAIL | |
| `revision_summary:` present (required for v1.0+) | PASS / FAIL / N/A | |
| `revision_summary:` begins with CR ID (e.g., "CR-XXX:") | PASS / FAIL / N/A | |

### Document Structure

| Item | Status | Evidence |
|------|--------|----------|
| Document follows type-specific template | PASS / FAIL | |
| All required sections present | PASS / FAIL | |
| Section numbering sequential and correct | PASS / FAIL | |

### Content Integrity

| Item | Status | Evidence |
|------|--------|----------|
| No placeholder text (TBD, TODO, XXX, FIXME) | PASS / FAIL | |
| No obvious factual errors or contradictions | PASS / FAIL | |
| References to other documents are valid | PASS / FAIL | |
| No typos or grammatical errors | PASS / FAIL | |
| Formatting consistent throughout | PASS / FAIL | |

---

## STRUCTURED REVIEW RESPONSE FORMAT

Your review comment MUST follow this format:

```
## {assignee} Review: {doc_id}

### Checklist Verification

| Item | Status | Evidence |
|------|--------|----------|
| Frontmatter: title present | PASS/FAIL | "[quoted value]" or "MISSING" |
| Frontmatter: revision_summary present | PASS/FAIL/N/A | "[quoted value]" or "N/A for v0.x" |
| Frontmatter: CR ID in revision_summary | PASS/FAIL/N/A | "[CR-XXX]" or "N/A" |
| Template compliance | PASS/FAIL | [note deviation if any] |
| Required sections present | PASS/FAIL | [list sections] |
| No placeholder content | PASS/FAIL | "None found" or "[quoted]" |
| No typos/errors | PASS/FAIL | "None found" or "[list]" |
| Formatting consistent | PASS/FAIL | [note inconsistency if any] |

### Findings

[List ALL findings. Every finding is a deficiency.]

1. [Finding or "No findings"]

### Recommendation

[RECOMMEND / REQUEST UPDATES] - [Brief rationale]
```

---

## CRITICAL REMINDERS

- **Compliance is BINARY**: Document is either compliant or non-compliant
- **ONE FAILED ITEM = REJECT**: No exceptions, no "minor issues"
- **VERIFY WITH EVIDENCE**: Quote actual values, do not assume
- **REJECTION IS CORRECT**: A rejected document prevents nonconformance

**There is no "approve with comments." There is no severity classification.**
**If ANY deficiency exists, the only valid outcome is REQUEST UPDATES.**

---

## Commands

Submit your review:

**If ALL items PASS:**
```
/qms --user {assignee} review {doc_id} --recommend --comment "[your structured review]"
```

**If ANY item FAILS:**
```
/qms --user {assignee} review {doc_id} --request-updates --comment "[your structured review with findings]"
```
"""


def generate_approval_task_content(
    doc_id: str,
    version: str,
    workflow_type: str,
    assignee: str,
    assigned_by: str,
    task_id: str
) -> str:
    """Generate enhanced approval task content with final verification."""
    return f"""---
task_id: {task_id}
task_type: APPROVAL
workflow_type: {workflow_type}
doc_id: {doc_id}
assigned_by: {assigned_by}
assigned_date: {today()}
version: {version}
---

# APPROVAL REQUEST: {doc_id}

**Workflow:** {workflow_type}
**Version:** {version}
**Assigned By:** {assigned_by}
**Date:** {today()}

---

## FINAL VERIFICATION - YOU ARE THE LAST LINE OF DEFENSE

Before approving, you MUST confirm:

### Pre-Approval Checklist

| Item | Verified |
|------|----------|
| Frontmatter complete (title, revision_summary with CR ID if v1.0+) | YES / NO |
| All review findings from previous cycle addressed | YES / NO |
| No new deficiencies introduced since review | YES / NO |
| Document is 100% compliant with all requirements | YES / NO |

**If ANY item is NO: REJECT**

---

## CRITICAL REMINDERS

- An incorrectly approved document creates **nonconformance**
- A rejected document creates a **correction cycle** (much lower cost)
- **Rejection is always the safer choice**
- You are the final gatekeeper - if you miss something, it becomes effective

**IF ANY DOUBT EXISTS: REJECT**

---

## Commands

**Approve (only if 100% compliant):**
```
/qms --user {assignee} approve {doc_id}
```

**Reject (if any deficiency):**
```
/qms --user {assignee} reject {doc_id} --comment "[reason for rejection]"
```
"""


# =============================================================================
# Template Loading (CR-019)
# =============================================================================

def strip_template_comments(body: str) -> str:
    """Remove TEMPLATE DOCUMENT NOTICE comment block (template metadata only).

    Note: TEMPLATE USAGE GUIDE is intentionally preserved - it provides guidance
    for document authors and should be manually deleted after reading.
    """
    # Pattern matches the TEMPLATE DOCUMENT NOTICE block only
    # Uses flexible matching for equals signs (70-82 characters) and whitespace
    pattern = r'<!--\s*={70,82}\s*TEMPLATE DOCUMENT NOTICE\s*={70,82}\s*.*?={70,82}\s*-->\s*'
    return re.sub(pattern, '', body, flags=re.DOTALL)


def create_minimal_template(doc_id: str, title: str) -> Tuple[Dict[str, Any], str]:
    """Create minimal fallback template when no TEMPLATE document exists."""
    frontmatter = {"title": title}
    body = f"""# {doc_id}: {title}

## 1. Purpose

[Describe the purpose of this document]

---

## 2. Scope

[Define what this document covers]

---

## 3. Content

[Main content here]

---

**END OF DOCUMENT**
"""
    return frontmatter, body


def load_template_for_type(doc_type: str, doc_id: str, title: str) -> Tuple[Dict[str, Any], str]:
    """
    Load template for document type and substitute placeholders.

    Returns (frontmatter, body) tuple ready for new document creation.
    Falls back to minimal template if TEMPLATE-{type} doesn't exist.
    """
    template_id = f"TEMPLATE-{doc_type}"
    template_path = QMS_ROOT / "TEMPLATE" / f"{template_id}.md"

    if not template_path.exists():
        return create_minimal_template(doc_id, title)

    # Read raw template file
    content = template_path.read_text(encoding="utf-8")

    # Find the "example frontmatter" - the second --- block
    # Template structure: [template frontmatter] [notice] [example frontmatter] [guide] [body]
    parts = content.split("---")
    if len(parts) < 5:
        # Malformed template, fall back
        return create_minimal_template(doc_id, title)

    # Reconstruct from example frontmatter onward (parts[3] is example FM, parts[4+] is body)
    example_fm_raw = parts[3].strip()
    body_parts = "---".join(parts[4:])

    # Parse example frontmatter
    import yaml
    try:
        example_fm = yaml.safe_load(example_fm_raw) or {}
    except yaml.YAMLError:
        example_fm = {}

    # Strip template comment blocks from body
    body = strip_template_comments(body_parts)

    # Replace placeholders
    body = body.replace("{{TITLE}}", title)
    body = body.replace(f"{doc_type}-XXX", doc_id)

    # Update frontmatter with actual title and default revision_summary
    frontmatter = {
        "title": title,
        "revision_summary": "Initial draft",
    }

    return frontmatter, body.strip() + "\n"


# =============================================================================
# Commands
# =============================================================================

def cmd_create(args):
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


def cmd_read(args):
    """Read a document."""
    doc_id = args.doc_id

    try:
        if args.version:
            # Read specific archived version
            path = get_archive_path(doc_id, args.version)
        elif args.draft:
            path = get_doc_path(doc_id, draft=True)
        else:
            # Read effective version, fall back to draft
            path = get_doc_path(doc_id, draft=False)
            if not path.exists():
                path = get_doc_path(doc_id, draft=True)

        if not path.exists():
            print(f"Error: Document not found: {doc_id}")
            return 1

        content = path.read_text(encoding="utf-8")
        print(content)
        return 0

    except Exception as e:
        print(f"Error: {e}")
        return 1


def cmd_checkout(args):
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

    if draft_path.exists():
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
        meta = update_meta_checkout(meta, user)
        write_meta(doc_id, doc_type, meta)

        # Log CHECKOUT event
        log_checkout(doc_id, doc_type, user, version)

        # Write content to workspace
        workspace_path = get_workspace_path(user, doc_id)
        workspace_path.parent.mkdir(parents=True, exist_ok=True)
        write_document_minimal(workspace_path, frontmatter, body)

    elif effective_path.exists():
        # Create new draft from effective
        content = effective_path.read_text(encoding="utf-8")
        frontmatter, body = parse_frontmatter(content)

        current_version = meta.get("version", "1.0")
        major = int(str(current_version).split(".")[0])
        new_version = f"{major}.1"

        # Archive effective version before creating draft (per CR-005)
        archive_path = get_archive_path(doc_id, current_version)
        archive_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(effective_path, archive_path)
        print(f"Archived: v{current_version}")

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
        write_document_minimal(workspace_path, frontmatter, body)

        print(f"Created draft v{new_version} from effective v{current_version}")
    else:
        print(f"Error: Document not found: {doc_id}")
        return 1

    print(f"Checked out: {doc_id}")
    print(f"Workspace: {workspace_path.relative_to(PROJECT_ROOT)}")

    return 0


def cmd_checkin(args):
    """Check in a document from workspace."""
    doc_id = args.doc_id
    user = get_current_user(args)

    if not verify_user_identity(user):
        return 1

    # Permission check (group level)
    allowed, error = check_permission(user, "checkin")
    if not allowed:
        print(error)
        return 1

    workspace_path = get_workspace_path(user, doc_id)
    if not workspace_path.exists():
        print(f"""
Error: {doc_id} not found in your workspace.

Your workspace contains documents you have checked out for editing.
To check out a document: qms --user {user} checkout {doc_id}
To see your workspace: qms --user {user} workspace
""")
        return 1

    draft_path = get_doc_path(doc_id, draft=True)
    doc_type = get_doc_type(doc_id)
    meta = read_meta(doc_id, doc_type) or {}

    # Verify user has it checked out (ownership check via .meta)
    doc_owner = meta.get("responsible_user")
    allowed, error = check_permission(user, "checkin", doc_owner=doc_owner)
    if not allowed:
        print(error)
        return 1

    # Read workspace version
    frontmatter, body = read_document(workspace_path)

    # Get version from .meta (authoritative source)
    version = meta.get("version", frontmatter.get("version", "0.1"))

    # Write content to QMS draft with minimal frontmatter
    write_document_minimal(draft_path, frontmatter, body)

    # Update .meta file
    meta = update_meta_checkin(meta)
    write_meta(doc_id, doc_type, meta)

    # Log CHECKIN event
    log_checkin(doc_id, doc_type, user, version)

    # Remove from workspace
    workspace_path.unlink()

    print(f"Checked in: {doc_id} (v{version})")

    return 0


def cmd_route(args):
    """Route a document for review or approval."""
    doc_id = args.doc_id
    user = get_current_user(args)

    if not verify_user_identity(user):
        return 1

    # Permission check (group level)
    allowed, error = check_permission(user, "route")
    if not allowed:
        print(error)
        return 1

    draft_path = get_doc_path(doc_id, draft=True)
    if not draft_path.exists():
        print(f"""
Error: No draft found for {doc_id}.

The document may not exist, or it may already be effective.
To create a new document: qms --user {user} create SOP --title "Title"
To check out an effective document for revision: qms --user {user} checkout {doc_id}
""")
        return 1

    # Get workflow state from .meta (authoritative source)
    doc_type = get_doc_type(doc_id)
    meta = read_meta(doc_id, doc_type) or {}

    # Verify document is checked in (not checked out)
    if meta.get("checked_out"):
        checked_out_by = meta.get("responsible_user", "unknown")
        print(f"""
Error: {doc_id} is still checked out by {checked_out_by}.

Documents must be checked in before routing for review/approval.
The workflow operates on the QMS copy, not the workspace copy.

If you are the owner, check it in first:
  qms --user {checked_out_by} checkin {doc_id}

Then route for review:
  qms --user {checked_out_by} route {doc_id} --review
""")
        return 1

    current_status = Status(meta.get("status", "DRAFT"))
    is_executable = meta.get("executable", False)
    # CAPA-4: Use execution_phase to determine workflow path (not just current status)
    # This ensures documents that were checked out and back in after release
    # continue in the post-release workflow
    execution_phase = meta.get("execution_phase")

    # Determine target status based on flags
    # For executable docs, use execution_phase to determine pre vs post workflow
    if args.review:
        if is_executable:
            # CAPA-4: Use execution_phase (if set) to determine workflow path
            # Also handle legacy documents without execution_phase by checking status
            is_post_release = (execution_phase == "post_release" or
                               current_status == Status.IN_EXECUTION)
            if is_post_release:
                # Post-release: route to post-review (even if status is DRAFT after checkout/checkin)
                if current_status in (Status.DRAFT, Status.IN_EXECUTION):
                    target_status = Status.IN_POST_REVIEW
                    workflow_type = "POST_REVIEW"
                else:
                    print(f"Error: Cannot route for post-review from {current_status.value}")
                    print("  Post-review routing is valid from: DRAFT, IN_EXECUTION")
                    return 1
            else:
                # Pre-release: route to pre-review
                if current_status == Status.DRAFT:
                    target_status = Status.IN_PRE_REVIEW
                    workflow_type = "PRE_REVIEW"
                else:
                    print(f"Error: Cannot route for pre-review from {current_status.value}")
                    print("  Pre-review routing is valid from: DRAFT")
                    return 1
        else:
            target_status = Status.IN_REVIEW
            workflow_type = "REVIEW"
    elif args.approval:
        if is_executable:
            # CAPA-4: Use execution_phase to determine workflow path
            # Also handle legacy documents without execution_phase by checking status
            is_post_release = (execution_phase == "post_release" or
                               current_status == Status.POST_REVIEWED)
            if is_post_release:
                # Post-release: route to post-approval
                if current_status == Status.POST_REVIEWED:
                    target_status = Status.IN_POST_APPROVAL
                    workflow_type = "POST_APPROVAL"
                else:
                    print(f"Error: Cannot route for post-approval from {current_status.value}")
                    print("  Post-approval routing is valid from: POST_REVIEWED")
                    return 1
            else:
                # Pre-release: route to pre-approval
                if current_status == Status.PRE_REVIEWED:
                    target_status = Status.IN_PRE_APPROVAL
                    workflow_type = "PRE_APPROVAL"
                else:
                    print(f"Error: Cannot route for pre-approval from {current_status.value}")
                    print("  Pre-approval routing is valid from: PRE_REVIEWED")
                    return 1
        else:
            if current_status != Status.REVIEWED:
                print(f"Error: Must be REVIEWED before approval (currently {current_status.value})")
                return 1
            target_status = Status.IN_APPROVAL
            workflow_type = "APPROVAL"
    else:
        print("Error: Must specify workflow type (--review or --approval)")
        return 1

    # Handle --retire flag
    if getattr(args, 'retire', False):
        # --retire only applies to final approval routing
        if workflow_type not in ("APPROVAL", "POST_APPROVAL"):
            print("Error: --retire only applies to --approval routing (for final approval phase)")
            return 1
        # Set retiring flag in meta (will be checked during approval)
        meta["retiring"] = True

    # Auto-assign QA if no --assign provided
    assignees = args.assign if args.assign else ["qa"]

    # Validate transition
    if target_status not in TRANSITIONS.get(current_status, []):
        print(f"Error: Cannot transition from {current_status.value} to {target_status.value}")
        return 1

    # Update .meta file (authoritative workflow state)
    version = meta.get("version", "0.1")
    meta = update_meta_route(meta, target_status.value, assignees)
    write_meta(doc_id, doc_type, meta)

    # Log status change (CAPA-3: audit trail completeness)
    log_status_change(doc_id, doc_type, user, version, current_status.value, target_status.value)

    # Log routing event to audit trail
    if "REVIEW" in workflow_type:
        log_route_review(doc_id, doc_type, user, version, assignees, workflow_type)
    else:
        log_route_approval(doc_id, doc_type, user, version, assignees, workflow_type)

    # Create tasks in assignee inboxes (CR-012: Enhanced with QA Review Safeguards)
    for assignee in assignees:
        inbox_path = get_inbox_path(assignee)
        inbox_path.mkdir(parents=True, exist_ok=True)

        task_type = "REVIEW" if "REVIEW" in workflow_type else "APPROVAL"
        task_id = f"task-{doc_id}-{workflow_type.lower()}-v{version.replace('.', '-')}"
        task_path = inbox_path / f"{task_id}.md"

        # Generate enhanced task content with mandatory checklist and structured format
        if task_type == "REVIEW":
            task_content = generate_review_task_content(
                doc_id=doc_id,
                version=version,
                workflow_type=workflow_type,
                assignee=assignee,
                assigned_by=user,
                task_id=task_id
            )
        else:
            task_content = generate_approval_task_content(
                doc_id=doc_id,
                version=version,
                workflow_type=workflow_type,
                assignee=assignee,
                assigned_by=user,
                task_id=task_id
            )

        task_path.write_text(task_content, encoding="utf-8")

    print(f"Routed: {doc_id} for {workflow_type}")
    print(f"Status: {current_status.value} -> {target_status.value}")
    print(f"Assigned to: {', '.join(assignees)}")

    return 0


def cmd_assign(args):
    """Add reviewers/approvers to an active workflow."""
    doc_id = args.doc_id
    user = get_current_user(args)

    if not verify_user_identity(user):
        return 1

    # Permission check - only QA can assign
    allowed, error = check_permission(user, "assign")
    if not allowed:
        print(error)
        return 1

    new_assignees = args.assignees
    if not new_assignees:
        print("""
Error: Must specify --assignees with at least one user to assign.

Usage: qms --user qa assign DOC-ID --assignees user1 user2 ...

Example:
  qms --user qa assign SOP-003 --assignees tu_ui tu_scene

Valid users to assign:
  Technical Units: tu_ui, tu_scene, tu_sketch, tu_sim
  Business Unit: bu
""")
        return 1

    # Validate assignees are valid users
    invalid_users = [u for u in new_assignees if u not in VALID_USERS]
    if invalid_users:
        print(f"""
Error: Invalid user(s): {', '.join(invalid_users)}

Valid users to assign:
  Technical Units: tu_ui, tu_scene, tu_sketch, tu_sim
  Business Unit: bu
  QA: qa
  Initiators: lead, claude
""")
        return 1

    draft_path = get_doc_path(doc_id, draft=True)
    if not draft_path.exists():
        print(f"""
Error: No draft found for {doc_id}.

You can only assign users to documents that are in an active workflow.
Check the document status: qms --user {user} status {doc_id}
""")
        return 1

    # Get workflow state from .meta (authoritative source) - CR-012 fix
    doc_type = get_doc_type(doc_id)
    meta = read_meta(doc_id, doc_type) or {}
    current_status = Status(meta.get("status", "DRAFT"))
    version = meta.get("version", "0.1")
    pending_assignees = meta.get("pending_assignees", [])

    # Determine if we're in a review or approval workflow
    review_statuses = [Status.IN_REVIEW, Status.IN_PRE_REVIEW, Status.IN_POST_REVIEW]
    approval_statuses = [Status.IN_APPROVAL, Status.IN_PRE_APPROVAL, Status.IN_POST_APPROVAL]

    if current_status in review_statuses:
        workflow_name = "review"
        # Determine workflow type from status
        if current_status == Status.IN_PRE_REVIEW:
            workflow_type = "PRE_REVIEW"
        elif current_status == Status.IN_POST_REVIEW:
            workflow_type = "POST_REVIEW"
        else:
            workflow_type = "REVIEW"
    elif current_status in approval_statuses:
        workflow_name = "approval"
        if current_status == Status.IN_PRE_APPROVAL:
            workflow_type = "PRE_APPROVAL"
        elif current_status == Status.IN_POST_APPROVAL:
            workflow_type = "POST_APPROVAL"
        else:
            workflow_type = "APPROVAL"
    else:
        print(f"Error: {doc_id} is not in an active workflow (status: {current_status.value})")
        print("Can only assign users during IN_REVIEW or IN_APPROVAL states.")
        return 1

    # Add new assignees to pending_assignees in .meta
    added = []
    for new_user in new_assignees:
        if new_user in pending_assignees:
            print(f"Note: {new_user} is already assigned")
        else:
            pending_assignees.append(new_user)
            added.append(new_user)

            # Create task in new assignee's inbox (CR-012: Use enhanced task content)
            inbox_path = get_inbox_path(new_user)
            inbox_path.mkdir(parents=True, exist_ok=True)

            task_type = "REVIEW" if workflow_name == "review" else "APPROVAL"
            task_id = f"task-{doc_id}-{workflow_type.lower()}-v{version.replace('.', '-')}"
            task_path = inbox_path / f"{task_id}.md"

            # Generate enhanced task content
            if task_type == "REVIEW":
                task_content = generate_review_task_content(
                    doc_id=doc_id,
                    version=version,
                    workflow_type=workflow_type,
                    assignee=new_user,
                    assigned_by=user,
                    task_id=task_id
                )
            else:
                task_content = generate_approval_task_content(
                    doc_id=doc_id,
                    version=version,
                    workflow_type=workflow_type,
                    assignee=new_user,
                    assigned_by=user,
                    task_id=task_id
                )

            task_path.write_text(task_content, encoding="utf-8")

    if added:
        # Update .meta with new pending_assignees
        meta["pending_assignees"] = pending_assignees
        write_meta(doc_id, doc_type, meta)
        print(f"Assigned to {doc_id} ({workflow_name}): {', '.join(added)}")
    else:
        print("No new users assigned (all already in workflow)")

    return 0


def cmd_review(args):
    """Submit a review for a document."""
    doc_id = args.doc_id
    user = get_current_user(args)

    if not verify_user_identity(user):
        return 1

    # Permission check (group level - assigned check done later)
    allowed, error = check_permission(user, "review")
    if not allowed:
        print(error)
        return 1

    comment = args.comment

    if not comment:
        print(f"""
Error: Must provide --comment with review.

Usage:
  qms --user {user} review DOC-ID --recommend --comment "Your comments"
  qms --user {user} review DOC-ID --request-updates --comment "Changes needed"

The comment should explain your review findings and rationale.
""")
        return 1

    # Determine outcome
    if args.recommend:
        outcome = "RECOMMEND"
    elif args.request_updates:
        outcome = "UPDATES_REQUIRED"
    else:
        print(f"""
Error: Must specify review outcome.

Options:
  --recommend        Recommend the document for approval
  --request-updates  Request changes before approval

Usage:
  qms --user {user} review DOC-ID --recommend --comment "Approved. No issues found."
  qms --user {user} review DOC-ID --request-updates --comment "Section 3 needs clarification."
""")
        return 1

    draft_path = get_doc_path(doc_id, draft=True)
    if not draft_path.exists():
        print(f"""
Error: No draft found for {doc_id}.

Check your inbox for assigned review tasks: qms --user {user} inbox
Check document status: qms --user {user} status {doc_id}
""")
        return 1

    # Get workflow state from .meta (authoritative source)
    doc_type = get_doc_type(doc_id)
    meta = read_meta(doc_id, doc_type) or {}
    current_status = Status(meta.get("status", "DRAFT"))
    version = meta.get("version", "0.1")
    pending_assignees = meta.get("pending_assignees", [])

    # Verify document is in a review state
    review_statuses = [Status.IN_REVIEW, Status.IN_PRE_REVIEW, Status.IN_POST_REVIEW]
    if current_status not in review_statuses:
        print(f"""
Error: {doc_id} is not in review.

Current status: {current_status.value}

Documents can only be reviewed when in one of these states:
  - IN_REVIEW (non-executable documents)
  - IN_PRE_REVIEW (executable documents, before execution)
  - IN_POST_REVIEW (executable documents, after execution)

Check document status: qms --user {user} status {doc_id}
""")
        return 1

    # Check if user is assigned to review
    if user not in pending_assignees:
        print(f"""
Error: You ({user}) are not assigned to review {doc_id}.

Currently assigned reviewers: {', '.join(pending_assignees) if pending_assignees else 'None'}

You can only review documents you are assigned to.
Check your inbox for assigned tasks: qms --user {user} inbox

If you should be reviewing this document, ask QA to assign you:
  (QA) qms --user qa assign {doc_id} --assignees {user}
""")
        return 1

    # Log REVIEW event to audit trail (comments only live here now)
    log_review(doc_id, doc_type, user, version, outcome, comment)

    # Update .meta file - remove this user from pending assignees
    remaining_assignees = [u for u in pending_assignees if u != user]
    all_complete = len(remaining_assignees) == 0

    new_status = None
    if all_complete:
        # Transition to REVIEWED state
        status_map = {
            Status.IN_REVIEW: Status.REVIEWED,
            Status.IN_PRE_REVIEW: Status.PRE_REVIEWED,
            Status.IN_POST_REVIEW: Status.POST_REVIEWED,
        }
        new_status = status_map.get(current_status)
        if new_status:
            print(f"All reviews complete. Status: {current_status.value} -> {new_status.value}")
            # Log status change (CAPA-3: audit trail completeness)
            log_status_change(doc_id, doc_type, user, version, current_status.value, new_status.value)

    meta = update_meta_review_complete(
        meta, user, remaining_assignees,
        new_status=new_status.value if new_status else None
    )
    write_meta(doc_id, doc_type, meta)

    # Remove task from inbox
    inbox_path = get_inbox_path(user)
    for task_file in inbox_path.glob(f"task-{doc_id}-*.md"):
        task_file.unlink()

    print(f"Review submitted for {doc_id}")

    return 0


def cmd_approve(args):
    """Approve a document."""
    doc_id = args.doc_id
    user = get_current_user(args)

    if not verify_user_identity(user):
        return 1

    # Permission check (group level)
    allowed, error = check_permission(user, "approve")
    if not allowed:
        print(error)
        return 1

    draft_path = get_doc_path(doc_id, draft=True)
    if not draft_path.exists():
        print(f"""
Error: No draft found for {doc_id}.

Check your inbox for assigned approval tasks: qms --user {user} inbox
Check document status: qms --user {user} status {doc_id}
""")
        return 1

    # Get workflow state from .meta (authoritative source)
    doc_type = get_doc_type(doc_id)
    meta = read_meta(doc_id, doc_type) or {}
    current_status = Status(meta.get("status", "DRAFT"))
    current_version = meta.get("version", "0.1")
    is_executable = meta.get("executable", False)
    pending_assignees = meta.get("pending_assignees", [])

    # Verify document is in an approval state
    approval_statuses = [Status.IN_APPROVAL, Status.IN_PRE_APPROVAL, Status.IN_POST_APPROVAL]
    if current_status not in approval_statuses:
        print(f"""
Error: {doc_id} is not in approval.

Current status: {current_status.value}

Documents can only be approved when in one of these states:
  - IN_APPROVAL (non-executable documents)
  - IN_PRE_APPROVAL (executable documents, before execution)
  - IN_POST_APPROVAL (executable documents, after execution)

Check document status: qms --user {user} status {doc_id}
""")
        return 1

    # Check if user is assigned to approve
    if user not in pending_assignees:
        print(f"""
Error: You ({user}) are not assigned to approve {doc_id}.

Currently assigned approvers: {', '.join(pending_assignees) if pending_assignees else 'None'}

You can only approve documents you are assigned to.
Check your inbox for assigned tasks: qms --user {user} inbox
""")
        return 1

    # Log APPROVE event to audit trail
    log_approve(doc_id, doc_type, user, current_version)

    # Update .meta file - remove this user from pending assignees
    remaining_assignees = [u for u in pending_assignees if u != user]
    all_approved = len(remaining_assignees) == 0

    if all_approved:
        # Transition to APPROVED state and bump version
        status_map = {
            Status.IN_APPROVAL: Status.APPROVED,
            Status.IN_PRE_APPROVAL: Status.PRE_APPROVED,
            Status.IN_POST_APPROVAL: Status.POST_APPROVED,
        }
        new_status = status_map.get(current_status)

        if new_status:
            # Bump to major version
            major = int(str(current_version).split(".")[0])
            new_version = f"{major + 1}.0"

            # Archive current draft
            archive_path = get_archive_path(doc_id, current_version)
            archive_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy(draft_path, archive_path)

            print(f"All approvals complete. Status: {current_status.value} -> {new_status.value}")
            print(f"Version: {current_version} -> {new_version}")

            # Log status change (CAPA-3: audit trail completeness)
            log_status_change(doc_id, doc_type, user, new_version, current_status.value, new_status.value)

            # Check if this is a retirement approval
            is_retiring = meta.get("retiring", False)

            if is_retiring:
                # Retirement workflow: archive and set RETIRED status
                archive_path = get_archive_path(doc_id, new_version)
                archive_path.parent.mkdir(parents=True, exist_ok=True)

                # Read document and archive it
                frontmatter, body = read_document(draft_path)
                write_document_minimal(archive_path, frontmatter, body)
                print(f"Archived: {archive_path.relative_to(PROJECT_ROOT)}")

                # Delete working copy (draft)
                draft_path.unlink()

                # Also delete effective copy if it exists (for previously-effective docs being retired)
                effective_path = get_doc_path(doc_id, draft=False)
                if effective_path.exists():
                    effective_path.unlink()

                # Update meta - set RETIRED status, clear owner
                meta = update_meta_approval(meta, new_status=Status.RETIRED.value, new_version=new_version, clear_owner=True)
                meta.pop("retiring", None)  # Clear the retiring flag
                write_meta(doc_id, doc_type, meta)
                log_retire(doc_id, doc_type, user, current_version, new_version)
                # Log additional status change to RETIRED (CAPA-3)
                log_status_change(doc_id, doc_type, user, new_version, new_status.value, Status.RETIRED.value)
                print(f"Document is now RETIRED")
                # No metadata injection for RETIRED docs (files are deleted)

            elif new_status == Status.APPROVED:
                # Non-executable normal workflow: transition to EFFECTIVE
                frontmatter, body = read_document(draft_path)
                effective_path = get_doc_path(doc_id, draft=False)
                write_document_minimal(effective_path, frontmatter, body)
                draft_path.unlink()
                print(f"Document is now EFFECTIVE at {effective_path.relative_to(PROJECT_ROOT)}")

                # Update meta - clear owner for effective docs
                meta = update_meta_approval(meta, new_status=Status.EFFECTIVE.value, new_version=new_version, clear_owner=True)
                log_effective(doc_id, doc_type, user, current_version, new_version)
                # Log additional status change to EFFECTIVE (CAPA-3)
                log_status_change(doc_id, doc_type, user, new_version, new_status.value, Status.EFFECTIVE.value)

                write_meta(doc_id, doc_type, meta)
            else:
                # Executable document - stays as draft until closed
                meta = update_meta_approval(meta, new_status=new_status.value, new_version=new_version, clear_owner=False)
                write_meta(doc_id, doc_type, meta)
    else:
        # Still waiting for more approvals
        meta["pending_assignees"] = remaining_assignees
        write_meta(doc_id, doc_type, meta)

    # Remove task from inbox
    inbox_path = get_inbox_path(user)
    for task_file in inbox_path.glob(f"task-{doc_id}-*.md"):
        task_file.unlink()

    print(f"Approval submitted for {doc_id}")

    return 0


def cmd_reject(args):
    """Reject a document."""
    doc_id = args.doc_id
    user = get_current_user(args)

    if not verify_user_identity(user):
        return 1

    # Permission check (group level)
    allowed, error = check_permission(user, "reject")
    if not allowed:
        print(error)
        return 1

    comment = args.comment

    if not comment:
        print(f"""
Error: Must provide --comment with rejection.

Usage:
  qms --user {user} reject DOC-ID --comment "Reason for rejection"

The comment should explain why the document is being rejected
and what changes are needed before re-submission.
""")
        return 1

    draft_path = get_doc_path(doc_id, draft=True)
    if not draft_path.exists():
        print(f"""
Error: No draft found for {doc_id}.

Check your inbox for assigned approval tasks: qms --user {user} inbox
Check document status: qms --user {user} status {doc_id}
""")
        return 1

    # Get workflow state from .meta (authoritative source)
    doc_type = get_doc_type(doc_id)
    meta = read_meta(doc_id, doc_type) or {}
    current_status = Status(meta.get("status", "DRAFT"))
    version = meta.get("version", "0.1")
    pending_assignees = meta.get("pending_assignees", [])

    # Verify document is in an approval state
    approval_statuses = [Status.IN_APPROVAL, Status.IN_PRE_APPROVAL, Status.IN_POST_APPROVAL]
    if current_status not in approval_statuses:
        print(f"""
Error: {doc_id} is not in approval.

Current status: {current_status.value}

Documents can only be rejected when in an approval state.
Check document status: qms --user {user} status {doc_id}
""")
        return 1

    # Check if user is assigned to approve
    if user not in pending_assignees:
        print(f"Error: You are not assigned to approve {doc_id}")
        return 1

    # Log REJECT event to audit trail (comment goes here)
    log_reject(doc_id, doc_type, user, version, comment)

    # Transition back to REVIEWED state
    status_map = {
        Status.IN_APPROVAL: Status.REVIEWED,
        Status.IN_PRE_APPROVAL: Status.PRE_REVIEWED,
        Status.IN_POST_APPROVAL: Status.POST_REVIEWED,
    }
    new_status = status_map.get(current_status)

    if new_status:
        print(f"Document rejected. Status: {current_status.value} -> {new_status.value}")
        # Log status change (CAPA-3: audit trail completeness)
        log_status_change(doc_id, doc_type, user, version, current_status.value, new_status.value)

    # Update .meta file
    meta = update_meta_approval(meta, new_status=new_status.value if new_status else None)
    meta["pending_assignees"] = []  # Clear pending assignees on rejection
    write_meta(doc_id, doc_type, meta)

    # Remove all pending approval tasks for this document
    for user_dir in USERS_ROOT.iterdir():
        if user_dir.is_dir():
            inbox = user_dir / "inbox"
            if inbox.exists():
                for task_file in inbox.glob(f"task-{doc_id}-*approval*.md"):
                    task_file.unlink()

    print(f"Rejected: {doc_id}")
    print(f"Reason: {comment}")

    return 0


def cmd_release(args):
    """Release an executable document for execution."""
    doc_id = args.doc_id
    user = get_current_user(args)

    if not verify_user_identity(user):
        return 1

    # Permission check (group level)
    allowed, error = check_permission(user, "release")
    if not allowed:
        print(error)
        return 1

    draft_path = get_doc_path(doc_id, draft=True)
    if not draft_path.exists():
        print(f"""
Error: No draft found for {doc_id}.

Check document status: qms --user {user} status {doc_id}
""")
        return 1

    # Get workflow state from .meta (authoritative source)
    doc_type = get_doc_type(doc_id)
    meta = read_meta(doc_id, doc_type) or {}
    current_status = Status(meta.get("status", "DRAFT"))
    version = meta.get("version", "0.1")
    is_executable = meta.get("executable", False)

    if not is_executable:
        print(f"""
Error: {doc_id} is not an executable document.

Only executable documents (CR, INV, CAPA, TP, ER) can be released.
Non-executable documents (SOP, RS, DS, etc.) become EFFECTIVE after approval.
""")
        return 1

    # Check ownership
    doc_owner = meta.get("responsible_user")
    allowed, error = check_permission(user, "release", doc_owner=doc_owner)
    if not allowed:
        print(error)
        return 1

    if current_status != Status.PRE_APPROVED:
        print(f"""
Error: {doc_id} must be PRE_APPROVED to release.

Current status: {current_status.value}

Workflow for executable documents:
  DRAFT -> IN_PRE_REVIEW -> PRE_REVIEWED -> IN_PRE_APPROVAL -> PRE_APPROVED -> release -> IN_EXECUTION
""")
        return 1

    # Log RELEASE event to audit trail
    log_release(doc_id, doc_type, user, version)

    # Log status change (CAPA-3: audit trail completeness)
    log_status_change(doc_id, doc_type, user, version, Status.PRE_APPROVED.value, Status.IN_EXECUTION.value)

    # Update .meta file
    meta["status"] = Status.IN_EXECUTION.value
    # CAPA-4: Set execution_phase to post_release on release
    meta["execution_phase"] = "post_release"
    write_meta(doc_id, doc_type, meta)

    print(f"Released: {doc_id}")
    print(f"Status: PRE_APPROVED -> IN_EXECUTION")

    return 0


def cmd_revert(args):
    """Revert an executable document back to execution."""
    doc_id = args.doc_id
    user = get_current_user(args)

    if not verify_user_identity(user):
        return 1

    # Permission check (group level)
    allowed, error = check_permission(user, "revert")
    if not allowed:
        print(error)
        return 1

    reason = args.reason

    if not reason:
        print(f"""
Error: Must provide --reason for revert.

Usage:
  qms --user {user} revert DOC-ID --reason "Reason for reverting to execution"

The reason should explain why additional execution work is needed.
""")
        return 1

    draft_path = get_doc_path(doc_id, draft=True)
    if not draft_path.exists():
        print(f"""
Error: No draft found for {doc_id}.

Check document status: qms --user {user} status {doc_id}
""")
        return 1

    # Get workflow state from .meta (authoritative source)
    doc_type = get_doc_type(doc_id)
    meta = read_meta(doc_id, doc_type) or {}
    current_status = Status(meta.get("status", "DRAFT"))
    version = meta.get("version", "0.1")

    # Check ownership
    doc_owner = meta.get("responsible_user")
    allowed, error = check_permission(user, "revert", doc_owner=doc_owner)
    if not allowed:
        print(error)
        return 1

    if current_status != Status.POST_REVIEWED:
        print(f"""
Error: {doc_id} must be POST_REVIEWED to revert.

Current status: {current_status.value}

Revert moves a document from POST_REVIEWED back to IN_EXECUTION
when additional execution work is discovered during post-review.
""")
        return 1

    # Log REVERT event to audit trail
    log_revert(doc_id, doc_type, user, version, reason)

    # Update .meta file
    meta["status"] = Status.IN_EXECUTION.value
    write_meta(doc_id, doc_type, meta)

    print(f"Reverted: {doc_id}")
    print(f"Status: POST_REVIEWED -> IN_EXECUTION")
    print(f"Reason: {reason}")

    return 0


def cmd_close(args):
    """Close an executable document."""
    doc_id = args.doc_id
    user = get_current_user(args)

    if not verify_user_identity(user):
        return 1

    # Permission check (group level)
    allowed, error = check_permission(user, "close")
    if not allowed:
        print(error)
        return 1

    draft_path = get_doc_path(doc_id, draft=True)
    if not draft_path.exists():
        print(f"""
Error: No draft found for {doc_id}.

Check document status: qms --user {user} status {doc_id}
""")
        return 1

    # Get workflow state from .meta (authoritative source)
    doc_type = get_doc_type(doc_id)
    meta = read_meta(doc_id, doc_type) or {}
    current_status = Status(meta.get("status", "DRAFT"))
    version = meta.get("version", "0.1")
    is_executable = meta.get("executable", False)

    if not is_executable:
        print(f"""
Error: {doc_id} is not an executable document.

Only executable documents (CR, INV, CAPA, TP, ER) can be closed.
Non-executable documents (SOP, RS, DS, etc.) become EFFECTIVE after approval.
""")
        return 1

    # Check ownership
    doc_owner = meta.get("responsible_user")
    allowed, error = check_permission(user, "close", doc_owner=doc_owner)
    if not allowed:
        print(error)
        return 1

    if current_status != Status.POST_APPROVED:
        print(f"""
Error: {doc_id} must be POST_APPROVED to close.

Current status: {current_status.value}

Workflow for executable documents:
  ... -> IN_POST_REVIEW -> POST_REVIEWED -> IN_POST_APPROVAL -> POST_APPROVED -> close -> CLOSED
""")
        return 1

    # Move to effective location with minimal frontmatter
    frontmatter, body = read_document(draft_path)
    effective_path = get_doc_path(doc_id, draft=False)
    write_document_minimal(effective_path, frontmatter, body)
    draft_path.unlink()

    # Log CLOSE event to audit trail
    log_close(doc_id, doc_type, user, version)

    # Log status change (CAPA-3: audit trail completeness)
    log_status_change(doc_id, doc_type, user, version, current_status.value, Status.CLOSED.value)

    # Update .meta file (clear ownership on close)
    meta["status"] = Status.CLOSED.value
    meta["responsible_user"] = None
    meta["checked_out"] = False
    meta["checked_out_date"] = None
    meta["pending_assignees"] = []
    write_meta(doc_id, doc_type, meta)

    # Remove from workspace
    workspace_path = get_workspace_path(user, doc_id)
    if workspace_path.exists():
        workspace_path.unlink()

    print(f"Closed: {doc_id}")
    print(f"Location: {effective_path.relative_to(PROJECT_ROOT)}")

    return 0


def cmd_status(args):
    """Show document status."""
    doc_id = args.doc_id

    # Try draft first, then effective
    draft_path = get_doc_path(doc_id, draft=True)
    effective_path = get_doc_path(doc_id, draft=False)

    if draft_path.exists():
        path = draft_path
        location = "draft"
    elif effective_path.exists():
        path = effective_path
        location = "effective"
    else:
        print(f"Error: Document not found: {doc_id}")
        return 1

    # Read title from document frontmatter
    frontmatter, _ = read_document(path)

    # Get workflow state from .meta (authoritative source)
    doc_type = get_doc_type(doc_id)
    meta = read_meta(doc_id, doc_type) or {}

    print(f"Document: {doc_id}")
    print(f"Title: {frontmatter.get('title', 'N/A')}")
    print(f"Version: {meta.get('version', 'N/A')}")
    print(f"Status: {meta.get('status', 'N/A')}")
    print(f"Location: {location}")
    print(f"Type: {doc_type}")
    print(f"Executable: {meta.get('executable', False)}")
    print(f"Responsible User: {meta.get('responsible_user') or 'N/A'}")
    print(f"Checked Out: {meta.get('checked_out', False)}")

    if meta.get("effective_version"):
        print(f"Effective Version: {meta.get('effective_version')}")

    # Show pending assignees from .meta
    pending_assignees = meta.get("pending_assignees", [])
    if pending_assignees:
        status = meta.get("status", "")
        if "REVIEW" in status:
            print(f"\nPending Reviewers: {', '.join(pending_assignees)}")
        elif "APPROVAL" in status:
            print(f"\nPending Approvers: {', '.join(pending_assignees)}")

    return 0


def cmd_inbox(args):
    """List tasks in current user's inbox."""
    user = get_current_user(args)

    if not verify_user_identity(user):
        return 1

    inbox_path = get_inbox_path(user)

    if not inbox_path.exists():
        print(f"Inbox is empty")
        return 0

    tasks = list(inbox_path.glob("*.md"))
    if not tasks:
        print(f"Inbox is empty")
        return 0

    print(f"Inbox for {user}:")
    print("-" * 60)

    for task_path in sorted(tasks):
        frontmatter, _ = read_document(task_path)
        print(f"  [{frontmatter.get('task_type', '?')}] {frontmatter.get('doc_id', '?')}")
        print(f"    Workflow: {frontmatter.get('workflow_type', '?')}")
        print(f"    From: {frontmatter.get('assigned_by', '?')}")
        print(f"    Date: {frontmatter.get('assigned_date', '?')}")
        print()

    return 0


def cmd_workspace(args):
    """List documents in current user's workspace."""
    user = get_current_user(args)

    if not verify_user_identity(user):
        return 1

    workspace_path = USERS_ROOT / user / "workspace"

    if not workspace_path.exists():
        print(f"Workspace is empty")
        return 0

    docs = list(workspace_path.glob("*.md"))
    if not docs:
        print(f"Workspace is empty")
        return 0

    print(f"Workspace for {user}:")
    print("-" * 60)

    for doc_path in sorted(docs):
        frontmatter, _ = read_document(doc_path)
        print(f"  {frontmatter.get('doc_id', doc_path.stem)}")
        print(f"    Version: {frontmatter.get('version', '?')}")
        print(f"    Status: {frontmatter.get('status', '?')}")
        print()

    return 0


def cmd_fix(args) -> int:
    """Administrative fix for EFFECTIVE documents (QA/lead only)."""
    current_user = get_current_user(args)

    if current_user not in {"qa", "lead"}:
        print("Error: Only QA or lead can run administrative fixes.", file=sys.stderr)
        return 1

    doc_id = args.doc_id
    doc_path = get_doc_path(doc_id, draft=False)

    if not doc_path.exists():
        print(f"Error: Document not found: {doc_id}", file=sys.stderr)
        return 1

    frontmatter, body = read_document(doc_path)
    status = frontmatter.get("status", "")

    if status not in ("EFFECTIVE", "CLOSED"):
        print(f"Error: Fix only applies to EFFECTIVE/CLOSED documents (current: {status})", file=sys.stderr)
        return 1

    changes = []

    # Fix 1: Clear checked_out if set
    if frontmatter.get("checked_out"):
        frontmatter["checked_out"] = False
        frontmatter.pop("checked_out_date", None)
        changes.append("cleared checked_out flag")

    # Fix 2: Sync body version header with frontmatter
    version = frontmatter.get("version", "1.0")
    old_version_pattern = r"\*\*Version:\*\* [^\n]+"
    new_version_line = f"**Version:** {version}"
    if re.search(old_version_pattern, body):
        new_body = re.sub(old_version_pattern, new_version_line, body, count=1)
        if new_body != body:
            body = new_body
            changes.append(f"updated body version to {version}")

    # Fix 3: Update Effective Date if TBD
    if status == "EFFECTIVE":
        old_date_pattern = r"\*\*Effective Date:\*\* TBD"
        today = datetime.now().strftime("%Y-%m-%d")
        new_date_line = f"**Effective Date:** {today}"
        if re.search(old_date_pattern, body):
            body = re.sub(old_date_pattern, new_date_line, body, count=1)
            changes.append(f"set effective date to {today}")

    if not changes:
        print(f"No fixes needed for {doc_id}")
        return 0

    write_document(doc_path, frontmatter, body)
    print(f"Fixed {doc_id}:")
    for change in changes:
        print(f"  - {change}")

    return 0


def cmd_cancel(args) -> int:
    """Cancel a never-effective document (version < 1.0)."""
    user = get_current_user(args)

    # Only initiators can cancel
    if user not in USER_GROUPS["initiators"]:
        print("Error: Only initiators can cancel documents.", file=sys.stderr)
        return 1

    doc_id = args.doc_id
    doc_type = get_doc_type(doc_id)

    # Get document metadata
    meta = read_meta(doc_id, doc_type)
    if meta is None:
        print(f"Error: Document {doc_id} not found.", file=sys.stderr)
        return 1

    # Check version < 1.0 (never effective)
    version = meta.get("version", "0.1")
    major = int(version.split(".")[0])
    if major >= 1:
        print(f"Error: Cannot cancel {doc_id} - it was effective (v{version}).", file=sys.stderr)
        print("Use the retire workflow instead (checkout, edit, route --approval --retire).")
        return 1

    # Check not checked out by someone else
    if meta.get("checked_out"):
        responsible = meta.get("responsible_user", "unknown")
        print(f"Error: {doc_id} is checked out by {responsible}.", file=sys.stderr)
        print("Document must be checked in before canceling.")
        return 1

    # Require --confirm
    if not args.confirm:
        print(f"This will permanently delete {doc_id} (v{version}) and free the doc ID.")
        print("The following will be deleted:")
        print(f"  - Document file(s)")
        print(f"  - Metadata (.meta/{doc_type}/{doc_id}.json)")
        print(f"  - Audit trail (.audit/{doc_type}/{doc_id}.jsonl)")
        print()
        print("Run with --confirm to proceed.")
        return 1

    # Delete document file(s)
    draft_path = get_doc_path(doc_id, draft=True)
    effective_path = get_doc_path(doc_id, draft=False)

    deleted_files = []
    if draft_path.exists():
        draft_path.unlink()
        deleted_files.append(str(draft_path.relative_to(PROJECT_ROOT)))

    if effective_path.exists():
        effective_path.unlink()
        deleted_files.append(str(effective_path.relative_to(PROJECT_ROOT)))

    # For CR documents, also try to remove the directory if empty
    if doc_type == "CR":
        cr_dir = QMS_ROOT / "CR" / doc_id
        if cr_dir.exists() and not any(cr_dir.iterdir()):
            cr_dir.rmdir()
            deleted_files.append(str(cr_dir.relative_to(PROJECT_ROOT)))

    # Delete .meta file
    meta_path = get_meta_path(doc_id, doc_type)
    if meta_path.exists():
        meta_path.unlink()
        deleted_files.append(str(meta_path.relative_to(PROJECT_ROOT)))

    # Delete .audit file
    audit_dir = QMS_ROOT / ".audit" / doc_type
    audit_path = audit_dir / f"{doc_id}.jsonl"
    if audit_path.exists():
        audit_path.unlink()
        deleted_files.append(str(audit_path.relative_to(PROJECT_ROOT)))

    # Also clean up any workspace copies
    for username in ["lead", "claude", "qa"]:
        workspace_path = Path(f".claude/users/{username}/workspace/{doc_id}.md")
        full_workspace_path = PROJECT_ROOT / workspace_path
        if full_workspace_path.exists():
            full_workspace_path.unlink()
            deleted_files.append(str(workspace_path))

    # Clean up inbox tasks
    for username in os.listdir(PROJECT_ROOT / ".claude" / "users"):
        inbox_dir = PROJECT_ROOT / ".claude" / "users" / username / "inbox"
        if inbox_dir.exists():
            for task_file in inbox_dir.glob(f"task-{doc_id}-*.md"):
                task_file.unlink()
                deleted_files.append(str(task_file.relative_to(PROJECT_ROOT)))

    print(f"Canceled: {doc_id}")
    print("Deleted:")
    for f in deleted_files:
        print(f"  - {f}")

    return 0


# =============================================================================
# New Audit/History Commands
# =============================================================================

def cmd_history(args):
    """Show full audit history for a document."""
    user = get_current_user(args)

    if not verify_user_identity(user):
        return 1

    doc_id = args.doc_id
    doc_type = get_doc_type(doc_id)

    # Read audit log
    events = read_audit_log(doc_id, doc_type)

    if not events:
        # Check if document exists but has no audit log (pre-migration)
        draft_path = get_doc_path(doc_id, draft=True)
        effective_path = get_doc_path(doc_id, draft=False)
        if draft_path.exists() or effective_path.exists():
            print(f"Document {doc_id} exists but has no audit log.")
            print("Run 'qms migrate' to generate audit logs from frontmatter history.")
        else:
            print(f"Document not found: {doc_id}")
        return 1

    print(f"Audit History: {doc_id}")
    print("=" * 70)
    print(format_audit_history(events))

    return 0


def cmd_comments(args):
    """Show review/approval comments for a document."""
    user = get_current_user(args)

    if not verify_user_identity(user):
        return 1

    doc_id = args.doc_id
    doc_type = get_doc_type(doc_id)

    # Get document status to enforce visibility rules
    draft_path = get_doc_path(doc_id, draft=True)
    effective_path = get_doc_path(doc_id, draft=False)

    if draft_path.exists():
        frontmatter, _ = read_document(draft_path)
    elif effective_path.exists():
        frontmatter, _ = read_document(effective_path)
    else:
        print(f"Document not found: {doc_id}")
        return 1

    status = frontmatter.get("status", "")
    version = frontmatter.get("version", "")

    # Enforce visibility rule: comments only visible after REVIEWED state
    review_states = {"IN_REVIEW", "IN_PRE_REVIEW", "IN_POST_REVIEW"}
    if status in review_states:
        print(f"Comments are not visible while document is in {status}.")
        print("Comments become visible after review phase completes.")
        return 1

    # Get comments
    if args.version:
        comments = get_comments(doc_id, doc_type, version=args.version)
        print(f"Comments for {doc_id} v{args.version}:")
    else:
        comments = get_latest_version_comments(doc_id, doc_type, version)
        print(f"Comments for {doc_id} (current version {version}):")

    print("=" * 70)

    if not comments:
        print("No comments found.")
        # Check if there's frontmatter history (pre-migration)
        if frontmatter.get("review_history") or frontmatter.get("approval_history"):
            print("\nNote: This document has legacy frontmatter comments.")
            print("Run 'qms migrate' to convert them to the new audit system.")
    else:
        print(format_comments(comments))

    return 0


def cmd_migrate(args):
    """Migrate existing documents to new metadata architecture."""
    user = get_current_user(args)

    if not verify_user_identity(user):
        return 1

    # Only lead can run migration
    if user != "lead":
        print("Error: Only 'lead' can run document migration.")
        return 1

    dry_run = args.dry_run if hasattr(args, 'dry_run') else False

    if dry_run:
        print("DRY RUN - No changes will be made")
        print("=" * 70)

    # Find all documents
    migrated = 0
    skipped = 0
    errors = 0

    for doc_type, config in DOCUMENT_TYPES.items():
        doc_path = QMS_ROOT / config["path"]
        if not doc_path.exists():
            continue

        # Find all markdown files
        for md_file in doc_path.rglob("*.md"):
            # Skip archive
            if ".archive" in str(md_file):
                continue

            try:
                frontmatter, body = read_document(md_file)
                doc_id = frontmatter.get("doc_id")

                if not doc_id:
                    continue

                # Check if already migrated (has .meta file)
                actual_type = get_doc_type(doc_id)
                meta_path = get_meta_path(doc_id, actual_type)

                if meta_path.exists() and not args.force:
                    skipped += 1
                    continue

                print(f"Migrating: {doc_id}")

                if not dry_run:
                    # Create .meta file
                    meta = create_initial_meta(
                        doc_id=doc_id,
                        doc_type=frontmatter.get("document_type", actual_type),
                        version=frontmatter.get("version", "0.1"),
                        status=frontmatter.get("status", "DRAFT"),
                        executable=frontmatter.get("executable", False),
                        responsible_user=frontmatter.get("responsible_user")
                    )
                    meta["checked_out"] = frontmatter.get("checked_out", False)
                    meta["checked_out_date"] = frontmatter.get("checked_out_date")
                    meta["effective_version"] = frontmatter.get("effective_version")
                    meta["supersedes"] = frontmatter.get("supersedes")

                    write_meta(doc_id, actual_type, meta)

                    # Convert review_history to audit events
                    for review in frontmatter.get("review_history", []):
                        review_type = review.get("type", "REVIEW")
                        version = frontmatter.get("version", "0.1")

                        # Log routing event
                        assignees = [a.get("user") for a in review.get("assignees", [])]
                        log_route_review(doc_id, actual_type, "system", version, assignees, review_type)

                        # Log individual reviews
                        for assignee in review.get("assignees", []):
                            if assignee.get("status") == "COMPLETE":
                                outcome = assignee.get("outcome", "RECOMMEND")
                                comment = assignee.get("comments", "")
                                log_review(doc_id, actual_type, assignee.get("user"), version, outcome, comment)

                    # Convert approval_history to audit events
                    for approval in frontmatter.get("approval_history", []):
                        approval_type = approval.get("type", "APPROVAL")
                        version = frontmatter.get("version", "0.1")

                        # Log routing event
                        assignees = [a.get("user") for a in approval.get("assignees", [])]
                        log_route_approval(doc_id, actual_type, "system", version, assignees, approval_type)

                        # Log individual approvals/rejections
                        for assignee in approval.get("assignees", []):
                            if assignee.get("status") == "APPROVED":
                                log_approve(doc_id, actual_type, assignee.get("user"), version)
                            elif assignee.get("status") == "REJECTED":
                                comment = assignee.get("comments", "")
                                log_reject(doc_id, actual_type, assignee.get("user"), version, comment)

                migrated += 1

            except Exception as e:
                print(f"  Error: {e}")
                errors += 1

    print()
    print("=" * 70)
    print(f"Migration complete:")
    print(f"  Migrated: {migrated}")
    print(f"  Skipped (already migrated): {skipped}")
    print(f"  Errors: {errors}")

    if dry_run:
        print("\nThis was a dry run. Run without --dry-run to apply changes.")

    return 0 if errors == 0 else 1


def cmd_verify_migration(args):
    """Verify migration completed successfully."""
    user = get_current_user(args)

    if not verify_user_identity(user):
        return 1

    print("Verifying migration...")
    print("=" * 70)

    issues = []

    for doc_type, config in DOCUMENT_TYPES.items():
        doc_path = QMS_ROOT / config["path"]
        if not doc_path.exists():
            continue

        for md_file in doc_path.rglob("*.md"):
            if ".archive" in str(md_file):
                continue

            try:
                frontmatter, _ = read_document(md_file)
                doc_id = frontmatter.get("doc_id")

                if not doc_id:
                    continue

                actual_type = get_doc_type(doc_id)
                meta_path = get_meta_path(doc_id, actual_type)

                if not meta_path.exists():
                    issues.append(f"{doc_id}: Missing .meta file")
                else:
                    # Verify meta matches frontmatter
                    meta = read_meta(doc_id, actual_type)
                    if meta:
                        if meta.get("version") != frontmatter.get("version"):
                            issues.append(f"{doc_id}: Version mismatch (meta={meta.get('version')}, fm={frontmatter.get('version')})")
                        if meta.get("status") != frontmatter.get("status"):
                            issues.append(f"{doc_id}: Status mismatch (meta={meta.get('status')}, fm={frontmatter.get('status')})")

            except Exception as e:
                issues.append(f"{md_file}: Error - {e}")

    if issues:
        print("Issues found:")
        for issue in issues:
            print(f"  - {issue}")
        return 1
    else:
        print("All documents verified successfully.")
        return 0


# =============================================================================
# Main
# =============================================================================

def main():
    parser = argparse.ArgumentParser(
        description="QMS - Quality Management System CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  qms --user claude create SOP --title "New Procedure"
  qms --user claude checkout SOP-001
  qms --user claude route SOP-001 --review
  qms --user qa review SOP-001 --recommend --comment "Looks good"
  qms --user qa approve SOP-001
  qms --user claude status SOP-001
  qms --user qa inbox
  qms --user claude workspace

Valid users:
  Initiators: lead, claude
  QA:         qa
  Reviewers:  tu_ui, tu_scene, tu_sketch, tu_sim, bu
        """
    )

    # Global --user argument (required for most commands)
    parser.add_argument("--user", "-u", required=True,
                        help="Your QMS identity (required)")

    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    # create
    p_create = subparsers.add_parser("create", help="Create a new document")
    p_create.add_argument("type", help="Document type (SOP, CR, INV, RS, DS, etc.)")
    p_create.add_argument("--title", help="Document title")

    # read
    p_read = subparsers.add_parser("read", help="Read a document")
    p_read.add_argument("doc_id", help="Document ID")
    p_read.add_argument("--draft", action="store_true", help="Read draft version")
    p_read.add_argument("--version", help="Read specific version (e.g., 1.0)")

    # checkout
    p_checkout = subparsers.add_parser("checkout", help="Check out a document")
    p_checkout.add_argument("doc_id", help="Document ID")

    # checkin
    p_checkin = subparsers.add_parser("checkin", help="Check in a document")
    p_checkin.add_argument("doc_id", help="Document ID")

    # route
    p_route = subparsers.add_parser("route", help="Route document for review/approval")
    p_route.add_argument("doc_id", help="Document ID")
    p_route.add_argument("--review", action="store_true", help="Route for review (pre/post inferred from status)")
    p_route.add_argument("--approval", action="store_true", help="Route for approval (pre/post inferred from status)")
    p_route.add_argument("--assign", nargs="+", help="Users to assign (optional, defaults to QA)")
    p_route.add_argument("--retire", action="store_true", help="Retirement approval (leads to RETIRED instead of EFFECTIVE/CLOSED)")

    # assign
    p_assign = subparsers.add_parser("assign", help="Add reviewers/approvers to active workflow (QA only)")
    p_assign.add_argument("doc_id", help="Document ID")
    p_assign.add_argument("--assignees", nargs="+", required=True, help="Users to add to workflow")

    # review
    p_review = subparsers.add_parser("review", help="Submit a review")
    p_review.add_argument("doc_id", help="Document ID")
    p_review.add_argument("--comment", required=True, help="Review comments")
    review_outcome = p_review.add_mutually_exclusive_group(required=True)
    review_outcome.add_argument("--recommend", action="store_true", help="Recommend for approval")
    review_outcome.add_argument("--request-updates", action="store_true", help="Request updates before approval")

    # approve
    p_approve = subparsers.add_parser("approve", help="Approve a document")
    p_approve.add_argument("doc_id", help="Document ID")

    # reject
    p_reject = subparsers.add_parser("reject", help="Reject a document")
    p_reject.add_argument("doc_id", help="Document ID")
    p_reject.add_argument("--comment", required=True, help="Rejection reason")

    # release
    p_release = subparsers.add_parser("release", help="Release for execution")
    p_release.add_argument("doc_id", help="Document ID")

    # revert
    p_revert = subparsers.add_parser("revert", help="Revert to execution")
    p_revert.add_argument("doc_id", help="Document ID")
    p_revert.add_argument("--reason", required=True, help="Revert reason")

    # close
    p_close = subparsers.add_parser("close", help="Close a document")
    p_close.add_argument("doc_id", help="Document ID")

    # status
    p_status = subparsers.add_parser("status", help="Show document status")
    p_status.add_argument("doc_id", help="Document ID")

    # inbox
    p_inbox = subparsers.add_parser("inbox", help="List inbox tasks")

    # workspace
    p_workspace = subparsers.add_parser("workspace", help="List workspace documents")

    # fix (admin)
    p_fix = subparsers.add_parser("fix", help="Administrative fix for EFFECTIVE documents (QA/lead only)")
    p_fix.add_argument("doc_id", help="Document ID to fix")

    # cancel (delete never-effective document)
    p_cancel = subparsers.add_parser("cancel", help="Cancel a never-effective document (version < 1.0)")
    p_cancel.add_argument("doc_id", help="Document ID to cancel")
    p_cancel.add_argument("--confirm", action="store_true", help="Confirm permanent deletion")

    # history (audit trail)
    p_history = subparsers.add_parser("history", help="Show full audit history for a document")
    p_history.add_argument("doc_id", help="Document ID")

    # comments
    p_comments = subparsers.add_parser("comments", help="Show review/approval comments")
    p_comments.add_argument("doc_id", help="Document ID")
    p_comments.add_argument("--version", help="Show comments for specific version (e.g., 1.1)")

    # migrate
    p_migrate = subparsers.add_parser("migrate", help="Migrate documents to new metadata architecture (lead only)")
    p_migrate.add_argument("--dry-run", action="store_true", help="Show what would be migrated without making changes")
    p_migrate.add_argument("--force", action="store_true", help="Re-migrate documents that already have .meta files")

    # verify-migration
    p_verify = subparsers.add_parser("verify-migration", help="Verify migration completed successfully")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 1

    commands = {
        "create": cmd_create,
        "read": cmd_read,
        "checkout": cmd_checkout,
        "checkin": cmd_checkin,
        "route": cmd_route,
        "assign": cmd_assign,
        "review": cmd_review,
        "approve": cmd_approve,
        "reject": cmd_reject,
        "release": cmd_release,
        "revert": cmd_revert,
        "close": cmd_close,
        "status": cmd_status,
        "inbox": cmd_inbox,
        "workspace": cmd_workspace,
        "fix": cmd_fix,
        "cancel": cmd_cancel,
        "history": cmd_history,
        "comments": cmd_comments,
        "migrate": cmd_migrate,
        "verify-migration": cmd_verify_migration,
    }

    return commands[args.command](args)


if __name__ == "__main__":
    sys.exit(main())
