"""
Test Prompt Registry

Tests for the PromptRegistry that generates configurable task prompts.

Created as part of CR-026: QMS CLI Extensibility Refactoring
"""
import sys
from pathlib import Path

import pytest

# Add qms-cli to path for imports
QMS_CLI_DIR = Path(__file__).parent.parent
if str(QMS_CLI_DIR) not in sys.path:
    sys.path.insert(0, str(QMS_CLI_DIR))

from prompts import (
    PromptRegistry, PromptConfig, ChecklistItem,
    get_prompt_registry, DEFAULT_REVIEW_CONFIG, DEFAULT_APPROVAL_CONFIG,
    CR_POST_REVIEW_CONFIG, SOP_REVIEW_CONFIG,
    load_config_from_yaml, get_prompt_file_path, PROMPTS_DIR
)


class TestPromptRegistry:
    """Tests for PromptRegistry."""

    def test_get_registry_returns_singleton(self):
        """get_prompt_registry returns the same instance."""
        registry1 = get_prompt_registry()
        registry2 = get_prompt_registry()
        assert registry1 is registry2

    def test_has_default_review_config(self):
        """Registry has default review configuration."""
        registry = PromptRegistry()
        config = registry.get_config("REVIEW", "REVIEW", "UNKNOWN")
        assert config is not None
        assert len(config.checklist_items) > 0

    def test_has_default_approval_config(self):
        """Registry has default approval configuration."""
        registry = PromptRegistry()
        config = registry.get_config("APPROVAL", "APPROVAL", "UNKNOWN")
        assert config is not None
        assert len(config.checklist_items) > 0

    def test_cr_post_review_has_execution_checks(self):
        """CR post-review config includes execution checks."""
        registry = PromptRegistry()
        config = registry.get_config("REVIEW", "POST_REVIEW", "CR")

        # Find execution-related checklist items
        execution_items = [
            item for item in config.checklist_items
            if "execution" in item.category.lower() or "EI" in item.item
        ]
        assert len(execution_items) > 0, "CR post-review should have execution checks"

    def test_sop_review_has_procedure_checks(self):
        """SOP review config includes procedure checks."""
        registry = PromptRegistry()
        config = registry.get_config("REVIEW", "REVIEW", "SOP")

        # Find procedure-related checklist items
        procedure_items = [
            item for item in config.checklist_items
            if "procedure" in item.category.lower() or "Responsibilities" in item.item
        ]
        assert len(procedure_items) > 0, "SOP review should have procedure checks"

    def test_fallback_to_default(self):
        """Unknown doc type falls back to workflow default config."""
        registry = PromptRegistry()
        # Unknown doc type should fall back to workflow default (review/review/default.yaml)
        config1 = registry.get_config("REVIEW", "REVIEW", "UNKNOWN_TYPE")
        config2 = registry.get_config("REVIEW", "REVIEW", "ANOTHER_UNKNOWN")
        # Both should get the same workflow default config
        assert len(config1.checklist_items) == len(config2.checklist_items)
        assert len(config1.critical_reminders) == len(config2.critical_reminders)

    def test_register_custom_config(self):
        """In-memory registration is used as fallback when no YAML files exist.

        Note (CR-027): YAML file loading takes priority over in-memory registration.
        This test verifies the in-memory registration mechanism still works by testing
        that configs can be registered and stored internally. In practice, YAML files
        should be used for all prompt customization.
        """
        registry = PromptRegistry()
        custom_config = PromptConfig(
            checklist_items=[
                ChecklistItem("Custom", "Custom check item", "custom evidence")
            ],
            critical_reminders=["Custom reminder"]
        )

        # Register a custom config
        registry.register("REVIEW", "CUSTOM_WORKFLOW", "CUSTOM_TYPE", custom_config)

        # Verify it was stored in the internal registry
        key = ("REVIEW", "CUSTOM_WORKFLOW", "CUSTOM_TYPE")
        assert key in registry._configs
        assert registry._configs[key] is custom_config
        assert registry._configs[key].checklist_items[0].item == "Custom check item"


class TestPromptGeneration:
    """Tests for prompt content generation."""

    def test_generate_review_content_includes_required_fields(self):
        """Review content includes all required fields."""
        registry = PromptRegistry()
        content = registry.generate_review_content(
            doc_id="TEST-001",
            version="0.1",
            workflow_type="PRE_REVIEW",
            assignee="qa",
            assigned_by="claude",
            task_id="task-TEST-001-pre_review-v0-1"
        )

        assert "TEST-001" in content
        assert "0.1" in content
        assert "PRE_REVIEW" in content
        assert "qa" in content
        assert "claude" in content
        assert "task-TEST-001-pre_review-v0-1" in content

    def test_generate_review_content_includes_checklist(self):
        """Review content includes verification checklist."""
        registry = PromptRegistry()
        content = registry.generate_review_content(
            doc_id="SOP-001",
            version="1.0",
            workflow_type="REVIEW",
            assignee="qa",
            assigned_by="lead",
            task_id="task-SOP-001-review-v1-0"
        )

        assert "MANDATORY VERIFICATION CHECKLIST" in content
        assert "PASS / FAIL" in content
        assert "title:" in content or "Frontmatter" in content

    def test_generate_review_content_includes_commands(self):
        """Review content includes command examples."""
        registry = PromptRegistry()
        content = registry.generate_review_content(
            doc_id="CR-001",
            version="0.1",
            workflow_type="PRE_REVIEW",
            assignee="qa",
            assigned_by="claude",
            task_id="task-CR-001-pre_review-v0-1"
        )

        assert "--recommend" in content
        assert "--request-updates" in content
        assert "/qms --user qa review CR-001" in content

    def test_generate_approval_content_includes_required_fields(self):
        """Approval content includes all required fields."""
        registry = PromptRegistry()
        content = registry.generate_approval_content(
            doc_id="TEST-001",
            version="1.0",
            workflow_type="PRE_APPROVAL",
            assignee="qa",
            assigned_by="claude",
            task_id="task-TEST-001-pre_approval-v1-0"
        )

        assert "TEST-001" in content
        assert "1.0" in content
        assert "PRE_APPROVAL" in content
        assert "qa" in content
        assert "claude" in content

    def test_generate_approval_content_includes_checklist(self):
        """Approval content includes pre-approval checklist."""
        registry = PromptRegistry()
        content = registry.generate_approval_content(
            doc_id="SOP-001",
            version="1.0",
            workflow_type="APPROVAL",
            assignee="qa",
            assigned_by="lead",
            task_id="task-SOP-001-approval-v1-0"
        )

        assert "Pre-Approval Checklist" in content or "FINAL VERIFICATION" in content
        assert "YES / NO" in content

    def test_generate_approval_content_includes_commands(self):
        """Approval content includes command examples."""
        registry = PromptRegistry()
        content = registry.generate_approval_content(
            doc_id="CR-001",
            version="1.0",
            workflow_type="PRE_APPROVAL",
            assignee="qa",
            assigned_by="claude",
            task_id="task-CR-001-pre_approval-v1-0"
        )

        assert "approve" in content
        assert "reject" in content
        assert "/qms --user qa" in content

    def test_review_content_uses_doc_type_specific_config(self):
        """Review content uses doc-type specific checklist when available."""
        registry = PromptRegistry()

        # CR post-review should include execution checks
        cr_content = registry.generate_review_content(
            doc_id="CR-026",
            version="1.0",
            workflow_type="POST_REVIEW",
            assignee="qa",
            assigned_by="claude",
            task_id="task-CR-026-post_review-v1-0",
            doc_type="CR"
        )

        assert "execution" in cr_content.lower() or "EI" in cr_content

    def test_review_critical_reminders_included(self):
        """Review content includes critical reminders."""
        registry = PromptRegistry()
        content = registry.generate_review_content(
            doc_id="TEST-001",
            version="0.1",
            workflow_type="REVIEW",
            assignee="qa",
            assigned_by="lead",
            task_id="task-TEST-001-review-v0-1"
        )

        assert "CRITICAL REMINDERS" in content
        # Should have binary compliance reminder
        assert "BINARY" in content or "binary" in content

    def test_approval_critical_reminders_included(self):
        """Approval content includes critical reminders."""
        registry = PromptRegistry()
        content = registry.generate_approval_content(
            doc_id="TEST-001",
            version="1.0",
            workflow_type="APPROVAL",
            assignee="qa",
            assigned_by="lead",
            task_id="task-TEST-001-approval-v1-0"
        )

        assert "CRITICAL REMINDERS" in content
        # Should mention rejection being safer
        assert "safer" in content.lower() or "gatekeeper" in content.lower()


class TestChecklistItem:
    """Tests for ChecklistItem dataclass."""

    def test_checklist_item_creation(self):
        """Can create checklist item with all fields."""
        item = ChecklistItem(
            category="Test Category",
            item="Test item description",
            evidence_prompt="provide evidence"
        )
        assert item.category == "Test Category"
        assert item.item == "Test item description"
        assert item.evidence_prompt == "provide evidence"

    def test_checklist_item_default_evidence(self):
        """Checklist item has empty evidence prompt by default."""
        item = ChecklistItem(
            category="Test",
            item="Test item"
        )
        assert item.evidence_prompt == ""


class TestPromptConfig:
    """Tests for PromptConfig dataclass."""

    def test_prompt_config_defaults(self):
        """PromptConfig has sensible defaults."""
        config = PromptConfig()
        assert config.checklist_items == []
        assert config.critical_reminders == []
        assert config.additional_sections == []
        assert config.response_format is None
        assert config.custom_header is None
        assert config.custom_footer is None

    def test_prompt_config_with_items(self):
        """Can create PromptConfig with checklist items."""
        config = PromptConfig(
            checklist_items=[
                ChecklistItem("A", "Item 1"),
                ChecklistItem("A", "Item 2"),
                ChecklistItem("B", "Item 3"),
            ],
            critical_reminders=["Reminder 1", "Reminder 2"]
        )
        assert len(config.checklist_items) == 3
        assert len(config.critical_reminders) == 2


class TestDefaultConfigs:
    """Tests for default configurations."""

    def test_default_review_config_has_frontmatter_checks(self):
        """Default review config includes frontmatter verification."""
        frontmatter_items = [
            item for item in DEFAULT_REVIEW_CONFIG.checklist_items
            if "frontmatter" in item.category.lower() or "title" in item.item.lower()
        ]
        assert len(frontmatter_items) > 0

    def test_default_review_config_has_structure_checks(self):
        """Default review config includes structure verification."""
        structure_items = [
            item for item in DEFAULT_REVIEW_CONFIG.checklist_items
            if "structure" in item.category.lower()
        ]
        assert len(structure_items) > 0

    def test_default_review_config_has_content_checks(self):
        """Default review config includes content verification."""
        content_items = [
            item for item in DEFAULT_REVIEW_CONFIG.checklist_items
            if "content" in item.category.lower()
        ]
        assert len(content_items) > 0

    def test_default_approval_config_has_checks(self):
        """Default approval config has pre-approval checks."""
        assert len(DEFAULT_APPROVAL_CONFIG.checklist_items) > 0
        assert len(DEFAULT_APPROVAL_CONFIG.critical_reminders) > 0

    def test_cr_post_review_extends_default(self):
        """CR post-review config extends default with execution checks."""
        # CR post-review should have more items than default
        assert len(CR_POST_REVIEW_CONFIG.checklist_items) >= len(DEFAULT_REVIEW_CONFIG.checklist_items)

    def test_sop_review_extends_default(self):
        """SOP review config extends default with procedure checks."""
        # SOP review should have more items than default
        assert len(SOP_REVIEW_CONFIG.checklist_items) >= len(DEFAULT_REVIEW_CONFIG.checklist_items)


# =============================================================================
# CR-027: YAML File Loading Tests
# =============================================================================

class TestYamlFileLoading:
    """Tests for YAML file loading functionality (CR-027)."""

    def test_prompts_directory_exists(self):
        """Prompts directory exists."""
        assert PROMPTS_DIR.exists(), f"Prompts directory not found: {PROMPTS_DIR}"
        assert PROMPTS_DIR.is_dir()

    def test_review_default_yaml_exists(self):
        """Default review YAML file exists."""
        default_path = PROMPTS_DIR / "review" / "default.yaml"
        assert default_path.exists(), f"review/default.yaml not found: {default_path}"

    def test_approval_default_yaml_exists(self):
        """Default approval YAML file exists."""
        default_path = PROMPTS_DIR / "approval" / "default.yaml"
        assert default_path.exists(), f"approval/default.yaml not found: {default_path}"

    def test_cr_post_review_yaml_exists(self):
        """CR post-review YAML file exists."""
        cr_path = PROMPTS_DIR / "review" / "post_review" / "cr.yaml"
        assert cr_path.exists(), f"review/post_review/cr.yaml not found: {cr_path}"

    def test_sop_review_yaml_exists(self):
        """SOP review YAML file exists."""
        sop_path = PROMPTS_DIR / "review" / "review" / "sop.yaml"
        assert sop_path.exists(), f"review/review/sop.yaml not found: {sop_path}"

    def test_load_config_from_yaml_returns_prompt_config(self):
        """load_config_from_yaml returns PromptConfig."""
        default_path = PROMPTS_DIR / "review" / "default.yaml"
        config = load_config_from_yaml(default_path)
        assert config is not None
        assert isinstance(config, PromptConfig)

    def test_load_config_from_yaml_has_checklist_items(self):
        """Loaded config has checklist items."""
        default_path = PROMPTS_DIR / "review" / "default.yaml"
        config = load_config_from_yaml(default_path)
        assert len(config.checklist_items) > 0

    def test_load_config_from_yaml_has_critical_reminders(self):
        """Loaded config has critical reminders."""
        default_path = PROMPTS_DIR / "review" / "default.yaml"
        config = load_config_from_yaml(default_path)
        assert len(config.critical_reminders) > 0

    def test_load_config_from_yaml_nonexistent_returns_none(self):
        """load_config_from_yaml returns None for nonexistent file."""
        nonexistent = PROMPTS_DIR / "nonexistent" / "file.yaml"
        config = load_config_from_yaml(nonexistent)
        assert config is None


class TestYamlFallbackChain:
    """Tests for YAML file fallback chain (CR-027)."""

    def test_get_prompt_file_path_exact_match(self):
        """Finds exact match file (cr.yaml for CR post-review)."""
        path = get_prompt_file_path("REVIEW", "POST_REVIEW", "CR")
        assert path is not None
        assert path.name == "cr.yaml"
        assert "post_review" in str(path)

    def test_get_prompt_file_path_workflow_default(self):
        """Falls back to workflow default when no doc-type match."""
        path = get_prompt_file_path("REVIEW", "PRE_REVIEW", "UNKNOWN")
        assert path is not None
        assert path.name == "default.yaml"
        assert "pre_review" in str(path)

    def test_get_prompt_file_path_task_type_default(self):
        """Falls back to task type default when no workflow match."""
        path = get_prompt_file_path("REVIEW", "UNKNOWN_WORKFLOW", "UNKNOWN")
        assert path is not None
        assert path.name == "default.yaml"
        assert "review" in str(path)

    def test_get_prompt_file_path_case_insensitive(self):
        """Path lookup is case-insensitive."""
        path1 = get_prompt_file_path("REVIEW", "POST_REVIEW", "CR")
        path2 = get_prompt_file_path("review", "post_review", "cr")
        assert path1 == path2


class TestYamlIntegration:
    """Integration tests for YAML file loading with PromptRegistry (CR-027)."""

    def test_registry_loads_cr_post_review_from_yaml(self):
        """Registry loads CR post-review config from YAML file."""
        registry = PromptRegistry()
        config = registry.get_config("REVIEW", "POST_REVIEW", "CR")

        # Should have execution checks from YAML
        execution_items = [
            item for item in config.checklist_items
            if "execution" in item.category.lower() or "EI" in item.item
        ]
        assert len(execution_items) > 0

    def test_registry_loads_sop_review_from_yaml(self):
        """Registry loads SOP review config from YAML file."""
        registry = PromptRegistry()
        config = registry.get_config("REVIEW", "REVIEW", "SOP")

        # Should have procedure checks from YAML
        procedure_items = [
            item for item in config.checklist_items
            if "procedure" in item.category.lower()
        ]
        assert len(procedure_items) > 0

    def test_registry_loads_default_review_from_yaml(self):
        """Registry loads default review config from YAML file."""
        registry = PromptRegistry()
        config = registry.get_config("REVIEW", "PRE_REVIEW", "UNKNOWN")

        # Should have standard checks
        assert len(config.checklist_items) > 0
        assert len(config.critical_reminders) > 0

    def test_registry_loads_approval_from_yaml(self):
        """Registry loads approval config from YAML file."""
        registry = PromptRegistry()
        config = registry.get_config("APPROVAL", "PRE_APPROVAL", "CR")

        # Should have approval checks
        assert len(config.checklist_items) > 0
        assert len(config.critical_reminders) > 0
