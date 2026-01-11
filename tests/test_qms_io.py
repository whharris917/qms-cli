"""
Unit tests for QMS CLI I/O functions.

Tests cover:
- parse_frontmatter(): Parse YAML frontmatter from markdown
- serialize_frontmatter(): Convert frontmatter dict and body back to markdown
- read_document(): Read and parse a document file
- write_document(): Write a document with frontmatter
- filter_author_frontmatter(): Extract only author-maintained fields
"""
import pytest
from pathlib import Path


class TestParseFrontmatter:
    """Tests for parse_frontmatter() function."""

    def test_basic_frontmatter(self, qms_module):
        """Should parse basic YAML frontmatter."""
        content = '''---
title: Test Document
revision_summary: Initial draft
---

# Body content
'''
        fm, body = qms_module.parse_frontmatter(content)
        assert fm["title"] == "Test Document"
        assert fm["revision_summary"] == "Initial draft"
        assert "# Body content" in body

    def test_no_frontmatter(self, qms_module):
        """Should return empty dict when no frontmatter present."""
        content = "# Just a heading\n\nSome content."
        fm, body = qms_module.parse_frontmatter(content)
        assert fm == {}
        assert body == content

    def test_incomplete_frontmatter(self, qms_module):
        """Should handle incomplete frontmatter (missing closing ---)."""
        content = "---\ntitle: Test\nNo closing delimiter"
        fm, body = qms_module.parse_frontmatter(content)
        assert fm == {}
        assert body == content

    def test_empty_frontmatter(self, qms_module):
        """Should handle empty frontmatter block."""
        content = "---\n---\n\n# Body"
        fm, body = qms_module.parse_frontmatter(content)
        assert fm == {}
        assert "# Body" in body

    def test_multiline_values(self, qms_module):
        """Should handle multiline YAML values."""
        content = '''---
title: Test
revision_summary: >
  This is a long
  multiline summary
---

Body here.
'''
        fm, body = qms_module.parse_frontmatter(content)
        assert fm["title"] == "Test"
        assert "multiline" in fm["revision_summary"]

    def test_strips_leading_newlines_from_body(self, qms_module):
        """Should strip leading newlines from body."""
        content = "---\ntitle: Test\n---\n\n\n# Body"
        fm, body = qms_module.parse_frontmatter(content)
        assert body.startswith("# Body")


class TestSerializeFrontmatter:
    """Tests for serialize_frontmatter() function."""

    def test_basic_serialization(self, qms_module):
        """Should serialize frontmatter and body to markdown format."""
        fm = {"title": "Test", "revision_summary": "Draft"}
        body = "# Content\n\nBody text."
        result = qms_module.serialize_frontmatter(fm, body)

        assert result.startswith("---\n")
        assert "title: Test" in result
        assert "---\n\n# Content" in result

    def test_roundtrip(self, qms_module):
        """parse -> serialize should preserve data."""
        original = '''---
title: Test Document
revision_summary: Initial draft
---

# Content

Body text here.
'''
        fm, body = qms_module.parse_frontmatter(original)
        result = qms_module.serialize_frontmatter(fm, body)

        # Re-parse to verify
        fm2, body2 = qms_module.parse_frontmatter(result)
        assert fm2["title"] == fm["title"]
        assert fm2["revision_summary"] == fm["revision_summary"]
        assert "Body text here" in body2


class TestReadDocument:
    """Tests for read_document() function."""

    def test_reads_existing_file(self, qms_module, temp_project):
        """Should read and parse an existing document."""
        doc_path = temp_project / "test_doc.md"
        doc_path.write_text('''---
title: Test
---

Body content.
''')
        fm, body = qms_module.read_document(doc_path)
        assert fm["title"] == "Test"
        assert "Body content" in body

    def test_raises_on_missing_file(self, qms_module, temp_project):
        """Should raise FileNotFoundError for missing files."""
        with pytest.raises(FileNotFoundError):
            qms_module.read_document(temp_project / "nonexistent.md")


class TestWriteDocument:
    """Tests for write_document() function."""

    def test_writes_with_frontmatter(self, qms_module, temp_project):
        """Should write document with proper frontmatter format."""
        doc_path = temp_project / "output.md"
        fm = {"title": "New Doc", "revision_summary": "Created"}
        body = "# New Document\n\nContent here."

        qms_module.write_document(doc_path, fm, body)

        content = doc_path.read_text()
        assert content.startswith("---\n")
        assert "title: New Doc" in content
        assert "# New Document" in content

    def test_creates_parent_directories(self, qms_module, temp_project):
        """Should create parent directories if they don't exist."""
        doc_path = temp_project / "deep" / "nested" / "path" / "doc.md"
        fm = {"title": "Nested"}
        body = "Content"

        qms_module.write_document(doc_path, fm, body)

        assert doc_path.exists()
        assert "Nested" in doc_path.read_text()

    def test_overwrites_existing(self, qms_module, temp_project):
        """Should overwrite existing file content."""
        doc_path = temp_project / "existing.md"
        doc_path.write_text("Old content")

        qms_module.write_document(doc_path, {"title": "New"}, "New body")

        content = doc_path.read_text()
        assert "Old content" not in content
        assert "New body" in content


class TestFilterAuthorFrontmatter:
    """Tests for filter_author_frontmatter() function."""

    def test_keeps_title_and_revision_summary(self, qms_module):
        """Should keep only title and revision_summary fields."""
        fm = {
            "title": "Test",
            "revision_summary": "Draft",
            "version": "1.0",
            "status": "EFFECTIVE",
            "responsible_user": "claude"
        }
        filtered = qms_module.filter_author_frontmatter(fm)

        assert filtered["title"] == "Test"
        assert filtered["revision_summary"] == "Draft"
        assert "version" not in filtered
        assert "status" not in filtered
        assert "responsible_user" not in filtered

    def test_empty_frontmatter(self, qms_module):
        """Should handle empty frontmatter."""
        filtered = qms_module.filter_author_frontmatter({})
        assert filtered == {}

    def test_missing_author_fields(self, qms_module):
        """Should handle frontmatter without author fields."""
        fm = {"version": "1.0", "status": "DRAFT"}
        filtered = qms_module.filter_author_frontmatter(fm)
        assert filtered == {}
