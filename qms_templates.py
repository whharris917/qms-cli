"""
QMS CLI Template Module

Contains functions for template loading, task content generation,
and document scaffolding.

Note: Task content generation now delegates to the PromptRegistry
for configurable prompts per doc_type and workflow_type.
"""
import re
from datetime import datetime
from typing import Dict, Any, Tuple

import yaml

from qms_paths import QMS_ROOT
from prompts import get_prompt_registry


# =============================================================================
# Date Helper
# =============================================================================

def today() -> str:
    """Get today's date as YYYY-MM-DD."""
    return datetime.now().strftime("%Y-%m-%d")


# =============================================================================
# Review Task Content Generation (CR-012: QA Review Safeguards)
# Now uses PromptRegistry for configurable prompts (CR-026)
# =============================================================================

def generate_review_task_content(
    doc_id: str,
    version: str,
    workflow_type: str,
    assignee: str,
    assigned_by: str,
    task_id: str,
    doc_type: str = ""
) -> str:
    """
    Generate enhanced review task content with mandatory checklist.

    Args:
        doc_id: Document ID (e.g., "CR-026")
        version: Document version
        workflow_type: Workflow type (e.g., "PRE_REVIEW", "POST_REVIEW")
        assignee: User assigned to review
        assigned_by: User who assigned the review
        task_id: Task identifier
        doc_type: Document type for prompt customization (CR-026)

    Returns:
        Formatted task content string
    """
    registry = get_prompt_registry()
    return registry.generate_review_content(
        doc_id=doc_id,
        version=version,
        workflow_type=workflow_type,
        assignee=assignee,
        assigned_by=assigned_by,
        task_id=task_id,
        doc_type=doc_type
    )


def generate_approval_task_content(
    doc_id: str,
    version: str,
    workflow_type: str,
    assignee: str,
    assigned_by: str,
    task_id: str,
    doc_type: str = ""
) -> str:
    """
    Generate enhanced approval task content with final verification.

    Args:
        doc_id: Document ID (e.g., "CR-026")
        version: Document version
        workflow_type: Workflow type (e.g., "PRE_APPROVAL", "POST_APPROVAL")
        assignee: User assigned to approve
        assigned_by: User who assigned the approval
        task_id: Task identifier
        doc_type: Document type for prompt customization (CR-026)

    Returns:
        Formatted task content string
    """
    registry = get_prompt_registry()
    return registry.generate_approval_content(
        doc_id=doc_id,
        version=version,
        workflow_type=workflow_type,
        assignee=assignee,
        assigned_by=assigned_by,
        task_id=task_id,
        doc_type=doc_type
    )


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
