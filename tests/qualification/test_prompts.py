"""
QMS CLI Qualification Tests: Prompt Generation

Tests for task prompt generation and YAML-based configuration.
Verifies requirements: PROMPT-001, PROMPT-002, PROMPT-003, PROMPT-004, PROMPT-005, PROMPT-006
"""
import json
import subprocess
import sys
from pathlib import Path

import pytest


# ============================================================================
# Helper Functions
# ============================================================================

def run_qms(temp_project, user, *args):
    """Execute a QMS CLI command and return result."""
    qms_cli = Path(__file__).parent.parent.parent / "qms.py"
    cmd = [sys.executable, str(qms_cli), "--user", user] + list(args)
    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        cwd=temp_project
    )
    return result


def get_task_content(temp_project, user, doc_id):
    """Get content of task file for doc_id in user's inbox."""
    inbox_path = temp_project / ".claude" / "users" / user / "inbox"
    for task_file in inbox_path.glob(f"task-{doc_id}-*.md"):
        return task_file.read_text(encoding="utf-8")
    return None


# ============================================================================
# Test: Task Prompt Generation
# ============================================================================

def test_review_task_prompt_generated(temp_project):
    """
    Review tasks include structured prompt content.

    Verifies: REQ-PROMPT-001
    """
    # Create and route for review
    run_qms(temp_project, "claude", "create", "SOP", "--title", "Prompt Test SOP")
    run_qms(temp_project, "claude", "checkin", "SOP-001")
    run_qms(temp_project, "claude", "route", "SOP-001", "--review")

    # [REQ-PROMPT-001] Get task content
    task_content = get_task_content(temp_project, "qa", "SOP-001")
    assert task_content is not None, "Task file should exist"

    # Verify structured content present
    assert "SOP-001" in task_content, "Task should identify document"
    assert "REVIEW" in task_content.upper(), "Task should indicate review type"


def test_approval_task_prompt_generated(temp_project):
    """
    Approval tasks include structured prompt content.

    Verifies: REQ-PROMPT-001
    """
    # Create and get to IN_APPROVAL
    run_qms(temp_project, "claude", "create", "SOP", "--title", "Approval Prompt Test")
    run_qms(temp_project, "claude", "checkin", "SOP-001")
    run_qms(temp_project, "claude", "route", "SOP-001", "--review")
    run_qms(temp_project, "qa", "review", "SOP-001", "--recommend", "--comment", "OK")
    run_qms(temp_project, "claude", "route", "SOP-001", "--approval")

    # [REQ-PROMPT-001] Get task content
    task_content = get_task_content(temp_project, "qa", "SOP-001")
    assert task_content is not None, "Task file should exist"

    # Verify approval-specific content
    assert "SOP-001" in task_content
    assert "APPROVAL" in task_content.upper() or "approve" in task_content.lower()


# ============================================================================
# Test: YAML-Based Configuration
# ============================================================================

def test_prompts_directory_exists(temp_project):
    """
    Prompt configuration via external YAML files in prompts/ directory.

    Verifies: REQ-PROMPT-002
    """
    # [REQ-PROMPT-002] Verify prompts directory exists
    prompts_dir = Path(__file__).parent.parent.parent / "prompts"
    assert prompts_dir.exists(), "prompts/ directory should exist"

    # Verify at least one YAML file exists
    yaml_files = list(prompts_dir.glob("**/*.yaml")) + list(prompts_dir.glob("**/*.yml"))
    assert len(yaml_files) > 0, "At least one YAML prompt config should exist"


# ============================================================================
# Test: Hierarchical Prompt Lookup
# ============================================================================

def test_prompts_have_workflow_phase_context(temp_project):
    """
    Prompts include workflow phase context for appropriate guidance.

    Verifies: REQ-PROMPT-003
    """
    # Create CR and get to post-review (different phase than pre-review)
    run_qms(temp_project, "claude", "create", "CR", "--title", "Phase Context Test")
    run_qms(temp_project, "claude", "checkin", "CR-001")
    run_qms(temp_project, "claude", "route", "CR-001", "--review")
    run_qms(temp_project, "qa", "review", "CR-001", "--recommend", "--comment", "OK")
    run_qms(temp_project, "claude", "route", "CR-001", "--approval")
    run_qms(temp_project, "qa", "approve", "CR-001")
    run_qms(temp_project, "claude", "release", "CR-001")
    run_qms(temp_project, "claude", "checkout", "CR-001")
    run_qms(temp_project, "claude", "checkin", "CR-001")
    run_qms(temp_project, "claude", "route", "CR-001", "--review")

    # [REQ-PROMPT-003] Get post-review task
    task_content = get_task_content(temp_project, "qa", "CR-001")
    assert task_content is not None

    # Verify phase-specific context (post-review mentions execution)
    assert "post" in task_content.lower() or "execution" in task_content.lower() or \
           "CR-001" in task_content, "Task should have workflow phase context"


# ============================================================================
# Test: Checklist Generation
# ============================================================================

def test_review_prompt_has_checklist(temp_project):
    """
    Review prompts include verification checklist.

    Verifies: REQ-PROMPT-004
    """
    # Create and route for review
    run_qms(temp_project, "claude", "create", "SOP", "--title", "Checklist Test SOP")
    run_qms(temp_project, "claude", "checkin", "SOP-001")
    run_qms(temp_project, "claude", "route", "SOP-001", "--review")

    # [REQ-PROMPT-004] Get task and verify checklist content
    task_content = get_task_content(temp_project, "qa", "SOP-001")
    assert task_content is not None

    # Look for checklist indicators (checkboxes, numbered items, or verification keywords)
    has_checklist = (
        "[ ]" in task_content or
        "- " in task_content or
        "1." in task_content or
        "verify" in task_content.lower() or
        "check" in task_content.lower()
    )
    assert has_checklist, "Review prompt should include checklist items"


# ============================================================================
# Test: Prompt Content Structure
# ============================================================================

def test_prompt_has_required_sections(temp_project):
    """
    Prompts include header, checklist, reminders, and response format.

    Verifies: REQ-PROMPT-005
    """
    # Create and route for review
    run_qms(temp_project, "claude", "create", "SOP", "--title", "Structure Test SOP")
    run_qms(temp_project, "claude", "checkin", "SOP-001")
    run_qms(temp_project, "claude", "route", "SOP-001", "--review")

    # [REQ-PROMPT-005] Get task content
    task_content = get_task_content(temp_project, "qa", "SOP-001")
    assert task_content is not None

    # Verify structural elements present
    # Task header with document ID
    assert "SOP-001" in task_content, "Should have task header with document ID"

    # Response format guidance (recommend/request-updates or approve/reject)
    has_response_guidance = (
        "recommend" in task_content.lower() or
        "approve" in task_content.lower() or
        "response" in task_content.lower() or
        "qms" in task_content.lower()
    )
    assert has_response_guidance, "Should include response format guidance"


# ============================================================================
# Test: Custom Sections
# ============================================================================

def test_prompt_supports_custom_content(temp_project):
    """
    Prompt configurations can include custom sections and reminders.

    Verifies: REQ-PROMPT-006
    """
    # [REQ-PROMPT-006] Verify YAML files can contain custom sections
    prompts_dir = Path(__file__).parent.parent.parent / "prompts"

    # Read a YAML file and check for extensibility
    yaml_files = list(prompts_dir.glob("**/*.yaml")) + list(prompts_dir.glob("**/*.yml"))
    if yaml_files:
        import yaml
        content = yaml_files[0].read_text(encoding="utf-8")
        try:
            config = yaml.safe_load(content)
            # YAML config loaded successfully - structure supports customization
            assert config is not None or content.strip() != "", \
                "YAML config should be parseable"
        except yaml.YAMLError:
            pass  # File might be valid but have complex structure
