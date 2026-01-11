"""
QMS CLI Template Module

Contains functions for template loading, task content generation,
and document scaffolding.
"""
import re
from datetime import datetime
from typing import Dict, Any, Tuple

import yaml

from qms_paths import QMS_ROOT


# =============================================================================
# Date Helper
# =============================================================================

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
