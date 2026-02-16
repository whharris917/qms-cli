"""
QMS Prompt Registry

Configurable prompt generation for review and approval tasks.
Allows customization per document type and workflow phase.

Created as part of CR-026: QMS CLI Extensibility Refactoring
Updated in CR-027: Extract prompts to external YAML files
Updated in CR-087: Remove in-memory fallback; YAML is sole config source
"""
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Tuple

import yaml


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
# YAML File Loading (CR-027)
# =============================================================================

# Directory containing prompt YAML files
PROMPTS_DIR = Path(__file__).parent / "prompts"


def load_config_from_yaml(file_path: Path) -> Optional[PromptConfig]:
    """
    Load a PromptConfig from a YAML file.

    Args:
        file_path: Path to the YAML file

    Returns:
        PromptConfig if file exists and is valid, None otherwise
    """
    if not file_path.exists():
        return None

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)

        if not data:
            return None

        # Parse checklist items
        checklist_items = []
        for category_data in data.get('checklist', []):
            category = category_data.get('category', '')
            for item_data in category_data.get('items', []):
                if isinstance(item_data, str):
                    # Simple string item
                    checklist_items.append(ChecklistItem(
                        category=category,
                        item=item_data,
                        evidence_prompt=""
                    ))
                elif isinstance(item_data, dict):
                    # Dict with text and optional evidence_prompt
                    checklist_items.append(ChecklistItem(
                        category=category,
                        item=item_data.get('text', ''),
                        evidence_prompt=item_data.get('evidence_prompt', '')
                    ))

        # Parse critical reminders
        critical_reminders = data.get('critical_reminders', [])

        # Parse additional sections
        additional_sections = []
        for section in data.get('additional_sections', []):
            if isinstance(section, dict):
                title = section.get('title', '')
                content = section.get('content', '')
                additional_sections.append((title, content))

        return PromptConfig(
            checklist_items=checklist_items,
            critical_reminders=critical_reminders,
            additional_sections=additional_sections,
            response_format=data.get('response_format'),
            custom_header=data.get('custom_header'),
            custom_footer=data.get('custom_footer'),
        )

    except (yaml.YAMLError, IOError):
        return None


def get_prompt_file_path(
    task_type: str,
    workflow_type: str,
    doc_type: str
) -> Optional[Path]:
    """
    Find the appropriate prompt file using fallback chain.

    Fallback order:
    1. {task_type}/{workflow_type}/{doc_type}.yaml (exact match)
    2. {task_type}/{workflow_type}/default.yaml (workflow default)
    3. {task_type}/default.yaml (task type default)

    Args:
        task_type: "review" or "approval"
        workflow_type: e.g., "pre_review", "post_review", "review"
        doc_type: e.g., "cr", "sop", "inv"

    Returns:
        Path to the first matching file, or None if no file found
    """
    # Handle None values
    if not task_type or not workflow_type:
        return None

    task_type_lower = task_type.lower()
    workflow_type_lower = workflow_type.lower()
    doc_type_lower = doc_type.lower() if doc_type else ""

    # Build fallback paths
    paths_to_try = []

    if doc_type_lower:
        # Exact match: task_type/workflow_type/doc_type.yaml
        paths_to_try.append(
            PROMPTS_DIR / task_type_lower / workflow_type_lower / f"{doc_type_lower}.yaml"
        )

    # Workflow default: task_type/workflow_type/default.yaml
    paths_to_try.append(
        PROMPTS_DIR / task_type_lower / workflow_type_lower / "default.yaml"
    )

    # Task type default: task_type/default.yaml
    paths_to_try.append(
        PROMPTS_DIR / task_type_lower / "default.yaml"
    )

    for path in paths_to_try:
        if path.exists():
            return path

    return None


# =============================================================================
# Prompt Registry
# =============================================================================

class PromptRegistry:
    """
    Registry for task prompt configurations.

    Loads prompt configurations from YAML files in the prompts/ directory.
    YAML is the sole configuration source (CR-087).
    """

    def __init__(self):
        """Initialize the registry."""
        pass

    def get_config(
        self,
        task_type: str,
        workflow_type: str,
        doc_type: str
    ) -> PromptConfig:
        """
        Get the most specific configuration for the given context.

        Loads from YAML files using hierarchical fallback:
        1. {task_type}/{workflow_type}/{doc_type}.yaml (exact match)
        2. {task_type}/{workflow_type}/default.yaml (workflow default)
        3. {task_type}/default.yaml (task type default)

        Raises:
            FileNotFoundError: If no YAML configuration file is found

        Returns:
            The most specific PromptConfig found
        """
        file_path = get_prompt_file_path(task_type, workflow_type, doc_type)
        if file_path:
            config = load_config_from_yaml(file_path)
            if config:
                return config

        raise FileNotFoundError(
            f"No prompt configuration found for task_type={task_type}, "
            f"workflow_type={workflow_type}, doc_type={doc_type}. "
            f"Expected YAML files in {PROMPTS_DIR}/. "
            f"Check that the prompts/ directory is complete."
        )

    def generate_review_content(
        self,
        doc_id: str,
        version: str,
        workflow_type: str,
        assignee: str,
        assigned_by: str,
        task_id: str,
        doc_type: str = "",
        title: str = "",
        status: str = "",
        responsible_user: str = ""
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
            title: Document title (CR-036-VAR-005)
            status: Document status (CR-036-VAR-005)
            responsible_user: Document owner (CR-036-VAR-005)

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

        # CR-034: Custom header rendering
        header_text = ""
        if config.custom_header:
            header_text = f"\n{config.custom_header}\n\n---\n"

        # CR-034: Custom footer rendering
        footer_text = ""
        if config.custom_footer:
            footer_text = f"\n\n---\n\n{config.custom_footer}"

        return f"""---
task_id: {task_id}
task_type: REVIEW
workflow_type: {workflow_type}
doc_id: {doc_id}
title: {title}
status: {status}
responsible_user: {responsible_user}
assigned_by: {assigned_by}
assigned_date: {today()}
version: {version}
---
{header_text}
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
{footer_text}"""

    def generate_approval_content(
        self,
        doc_id: str,
        version: str,
        workflow_type: str,
        assignee: str,
        assigned_by: str,
        task_id: str,
        doc_type: str = "",
        title: str = "",
        status: str = "",
        responsible_user: str = ""
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
            title: Document title (CR-036-VAR-005)
            status: Document status (CR-036-VAR-005)
            responsible_user: Document owner (CR-036-VAR-005)

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

        # CR-034: Custom header rendering
        header_text = ""
        if config.custom_header:
            header_text = f"\n{config.custom_header}\n\n---\n"

        # CR-034: Custom footer rendering
        footer_text = ""
        if config.custom_footer:
            footer_text = f"\n\n---\n\n{config.custom_footer}"

        return f"""---
task_id: {task_id}
task_type: APPROVAL
workflow_type: {workflow_type}
doc_id: {doc_id}
title: {title}
status: {status}
responsible_user: {responsible_user}
assigned_by: {assigned_by}
assigned_date: {today()}
version: {version}
---
{header_text}
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
{footer_text}"""


# Global registry instance
_registry: Optional[PromptRegistry] = None


def get_prompt_registry() -> PromptRegistry:
    """Get the global prompt registry instance."""
    global _registry
    if _registry is None:
        _registry = PromptRegistry()
    return _registry
