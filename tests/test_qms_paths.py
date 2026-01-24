"""
Unit tests for QMS CLI path functions.

Tests cover:
- get_doc_type(): Determine document type from doc_id
- get_doc_path(): Get path to document (effective or draft)
- get_archive_path(): Get archive path for versioned documents
- get_workspace_path(): Get user workspace path
- get_inbox_path(): Get user inbox path
- get_next_number(): Get next available document number
"""
import pytest
from pathlib import Path


class TestGetDocType:
    """Tests for get_doc_type() function."""

    def test_sop_type(self, qms_module):
        """SOP documents should return 'SOP' type."""
        assert qms_module.get_doc_type("SOP-001") == "SOP"
        assert qms_module.get_doc_type("SOP-123") == "SOP"

    def test_cr_type(self, qms_module):
        """CR documents should return 'CR' type."""
        assert qms_module.get_doc_type("CR-001") == "CR"
        assert qms_module.get_doc_type("CR-025") == "CR"

    def test_inv_type(self, qms_module):
        """INV documents should return 'INV' type."""
        assert qms_module.get_doc_type("INV-001") == "INV"

    def test_tp_type(self, qms_module):
        """TP (Test Protocol) documents should return 'TP' type (CR-034: sequential format)."""
        # CR-034 CC-007: TP now uses sequential format CR-001-TP-001
        assert qms_module.get_doc_type("CR-001-TP-001") == "TP"
        assert qms_module.get_doc_type("CR-028-TP-002") == "TP"

    def test_var_type(self, qms_module):
        """VAR (Variance Report) documents should return 'VAR' type."""
        assert qms_module.get_doc_type("CR-028-VAR-001") == "VAR"
        assert qms_module.get_doc_type("INV-001-VAR-001") == "VAR"
        assert qms_module.get_doc_type("CR-001-VAR-123") == "VAR"

    def test_sdlc_flow_types(self, qms_module):
        """SDLC-FLOW document types should return namespace-prefixed type."""
        # CR-034 SC-002: SDLC types now return {NAMESPACE}-{TYPE} format
        assert qms_module.get_doc_type("SDLC-FLOW-RS") == "FLOW-RS"
        assert qms_module.get_doc_type("SDLC-FLOW-RTM") == "FLOW-RTM"

    def test_sdlc_qms_types(self, qms_module):
        """SDLC-QMS document types should return namespace-prefixed type."""
        # CR-034 SC-002: SDLC types now return {NAMESPACE}-{TYPE} format
        assert qms_module.get_doc_type("SDLC-QMS-RS") == "QMS-RS"
        assert qms_module.get_doc_type("SDLC-QMS-RTM") == "QMS-RTM"

    def test_template_type(self, qms_module):
        """Template documents should return 'TEMPLATE' type."""
        assert qms_module.get_doc_type("TEMPLATE-CR") == "TEMPLATE"


class TestGetDocPath:
    """Tests for get_doc_path() function."""

    def test_sop_effective_path(self, qms_module):
        """SOP effective path should be QMS/SOP/SOP-XXX.md."""
        path = qms_module.get_doc_path("SOP-001")
        assert path.name == "SOP-001.md"
        assert "SOP" in path.parts

    def test_sop_draft_path(self, qms_module):
        """SOP draft path should be QMS/SOP/SOP-XXX-draft.md."""
        path = qms_module.get_doc_path("SOP-001", draft=True)
        assert path.name == "SOP-001-draft.md"

    def test_cr_uses_folder_per_doc(self, qms_module):
        """CR documents should be in QMS/CR/CR-XXX/CR-XXX.md."""
        path = qms_module.get_doc_path("CR-001")
        assert path.name == "CR-001.md"
        # CR uses folder_per_doc, so path should include CR-001 folder
        assert "CR-001" in path.parts

    def test_cr_draft_path(self, qms_module):
        """CR draft should be in QMS/CR/CR-XXX/CR-XXX-draft.md."""
        path = qms_module.get_doc_path("CR-025", draft=True)
        assert path.name == "CR-025-draft.md"
        assert "CR-025" in path.parts

    def test_inv_uses_folder_per_doc(self, qms_module):
        """INV documents should be in QMS/INV/INV-XXX/INV-XXX.md."""
        path = qms_module.get_doc_path("INV-001")
        assert path.name == "INV-001.md"
        assert "INV-001" in path.parts

    def test_tp_path(self, qms_module):
        """TP documents should be in QMS/CR/ directory."""
        path = qms_module.get_doc_path("CR-001-TP")
        assert path.name == "CR-001-TP.md"
        # TP is in CR directory (not in subfolder per current implementation)
        assert "CR" in path.parts

    def test_capa_path(self, qms_module):
        """CAPA documents should be in QMS/INV/ directory."""
        path = qms_module.get_doc_path("INV-001-CAPA-001")
        assert path.name == "INV-001-CAPA-001.md"
        # CAPA is in INV directory (not in subfolder per current implementation)
        assert "INV" in path.parts

    def test_var_path(self, qms_module):
        """VAR documents should be in parent CR's folder."""
        path = qms_module.get_doc_path("CR-028-VAR-001")
        assert path.name == "CR-028-VAR-001.md"
        # VAR is in parent CR's folder
        assert "CR" in path.parts
        assert "CR-028" in path.parts


class TestGetArchivePath:
    """Tests for get_archive_path() function."""

    def test_archive_path_includes_version(self, qms_module):
        """Archive path should include version in filename."""
        path = qms_module.get_archive_path("SOP-001", "1.0")
        assert path.name == "SOP-001-v1.0.md"

    def test_archive_in_archive_directory(self, qms_module):
        """Archive path should be under .archive directory."""
        path = qms_module.get_archive_path("SOP-001", "2.0")
        assert ".archive" in path.parts

    def test_cr_archive_path(self, qms_module):
        """CR archive should maintain folder structure."""
        path = qms_module.get_archive_path("CR-001", "1.0")
        assert path.name == "CR-001-v1.0.md"
        assert ".archive" in path.parts


class TestGetWorkspacePath:
    """Tests for get_workspace_path() function."""

    def test_workspace_path_structure(self, qms_module):
        """Workspace path should be .claude/users/{user}/workspace/{doc}.md."""
        path = qms_module.get_workspace_path("claude", "CR-025")
        assert path.name == "CR-025.md"
        assert "claude" in path.parts
        assert "workspace" in path.parts

    def test_different_users_different_paths(self, qms_module):
        """Different users should have different workspace paths."""
        claude_path = qms_module.get_workspace_path("claude", "CR-001")
        lead_path = qms_module.get_workspace_path("lead", "CR-001")
        assert claude_path != lead_path
        assert "claude" in claude_path.parts
        assert "lead" in lead_path.parts


class TestGetInboxPath:
    """Tests for get_inbox_path() function."""

    def test_inbox_path_structure(self, qms_module):
        """Inbox path should be .claude/users/{user}/inbox/."""
        path = qms_module.get_inbox_path("qa")
        assert "qa" in path.parts
        assert "inbox" in path.parts

    def test_different_users_different_inboxes(self, qms_module):
        """Different users should have different inbox paths."""
        qa_inbox = qms_module.get_inbox_path("qa")
        claude_inbox = qms_module.get_inbox_path("claude")
        assert qa_inbox != claude_inbox


class TestGetNextNumber:
    """Tests for get_next_number() function."""

    def test_empty_directory_returns_one(self, qms_module):
        """When no documents exist, should return 1."""
        # temp_project fixture creates empty directories
        num = qms_module.get_next_number("SOP")
        assert num == 1

    def test_increments_from_existing(self, qms_module, temp_project):
        """Should return next number after existing documents."""
        # Create some SOP files
        sop_dir = temp_project / "QMS" / "SOP"
        (sop_dir / "SOP-001.md").touch()
        (sop_dir / "SOP-002.md").touch()

        num = qms_module.get_next_number("SOP")
        assert num == 3

    def test_handles_draft_files(self, qms_module, temp_project):
        """Should correctly handle draft file naming."""
        sop_dir = temp_project / "QMS" / "SOP"
        (sop_dir / "SOP-001.md").touch()
        (sop_dir / "SOP-002-draft.md").touch()

        num = qms_module.get_next_number("SOP")
        assert num == 3

    def test_handles_folder_per_doc(self, qms_module, temp_project):
        """Should correctly handle CR folder structure."""
        cr_dir = temp_project / "QMS" / "CR"
        (cr_dir / "CR-001").mkdir()
        (cr_dir / "CR-002").mkdir()

        num = qms_module.get_next_number("CR")
        assert num == 3
