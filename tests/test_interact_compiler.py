"""
Test Interaction System — Compilation Engine

Qualification tests for REQ-INT-016 and the strikethrough rendering
portion of REQ-INT-009.

Created as part of CR-091: Interaction System Engine
"""
import sys
from pathlib import Path

import pytest

# Add qms-cli to path for imports
QMS_CLI_DIR = Path(__file__).parent.parent
if str(QMS_CLI_DIR) not in sys.path:
    sys.path.insert(0, str(QMS_CLI_DIR))

from interact_source import create_source, add_response
from interact_compiler import compile_document, compile_preview, _render_response


# =============================================================================
# Test templates
# =============================================================================

SIMPLE_TEMPLATE = """\
---
title: Simple Test
---

<!-- @template: SIMPLE | version: 1 | start: first -->

# Test Document

<!-- @prompt: first | next: second -->

Enter first value:

**First:** {{first}}

<!-- @prompt: second | next: end -->

Enter second value:

**Second:** {{second}}

<!-- @end -->
"""

LOOP_TEMPLATE = """\
---
title: Loop Test
---

<!-- @template: LOOP | version: 1 | start: preamble -->

# Loop Document

<!-- @prompt: preamble | next: step_action -->

Preamble guidance.

**Preamble:** {{preamble}}

<!-- @loop: steps -->

### Step {{_n}}

<!-- @prompt: step_action | next: step_result -->

Action guidance.

**{{step_action}}**

<!-- @prompt: step_result | next: more_steps | commit: true -->

Result guidance.

```
{{step_result}}
```

<!-- @gate: more_steps | type: yesno | yes: step_action | no: summary -->

More steps?

<!-- @end-loop: steps -->

<!-- @prompt: summary | next: end -->

Summary guidance.

**Summary:** {{summary}}

<!-- @end -->
"""

METADATA_TEMPLATE = """\
---
title: '{{title}}'
---

<!-- @template: META | version: 1 | start: p1 -->

# {{vr_id}}: {{title}}

<!-- @prompt: p1 | next: end -->

Guidance:

| Parent | Value |
|--------|-------|
| {{parent_doc_id}} | {{p1}} |

<!-- @end -->
"""


# =============================================================================
# REQ-INT-016: Compilation
# =============================================================================

class TestCompilation:
    """REQ-INT-016: The system shall compile source files into markdown by
    stripping tags and guidance, substituting placeholders with active
    responses, and rendering amendment trails."""

    def test_strips_template_header(self):
        """Compilation strips @template header comments."""
        source = create_source("T", "SIMPLE", 1, "__end__")
        add_response(source, "first", "val1", "claude")
        add_response(source, "second", "val2", "claude")
        result = compile_document(source, SIMPLE_TEMPLATE)
        assert "@template" not in result

    def test_strips_prompt_tags(self):
        """Compilation strips @prompt tag comments."""
        source = create_source("T", "SIMPLE", 1, "__end__")
        add_response(source, "first", "val1", "claude")
        add_response(source, "second", "val2", "claude")
        result = compile_document(source, SIMPLE_TEMPLATE)
        assert "@prompt" not in result

    def test_strips_guidance_text(self):
        """Compilation strips guidance text between tags and placeholders."""
        source = create_source("T", "SIMPLE", 1, "__end__")
        add_response(source, "first", "val1", "claude")
        add_response(source, "second", "val2", "claude")
        result = compile_document(source, SIMPLE_TEMPLATE)
        assert "Enter first value" not in result
        assert "Enter second value" not in result

    def test_substitutes_placeholders(self):
        """Compilation substitutes {{id}} with active responses."""
        source = create_source("T", "SIMPLE", 1, "__end__")
        add_response(source, "first", "Response One", "claude")
        add_response(source, "second", "Response Two", "claude")
        result = compile_document(source, SIMPLE_TEMPLATE)
        assert "Response One" in result
        assert "Response Two" in result

    def test_preserves_markdown_structure(self):
        """Compilation preserves headings and markdown structure."""
        source = create_source("T", "SIMPLE", 1, "__end__")
        add_response(source, "first", "val1", "claude")
        add_response(source, "second", "val2", "claude")
        result = compile_document(source, SIMPLE_TEMPLATE)
        assert "# Test Document" in result

    def test_substitutes_metadata(self):
        """Compilation substitutes metadata values in placeholders."""
        source = create_source("T", "META", 1, "__end__",
                               metadata={"parent_doc_id": "CR-091",
                                          "vr_id": "CR-091-VR-001",
                                          "title": "Test VR"})
        add_response(source, "p1", "evidence data", "claude")
        result = compile_document(source, METADATA_TEMPLATE)
        assert "CR-091" in result
        assert "CR-091-VR-001" in result
        assert "Test VR" in result

    def test_empty_responses_leave_blank(self):
        """Unfilled placeholders compile to empty strings."""
        source = create_source("T", "SIMPLE", 1, "first")
        # No responses — all placeholders should be empty
        result = compile_document(source, SIMPLE_TEMPLATE)
        assert "{{first}}" not in result
        assert "{{second}}" not in result


# =============================================================================
# REQ-INT-009 (strikethrough rendering in compilation)
# =============================================================================

class TestAmendmentRendering:
    """REQ-INT-009: Compiled output renders superseded entries with strikethrough."""

    def test_single_response_no_strikethrough(self):
        """Single response renders normally (no strikethrough)."""
        entries = [{"value": "correct", "author": "claude", "timestamp": "2026-02-21T12:00:00Z"}]
        rendered = _render_response("p1", entries)
        assert "correct" in rendered
        assert "~~" not in rendered

    def test_amendment_shows_strikethrough_on_original(self):
        """Amended responses show strikethrough on superseded entries."""
        entries = [
            {"value": "wrong", "author": "claude", "timestamp": "2026-02-21T12:00:00Z"},
            {"value": "right", "author": "claude", "timestamp": "2026-02-21T12:01:00Z",
             "reason": "typo"},
        ]
        rendered = _render_response("p1", entries)
        assert "~~wrong~~" in rendered
        assert "right" in rendered
        # Active entry should NOT be struck through
        assert "~~right~~" not in rendered

    def test_multiple_amendments_all_superseded_struck(self):
        """Multiple amendments show strikethrough on all superseded entries."""
        entries = [
            {"value": "v1", "author": "claude", "timestamp": "2026-02-21T12:00:00Z"},
            {"value": "v2", "author": "claude", "timestamp": "2026-02-21T12:01:00Z",
             "reason": "fix 1"},
            {"value": "v3", "author": "claude", "timestamp": "2026-02-21T12:02:00Z",
             "reason": "fix 2"},
        ]
        rendered = _render_response("p1", entries)
        assert "~~v1~~" in rendered
        assert "~~v2~~" in rendered
        assert "~~v3~~" not in rendered  # Active — not struck

    def test_attribution_includes_author(self):
        """Rendered response includes author attribution."""
        entries = [{"value": "val", "author": "claude", "timestamp": "2026-02-21T12:00:00Z"}]
        rendered = _render_response("p1", entries)
        assert "claude" in rendered

    def test_attribution_includes_timestamp(self):
        """Rendered response includes timestamp."""
        entries = [{"value": "val", "author": "claude", "timestamp": "2026-02-21T12:00:00Z"}]
        rendered = _render_response("p1", entries)
        assert "2026-02-21" in rendered

    def test_attribution_includes_commit_hash(self):
        """Rendered response includes commit hash when present."""
        entries = [{"value": "val", "author": "claude",
                    "timestamp": "2026-02-21T12:00:00Z", "commit": "abc1234"}]
        rendered = _render_response("p1", entries)
        assert "abc1234" in rendered

    def test_attribution_includes_amendment_reason(self):
        """Amendment entries include the reason in attribution."""
        entries = [
            {"value": "old", "author": "claude", "timestamp": "2026-02-21T12:00:00Z"},
            {"value": "new", "author": "claude", "timestamp": "2026-02-21T12:01:00Z",
             "reason": "corrected measurement"},
        ]
        rendered = _render_response("p1", entries)
        assert "corrected measurement" in rendered

    def test_compiled_document_shows_amendments(self):
        """Full compilation renders amendment trail correctly."""
        source = create_source("T", "SIMPLE", 1, "__end__")
        add_response(source, "first", "wrong", "claude")
        add_response(source, "first", "right", "claude", reason="correction")
        add_response(source, "second", "val2", "claude")

        result = compile_document(source, SIMPLE_TEMPLATE)
        assert "~~wrong~~" in result
        assert "right" in result


# =============================================================================
# REQ-INT-013: --compile preview
# =============================================================================

class TestCompilePreview:
    """REQ-INT-013: --compile outputs compiled markdown preview to stdout."""

    def test_compile_preview_matches_compile_document(self):
        """compile_preview produces same output as compile_document."""
        source = create_source("T", "SIMPLE", 1, "__end__")
        add_response(source, "first", "v1", "claude")
        add_response(source, "second", "v2", "claude")

        preview = compile_preview(source, SIMPLE_TEMPLATE)
        compiled = compile_document(source, SIMPLE_TEMPLATE)
        assert preview == compiled


# =============================================================================
# Real template compilation
# =============================================================================

class TestRealTemplateCompilation:
    """Integration: compile using the actual TEMPLATE-VR v3."""

    @pytest.fixture
    def vr_template(self):
        template_path = QMS_CLI_DIR / "seed" / "templates" / "TEMPLATE-VR.md"
        if not template_path.exists():
            pytest.skip("TEMPLATE-VR.md not found")
        return template_path.read_text(encoding="utf-8")

    def test_vr_compiles_with_filled_responses(self, vr_template):
        """VR template compiles with all prompts filled."""
        source = create_source("CR-091-VR-001", "VR", 3, "__end__",
                               metadata={
                                   "parent_doc_id": "CR-091",
                                   "vr_id": "CR-091-VR-001",
                                   "title": "Test Verification",
                               })
        # Fill non-loop prompts
        add_response(source, "related_eis", "EI-3, EI-4", "claude")
        add_response(source, "date", "2026-02-21", "claude")
        add_response(source, "objective", "Verify interaction engine", "claude")
        add_response(source, "pre_conditions", "Branch cr-091 checked out", "claude")
        # Fill one loop iteration
        add_response(source, "step_instructions.1", "Run parser tests", "claude")
        add_response(source, "step_expected.1", "All tests pass", "claude")
        add_response(source, "step_actual.1", "24 passed", "claude", commit="abc1234")
        add_response(source, "step_outcome.1", "Pass", "claude")
        # Fill summary
        add_response(source, "summary_outcome", "Pass", "claude")
        add_response(source, "summary_narrative", "All tests passed.", "claude")
        add_response(source, "performer", "claude", "claude")
        add_response(source, "performed_date", "2026-02-21", "claude")

        # Set loop state so compiler knows about iterations
        source["loops"]["steps"] = {"iterations": 1, "closed": True, "reopenings": []}

        result = compile_document(source, vr_template)

        # Verify content appears
        assert "CR-091-VR-001" in result
        assert "EI-3, EI-4" in result
        assert "Verify interaction engine" in result
        assert "Run parser tests" in result
        assert "24 passed" in result

        # Verify tags and guidance are stripped
        assert "@template" not in result
        assert "@prompt" not in result
        assert "@gate" not in result
        assert "Describe the action" not in result  # Guidance text

    def test_vr_compiles_empty_gracefully(self, vr_template):
        """VR template compiles without error even with no responses."""
        source = create_source("CR-091-VR-001", "VR", 3, "related_eis",
                               metadata={"parent_doc_id": "CR-091",
                                          "vr_id": "CR-091-VR-001",
                                          "title": "Empty VR"})
        # Should not raise
        result = compile_document(source, vr_template)
        assert "CR-091-VR-001" in result
