"""
QMS Prompt Registry

Configurable prompt generation for review and approval tasks.
Allows customization per document type and workflow phase.

Created as part of CR-026: QMS CLI Extensibility Refactoring
"""
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List, Dict, Tuple, Callable


def today() -> str:
    """Get today's date as YYYY-MM-DD."""
    return datetime.now().strftime("%Y-%m-%d")


@dataclass
class ChecklistItem:
    """A single checklist item for verification."""
    category: str
    item: str
    evidence_prompt: str = ""


@dataclass
class PromptConfig:
    """
    Configuration for generating task prompts.

    Attributes:
        checklist_items: Items for the verification checklist
        critical_reminders: Key reminders to emphasize
        additional_sections: Extra sections to include
        response_format: Format template for responses
        custom_header: Custom header text (replaces default)
        custom_footer: Custom footer text (replaces default)
    """
    checklist_items: List[ChecklistItem] = field(default_factory=list)
    critical_reminders: List[str] = field(default_factory=list)
    additional_sections: List[Tuple[str, str]] = field(default_factory=list)  # (title, content)
    response_format: Optional[str] = None
    custom_header: Optional[str] = None
    custom_footer: Optional[str] = None


# =============================================================================
# Default Checklist Items
# =============================================================================

DEFAULT_FRONTMATTER_CHECKS = [
    ChecklistItem(
        category="Frontmatter",
        item="`title:` field present and non-empty",
        evidence_prompt="quote actual value"
    ),
    ChecklistItem(
        category="Frontmatter",
        item="`revision_summary:` present (required for v1.0+)",
        evidence_prompt="quote actual value or N/A"
    ),
    ChecklistItem(
        category="Frontmatter",
        item="`revision_summary:` begins with CR ID (e.g., \"CR-XXX:\")",
        evidence_prompt="quote CR ID or N/A"
    ),
]

DEFAULT_STRUCTURE_CHECKS = [
    ChecklistItem(
        category="Document Structure",
        item="Document follows type-specific template",
        evidence_prompt=""
    ),
    ChecklistItem(
        category="Document Structure",
        item="All required sections present",
        evidence_prompt=""
    ),
    ChecklistItem(
        category="Document Structure",
        item="Section numbering sequential and correct",
        evidence_prompt=""
    ),
]

DEFAULT_CONTENT_CHECKS = [
    ChecklistItem(
        category="Content Integrity",
        item="No placeholder text (TBD, TODO, XXX, FIXME)",
        evidence_prompt=""
    ),
    ChecklistItem(
        category="Content Integrity",
        item="No obvious factual errors or contradictions",
        evidence_prompt=""
    ),
    ChecklistItem(
        category="Content Integrity",
        item="References to other documents are valid",
        evidence_prompt=""
    ),
    ChecklistItem(
        category="Content Integrity",
        item="No typos or grammatical errors",
        evidence_prompt=""
    ),
    ChecklistItem(
        category="Content Integrity",
        item="Formatting consistent throughout",
        evidence_prompt=""
    ),
]

# CR-specific checks for executable documents
CR_EXECUTION_CHECKS = [
    ChecklistItem(
        category="Execution Compliance",
        item="All execution items (EIs) have Pass/Fail outcomes",
        evidence_prompt=""
    ),
    ChecklistItem(
        category="Execution Compliance",
        item="Execution summaries describe what was done",
        evidence_prompt=""
    ),
    ChecklistItem(
        category="Execution Compliance",
        item="All EIs have performer and date",
        evidence_prompt=""
    ),
    ChecklistItem(
        category="Execution Compliance",
        item="VARs attached for any failed EIs",
        evidence_prompt=""
    ),
]

# SOP-specific checks
SOP_CHECKS = [
    ChecklistItem(
        category="Procedure Content",
        item="Responsibilities section defines all roles",
        evidence_prompt=""
    ),
    ChecklistItem(
        category="Procedure Content",
        item="Procedure steps are numbered and unambiguous",
        evidence_prompt=""
    ),
    ChecklistItem(
        category="Procedure Content",
        item="References section lists all dependencies",
        evidence_prompt=""
    ),
]

DEFAULT_CRITICAL_REMINDERS = [
    "**Compliance is BINARY**: Document is either compliant or non-compliant",
    "**ONE FAILED ITEM = REJECT**: No exceptions, no \"minor issues\"",
    "**VERIFY WITH EVIDENCE**: Quote actual values, do not assume",
    "**REJECTION IS CORRECT**: A rejected document prevents nonconformance",
]

APPROVAL_CRITICAL_REMINDERS = [
    "An incorrectly approved document creates **nonconformance**",
    "A rejected document creates a **correction cycle** (much lower cost)",
    "**Rejection is always the safer choice**",
    "You are the final gatekeeper - if you miss something, it becomes effective",
]


# =============================================================================
# Default Configurations
# =============================================================================

DEFAULT_REVIEW_CONFIG = PromptConfig(
    checklist_items=DEFAULT_FRONTMATTER_CHECKS + DEFAULT_STRUCTURE_CHECKS + DEFAULT_CONTENT_CHECKS,
    critical_reminders=DEFAULT_CRITICAL_REMINDERS,
)

DEFAULT_APPROVAL_CONFIG = PromptConfig(
    checklist_items=[
        ChecklistItem("Pre-Approval", "Frontmatter complete (title, revision_summary with CR ID if v1.0+)", ""),
        ChecklistItem("Pre-Approval", "All review findings from previous cycle addressed", ""),
        ChecklistItem("Pre-Approval", "No new deficiencies introduced since review", ""),
        ChecklistItem("Pre-Approval", "Document is 100% compliant with all requirements", ""),
    ],
    critical_reminders=APPROVAL_CRITICAL_REMINDERS,
)

# CR post-review configuration (includes execution checks)
CR_POST_REVIEW_CONFIG = PromptConfig(
    checklist_items=DEFAULT_FRONTMATTER_CHECKS + DEFAULT_STRUCTURE_CHECKS + DEFAULT_CONTENT_CHECKS + CR_EXECUTION_CHECKS,
    critical_reminders=DEFAULT_CRITICAL_REMINDERS + [
        "**EXECUTION VERIFICATION IS CRITICAL**: All EIs must have outcomes",
        "Missing EI data = incomplete execution = REJECT",
    ],
)

# SOP review configuration
SOP_REVIEW_CONFIG = PromptConfig(
    checklist_items=DEFAULT_FRONTMATTER_CHECKS + DEFAULT_STRUCTURE_CHECKS + DEFAULT_CONTENT_CHECKS + SOP_CHECKS,
    critical_reminders=DEFAULT_CRITICAL_REMINDERS,
)


# =============================================================================
# Prompt Registry
# =============================================================================

class PromptRegistry:
    """
    Registry for task prompt configurations.

    Allows registration of prompts per (task_type, workflow_type, doc_type).
    Falls back to defaults when specific configurations aren't registered.
    """

    def __init__(self):
        """Initialize with default configurations."""
        # Key: (task_type, workflow_type, doc_type) or with None for wildcards
        self._configs: Dict[Tuple[Optional[str], Optional[str], Optional[str]], PromptConfig] = {}

        # Register defaults
        self._register_defaults()

    def _register_defaults(self) -> None:
        """Register default prompt configurations."""
        # Default review config (fallback for all review types)
        self.register("REVIEW", None, None, DEFAULT_REVIEW_CONFIG)

        # Default approval config (fallback for all approval types)
        self.register("APPROVAL", None, None, DEFAULT_APPROVAL_CONFIG)

        # CR post-review (includes execution checks)
        self.register("REVIEW", "POST_REVIEW", "CR", CR_POST_REVIEW_CONFIG)

        # SOP review (includes procedure checks)
        self.register("REVIEW", "REVIEW", "SOP", SOP_REVIEW_CONFIG)

    def register(
        self,
        task_type: Optional[str],
        workflow_type: Optional[str],
        doc_type: Optional[str],
        config: PromptConfig
    ) -> None:
        """
        Register a prompt configuration.

        Args:
            task_type: "REVIEW" or "APPROVAL" (None for any)
            workflow_type: e.g., "PRE_REVIEW", "POST_APPROVAL" (None for any)
            doc_type: e.g., "CR", "SOP", "INV" (None for any)
            config: The PromptConfig to use
        """
        key = (task_type, workflow_type, doc_type)
        self._configs[key] = config

    def get_config(
        self,
        task_type: str,
        workflow_type: str,
        doc_type: str
    ) -> PromptConfig:
        """
        Get the most specific configuration for the given context.

        Falls back through specificity levels:
        1. (task_type, workflow_type, doc_type) - exact match
        2. (task_type, workflow_type, None) - any doc type
        3. (task_type, None, doc_type) - any workflow
        4. (task_type, None, None) - task type default
        5. (None, None, None) - global default

        Returns:
            The most specific PromptConfig found
        """
        # Try from most specific to least specific
        lookup_order = [
            (task_type, workflow_type, doc_type),
            (task_type, workflow_type, None),
            (task_type, None, doc_type),
            (task_type, None, None),
            (None, None, None),
        ]

        for key in lookup_order:
            if key in self._configs:
                return self._configs[key]

        # Absolute fallback - return default review config
        return DEFAULT_REVIEW_CONFIG

    def generate_review_content(
        self,
        doc_id: str,
        version: str,
        workflow_type: str,
        assignee: str,
        assigned_by: str,
        task_id: str,
        doc_type: str = ""
    ) -> str:
        """
        Generate review task content using registered configuration.

        Args:
            doc_id: Document ID (e.g., "CR-026")
            version: Document version
            workflow_type: Workflow type (e.g., "PRE_REVIEW", "POST_REVIEW")
            assignee: User assigned to review
            assigned_by: User who assigned the review
            task_id: Task identifier
            doc_type: Document type for prompt customization

        Returns:
            Formatted task content string
        """
        config = self.get_config("REVIEW", workflow_type, doc_type)

        # Group checklist items by category
        categories: Dict[str, List[ChecklistItem]] = {}
        for item in config.checklist_items:
            if item.category not in categories:
                categories[item.category] = []
            categories[item.category].append(item)

        # Build checklist sections
        checklist_sections = []
        for category, items in categories.items():
            lines = [f"### {category}\n"]
            lines.append("| Item | Status | Evidence |")
            lines.append("|------|--------|----------|")
            for item in items:
                evidence = f"({item.evidence_prompt})" if item.evidence_prompt else ""
                lines.append(f"| {item.item} | PASS / FAIL | {evidence} |")
            checklist_sections.append("\n".join(lines))

        checklist_text = "\n\n".join(checklist_sections)

        # Build reminders
        reminders_text = "\n".join(f"- {r}" for r in config.critical_reminders)

        # Build additional sections
        additional_text = ""
        for title, content in config.additional_sections:
            additional_text += f"\n\n## {title}\n\n{content}"

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

{checklist_text}

---

## STRUCTURED REVIEW RESPONSE FORMAT

Your review comment MUST follow this format:

```
## {assignee} Review: {doc_id}

### Checklist Verification

[Complete checklist table with PASS/FAIL and evidence]

### Findings

[List ALL findings. Every finding is a deficiency.]

1. [Finding or "No findings"]

### Recommendation

[RECOMMEND / REQUEST UPDATES] - [Brief rationale]
```

---

## CRITICAL REMINDERS

{reminders_text}

**There is no "approve with comments." There is no severity classification.**
**If ANY deficiency exists, the only valid outcome is REQUEST UPDATES.**
{additional_text}
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

    def generate_approval_content(
        self,
        doc_id: str,
        version: str,
        workflow_type: str,
        assignee: str,
        assigned_by: str,
        task_id: str,
        doc_type: str = ""
    ) -> str:
        """
        Generate approval task content using registered configuration.

        Args:
            doc_id: Document ID (e.g., "CR-026")
            version: Document version
            workflow_type: Workflow type (e.g., "PRE_APPROVAL", "POST_APPROVAL")
            assignee: User assigned to approve
            assigned_by: User who assigned the approval
            task_id: Task identifier
            doc_type: Document type for prompt customization

        Returns:
            Formatted task content string
        """
        config = self.get_config("APPROVAL", workflow_type, doc_type)

        # Build checklist
        checklist_lines = ["| Item | Verified |", "|------|----------|"]
        for item in config.checklist_items:
            checklist_lines.append(f"| {item.item} | YES / NO |")
        checklist_text = "\n".join(checklist_lines)

        # Build reminders
        reminders_text = "\n".join(f"- {r}" for r in config.critical_reminders)

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

{checklist_text}

**If ANY item is NO: REJECT**

---

## CRITICAL REMINDERS

{reminders_text}

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


# Global registry instance
_registry: Optional[PromptRegistry] = None


def get_prompt_registry() -> PromptRegistry:
    """Get the global prompt registry instance."""
    global _registry
    if _registry is None:
        _registry = PromptRegistry()
    return _registry
