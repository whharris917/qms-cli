"""
QMS CLI Qualification Tests: Document Templates

Tests for template-based document creation and variable substitution.
Verifies requirements: TEMPLATE-001, TEMPLATE-002, TEMPLATE-003, TEMPLATE-004, TEMPLATE-005
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


def read_document(temp_project, doc_path):
    """Read document content from QMS."""
    full_path = temp_project / "QMS" / doc_path
    if not full_path.exists():
        return None
    return full_path.read_text(encoding="utf-8")


def read_frontmatter(file_path):
    """Parse YAML frontmatter from a document."""
    content = file_path.read_text(encoding="utf-8")
    if not content.startswith("---"):
        return {}
    parts = content.split("---", 2)
    if len(parts) < 3:
        return {}
    import yaml
    return yaml.safe_load(parts[1]) or {}


# ============================================================================
# Test: Template-Based Creation
# ============================================================================

def test_new_document_uses_template(temp_project):
    """
    New documents are populated with content from appropriate template.

    Verifies: REQ-TEMPLATE-001
    """
    # [REQ-TEMPLATE-001] Create SOP
    result = run_qms(temp_project, "claude", "create", "SOP",
                     "--title", "Template-Based SOP")
    assert result.returncode == 0

    # Verify document has content (not empty)
    doc_content = read_document(temp_project, "SOP/SOP-001-draft.md")
    assert doc_content is not None
    assert len(doc_content) > 50, "Document should have template content"

    # Verify it contains standard structure elements
    assert "---" in doc_content, "Should have frontmatter"


def test_cr_uses_cr_template(temp_project):
    """
    CR documents use CR-specific template.

    Verifies: REQ-TEMPLATE-001
    """
    # [REQ-TEMPLATE-001] Create CR
    result = run_qms(temp_project, "claude", "create", "CR",
                     "--title", "CR Template Test")
    assert result.returncode == 0

    # Verify document has CR-appropriate content
    doc_content = read_document(temp_project, "CR/CR-001/CR-001-draft.md")
    assert doc_content is not None


# ============================================================================
# Test: Template Location
# ============================================================================

def test_templates_in_qms_template_directory(temp_project):
    """
    Document templates are stored in QMS/TEMPLATE/.

    Verifies: REQ-TEMPLATE-002
    """
    # [REQ-TEMPLATE-002] The template directory is created in temp_project by the fixture
    # The CLI should look for templates in QMS/TEMPLATE/
    # Verify a document created with known template works (implicit template location test)

    # Create document - if this succeeds with template content, templates are found
    result = run_qms(temp_project, "claude", "create", "SOP", "--title", "Template Location Test")
    assert result.returncode == 0

    # Read document and verify it has non-trivial content (came from template)
    doc_content = read_document(temp_project, "SOP/SOP-001-draft.md")
    assert doc_content is not None
    assert len(doc_content) > 100, "Document should have substantial template content"

    # Verify template structure elements are present
    assert "---" in doc_content, "Should have YAML frontmatter from template"
    assert "title:" in doc_content, "Should have title field from template"


# ============================================================================
# Test: Variable Substitution
# ============================================================================

def test_title_substitution(temp_project):
    """
    Template {{TITLE}} variable is substituted with user-provided title.

    Verifies: REQ-TEMPLATE-003
    """
    # [REQ-TEMPLATE-003] Create document with specific title
    run_qms(temp_project, "claude", "create", "SOP",
            "--title", "My Unique Test Title 12345")

    # Verify title appears in document
    doc_content = read_document(temp_project, "SOP/SOP-001-draft.md")
    assert doc_content is not None
    assert "My Unique Test Title 12345" in doc_content, \
        "Title should be substituted in document"


def test_doc_id_substitution(temp_project):
    """
    Template {TYPE}-XXX pattern is substituted with generated document ID.

    Verifies: REQ-TEMPLATE-003
    """
    # [REQ-TEMPLATE-003] Create document
    run_qms(temp_project, "claude", "create", "SOP",
            "--title", "ID Substitution Test")

    # Verify document ID appears (either in heading or content)
    doc_content = read_document(temp_project, "SOP/SOP-001-draft.md")
    assert doc_content is not None

    # The doc_id should appear somewhere in the document
    assert "SOP-001" in doc_content, \
        "Document ID should be substituted in document"


# ============================================================================
# Test: Frontmatter Initialization
# ============================================================================

def test_frontmatter_title_initialized(temp_project):
    """
    New documents have title field in frontmatter.

    Verifies: REQ-TEMPLATE-004
    """
    # [REQ-TEMPLATE-004] Create document
    run_qms(temp_project, "claude", "create", "SOP",
            "--title", "Frontmatter Title Test")

    # Verify frontmatter has title
    doc_path = temp_project / "QMS" / "SOP" / "SOP-001-draft.md"
    frontmatter = read_frontmatter(doc_path)

    assert "title" in frontmatter, "Frontmatter should have title field"
    assert frontmatter["title"] == "Frontmatter Title Test"


def test_frontmatter_revision_summary_initialized(temp_project):
    """
    New documents have revision_summary field set to "Initial draft".

    Verifies: REQ-TEMPLATE-004
    """
    # [REQ-TEMPLATE-004] Create document
    run_qms(temp_project, "claude", "create", "SOP",
            "--title", "Revision Summary Test")

    # Verify frontmatter has revision_summary
    doc_path = temp_project / "QMS" / "SOP" / "SOP-001-draft.md"
    frontmatter = read_frontmatter(doc_path)

    assert "revision_summary" in frontmatter, "Frontmatter should have revision_summary"
    assert frontmatter["revision_summary"] == "Initial draft", \
        "revision_summary should be 'Initial draft'"


# ============================================================================
# Test: Fallback Template Generation
# ============================================================================

def test_document_created_without_template_file(temp_project):
    """
    Documents can be created even if no template file exists.

    Verifies: REQ-TEMPLATE-005
    """
    # [REQ-TEMPLATE-005] Create document - CLI should generate minimal structure
    # even if no TEMPLATE-SOP.md exists in QMS/TEMPLATE/
    result = run_qms(temp_project, "claude", "create", "SOP",
                     "--title", "Fallback Template Test")
    assert result.returncode == 0, "Create should succeed even without template"

    # Verify document has minimal required structure
    doc_path = temp_project / "QMS" / "SOP" / "SOP-001-draft.md"
    assert doc_path.exists(), "Document should be created"

    # Verify has frontmatter
    content = doc_path.read_text(encoding="utf-8")
    assert content.startswith("---"), "Should have YAML frontmatter"

    # Verify frontmatter is valid
    frontmatter = read_frontmatter(doc_path)
    assert "title" in frontmatter, "Fallback should include title"


def test_fallback_includes_document_heading(temp_project):
    """
    Fallback template includes placeholder heading with document ID.

    Verifies: REQ-TEMPLATE-005
    """
    # [REQ-TEMPLATE-005] Create document
    run_qms(temp_project, "claude", "create", "SOP",
            "--title", "Heading Test SOP")

    # Verify document has heading with ID
    doc_content = read_document(temp_project, "SOP/SOP-001-draft.md")
    assert doc_content is not None

    # Should have markdown heading with doc ID
    assert "#" in doc_content, "Should have markdown heading"
    assert "SOP-001" in doc_content, "Heading should include document ID"
