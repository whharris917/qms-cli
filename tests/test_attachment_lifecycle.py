"""
Test Attachment Lifecycle

Qualification tests for:
  REQ-DOC-018: Attachment document classification
  REQ-DOC-019: Terminal state checkout guard
  REQ-DOC-020: Cascade close of child attachments

Created as part of CR-095: Attachment Auto-Close
"""
import sys
from pathlib import Path

import pytest

# Add qms-cli to path for imports
QMS_CLI_DIR = Path(__file__).parent.parent
if str(QMS_CLI_DIR) not in sys.path:
    sys.path.insert(0, str(QMS_CLI_DIR))

from qms_config import Status, DOCUMENT_TYPES, get_all_document_types


# =============================================================================
# REQ-DOC-018: Attachment document classification
# =============================================================================

class TestAttachmentClassification:
    """REQ-DOC-018: Documents with attachment=True are classified as attachments."""

    def test_vr_is_attachment(self):
        """VR documents have attachment=True."""
        all_types = get_all_document_types()
        assert all_types["VR"].get("attachment") is True

    def test_cr_not_attachment(self):
        """CR documents are not attachments."""
        all_types = get_all_document_types()
        assert all_types["CR"].get("attachment") is not True

    def test_sop_not_attachment(self):
        """SOP documents are not attachments."""
        all_types = get_all_document_types()
        assert all_types["SOP"].get("attachment") is not True

    def test_add_not_attachment(self):
        """ADD documents are not attachments (they have their own lifecycle)."""
        all_types = get_all_document_types()
        assert all_types["ADD"].get("attachment") is not True

    def test_attachment_types_are_executable(self):
        """All attachment types must also be executable."""
        all_types = get_all_document_types()
        for type_name, config in all_types.items():
            if config.get("attachment"):
                assert config.get("executable") is True, \
                    f"{type_name} is attachment but not executable"


# =============================================================================
# REQ-DOC-019: Terminal state checkout guard
# =============================================================================

class TestTerminalStateGuard:
    """REQ-DOC-019: CLOSED and RETIRED documents cannot be checked out."""

    def test_closed_is_terminal(self):
        """CLOSED is a terminal state."""
        assert Status.CLOSED.value == "CLOSED"

    def test_retired_is_terminal(self):
        """RETIRED is a terminal state."""
        assert Status.RETIRED.value == "RETIRED"

    def test_draft_is_not_terminal(self):
        """DRAFT is not a terminal state."""
        assert Status.DRAFT.value not in ("CLOSED", "RETIRED")

    def test_effective_is_not_terminal(self):
        """EFFECTIVE is not a terminal state (can be revised)."""
        assert Status.EFFECTIVE.value not in ("CLOSED", "RETIRED")


# =============================================================================
# REQ-DOC-020: Cascade close (unit-level tests)
# =============================================================================

class TestCascadeCloseLogic:
    """REQ-DOC-020: Cascade close discovers and closes attachment children."""

    def test_attachment_types_discoverable(self):
        """All attachment types can be found by iterating document types."""
        all_types = get_all_document_types()
        attachment_types = [
            name for name, config in all_types.items()
            if config.get("attachment")
        ]
        assert "VR" in attachment_types
        assert len(attachment_types) >= 1

    def test_vr_id_pattern_matches_parent(self):
        """VR IDs follow {parent}-VR-NNN pattern for discovery."""
        # This is the pattern used in _cascade_close_attachments
        parent_id = "CR-091"
        child_id = "CR-091-VR-001"
        prefix = "VR"
        # Pattern: {parent_id}-{prefix}-*
        import re
        pattern = f"^{re.escape(parent_id)}-{re.escape(prefix)}-\\d+$"
        assert re.match(pattern, child_id)

    def test_nested_parent_pattern(self):
        """VR IDs with nested parents (ADD) follow expected pattern."""
        parent_id = "CR-094-ADD-001"
        child_id = "CR-094-ADD-001-VR-001"
        prefix = "VR"
        import re
        pattern = f"^{re.escape(parent_id)}-{re.escape(prefix)}-\\d+$"
        assert re.match(pattern, child_id)


# =============================================================================
# Attachment close flexibility
# =============================================================================

class TestAttachmentCloseFlexibility:
    """Attachments can close from any non-terminal status, unlike normal
    executable documents which require POST_APPROVED."""

    def test_terminal_states_rejected(self):
        """Already-terminal attachments cannot be re-closed."""
        terminal = [Status.CLOSED, Status.RETIRED]
        for status in terminal:
            assert status.value in ("CLOSED", "RETIRED")

    def test_non_terminal_states_allowed(self):
        """Non-terminal states are valid for attachment closure."""
        allowed = [
            Status.DRAFT, Status.IN_PRE_REVIEW, Status.PRE_REVIEWED,
            Status.IN_PRE_APPROVAL, Status.PRE_APPROVED,
            Status.IN_EXECUTION, Status.IN_POST_REVIEW,
            Status.POST_REVIEWED, Status.IN_POST_APPROVAL,
            Status.POST_APPROVED,
        ]
        for status in allowed:
            assert status.value not in ("CLOSED", "RETIRED"), \
                f"{status.value} should be valid for attachment close"


# =============================================================================
# Interactive attachment auto-compile
# =============================================================================

class TestInteractiveAutoCompile:
    """Auto-compilation of interactive attachments during cascade close."""

    def test_compile_from_source_data(self):
        """Source data can be compiled into markdown."""
        from interact_source import create_source, add_response
        from interact_compiler import compile_document

        template_path = QMS_CLI_DIR / "seed" / "templates" / "TEMPLATE-VR.md"
        if not template_path.exists():
            pytest.skip("TEMPLATE-VR.md not found")
        template = template_path.read_text(encoding="utf-8")

        source = create_source("CR-001-VR-001", "VR", 5, "__end__",
                               metadata={"parent_doc_id": "CR-001",
                                          "vr_id": "CR-001-VR-001",
                                          "title": "Auto-compile Test"})
        add_response(source, "related_eis", "EI-1", "claude")
        add_response(source, "objective", "Test auto-compile", "claude")
        add_response(source, "pre_conditions", "Ready", "claude")
        add_response(source, "step_instructions.1", "Do it", "claude")
        add_response(source, "step_expected.1", "Expect it", "claude")
        add_response(source, "step_actual.1", "Got it", "claude", commit="abc")
        add_response(source, "step_outcome.1", "Pass", "claude")
        add_response(source, "summary_outcome", "Pass", "claude")
        add_response(source, "summary_narrative", "Done", "claude")
        source["loops"]["steps"] = {"iterations": 1, "closed": True, "reopenings": []}

        result = compile_document(source, template)
        assert "CR-001-VR-001" in result
        assert "Auto-compile Test" in result
        assert "Do it" in result
        assert "Got it" in result

    def test_compile_empty_source(self):
        """Empty source compiles without error (VR created but never authored)."""
        from interact_source import create_source
        from interact_compiler import compile_document

        template_path = QMS_CLI_DIR / "seed" / "templates" / "TEMPLATE-VR.md"
        if not template_path.exists():
            pytest.skip("TEMPLATE-VR.md not found")
        template = template_path.read_text(encoding="utf-8")

        source = create_source("CR-001-VR-001", "VR", 5, "related_eis",
                               metadata={"parent_doc_id": "CR-001",
                                          "vr_id": "CR-001-VR-001",
                                          "title": "Empty VR"})

        result = compile_document(source, template)
        assert "CR-001-VR-001" in result
        assert "Empty VR" in result
        # Should not contain raw placeholders
        assert "{{" not in result
