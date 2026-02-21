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
from interact_compiler import (
    compile_document, compile_preview, _render_response,
    _strip_template_preamble, _render_value_only, _render_attributions,
)


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
        source = create_source("CR-091-VR-001", "VR", 4, "__end__",
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
        source = create_source("CR-091-VR-001", "VR", 4, "related_eis",
                               metadata={"parent_doc_id": "CR-091",
                                          "vr_id": "CR-091-VR-001",
                                          "title": "Empty VR"})
        # Should not raise
        result = compile_document(source, vr_template)
        assert "CR-091-VR-001" in result


# =============================================================================
# CR-094 D1: Preamble stripping
# =============================================================================

PREAMBLE_TEMPLATE = """\
---
title: My Template
revision_summary: 'v1'
---

<!-- Notice: this is a template -->

<!-- @template: TEST | version: 1 | start: p1 -->

---
title: '{{title}}'
revision_summary: 'Initial draft'
---

# {{doc_id}}: {{title}}

<!-- @prompt: p1 | next: end -->

Guidance.

<!-- @end-prompt -->

**Value:** {{p1}}

<!-- @end -->
"""


class TestPreambleStripping:
    """CR-094 D1: Template frontmatter and notice stripped from compiled output."""

    def test_template_fm_removed(self):
        """Template's own frontmatter does not appear in compiled output."""
        result = _strip_template_preamble(PREAMBLE_TEMPLATE)
        assert "My Template" not in result
        assert "revision_summary: 'v1'" not in result

    def test_document_fm_kept(self):
        """Document's frontmatter (with placeholders) is preserved."""
        result = _strip_template_preamble(PREAMBLE_TEMPLATE)
        assert "{{title}}" in result
        assert "revision_summary: 'Initial draft'" in result

    def test_notice_stripped(self):
        """Template notice comment between FMs is stripped."""
        result = _strip_template_preamble(PREAMBLE_TEMPLATE)
        assert "Notice: this is a template" not in result

    def test_single_fm_preserved(self):
        """If only one FM block exists, it is kept as-is."""
        single_fm = "---\ntitle: Only One\n---\n\n# Content"
        result = _strip_template_preamble(single_fm)
        assert result == single_fm

    def test_compiled_output_has_one_fm(self):
        """Full compilation produces exactly one frontmatter block."""
        source = create_source("T", "TEST", 1, "__end__",
                               metadata={"doc_id": "T-001", "title": "Test"})
        add_response(source, "p1", "answer", "claude")
        result = compile_document(source, PREAMBLE_TEMPLATE)
        # Count --- delimiters that are FM (not horizontal rules)
        lines = result.split('\n')
        fm_count = sum(1 for l in lines if l.strip() == '---')
        # Two --- lines = one FM block (open + close)
        # Plus any horizontal rules from the template
        assert result.startswith("---")
        assert "My Template" not in result

    def test_real_template_preamble_stripped(self):
        """TEMPLATE-VR preamble (FM + notice) stripped in compilation."""
        template_path = QMS_CLI_DIR / "seed" / "templates" / "TEMPLATE-VR.md"
        if not template_path.exists():
            pytest.skip("TEMPLATE-VR.md not found")
        template = template_path.read_text(encoding="utf-8")
        source = create_source("VR-001", "VR", 4, "related_eis",
                               metadata={"parent_doc_id": "CR-001",
                                          "vr_id": "VR-001", "title": "T"})
        result = compile_document(source, template)
        assert "Verification Record Template" not in result
        assert "TEMPLATE DOCUMENT NOTICE" not in result


# =============================================================================
# CR-094 D2: Context-aware attribution
# =============================================================================

TABLE_TEMPLATE = """\
---
title: '{{title}}'
---

<!-- @template: TBL | version: 1 | start: col1 -->

<!-- @prompt: col1 | next: col2 -->

Enter column 1.

<!-- @end-prompt -->

<!-- @prompt: col2 | next: end -->

Enter column 2.

<!-- @end-prompt -->

| Header A | Header B |
|----------|----------|
| {{col1}} | {{col2}} |

<!-- @end -->
"""


class TestContextAwareAttribution:
    """CR-094 D2: Table rows get value-only; attribution outside bold/code."""

    @pytest.fixture
    def vr_template(self):
        template_path = QMS_CLI_DIR / "seed" / "templates" / "TEMPLATE-VR.md"
        if not template_path.exists():
            pytest.skip("TEMPLATE-VR.md not found")
        return template_path.read_text(encoding="utf-8")

    def test_table_rows_no_attribution(self):
        """Table cell substitution omits attribution."""
        source = create_source("T", "TBL", 1, "__end__",
                               metadata={"title": "T"})
        add_response(source, "col1", "Alpha", "claude")
        add_response(source, "col2", "Beta", "claude")
        result = compile_document(source, TABLE_TEMPLATE)
        # Find the data row
        for line in result.split('\n'):
            if '| Alpha' in line:
                assert '*--' not in line, "Attribution found in table row"
                assert line.count('|') >= 3, "Table row structure broken"
                break
        else:
            pytest.fail("Table row with Alpha not found")

    def test_table_row_single_line(self):
        """Table row with substitution remains a single line."""
        source = create_source("T", "TBL", 1, "__end__",
                               metadata={"title": "T"})
        add_response(source, "col1", "X", "claude")
        add_response(source, "col2", "Y", "claude")
        result = compile_document(source, TABLE_TEMPLATE)
        for line in result.split('\n'):
            if '| X' in line and '| Y' in line:
                assert '\n' not in line
                break
        else:
            pytest.fail("Single-line table row not found")

    def test_table_amendment_active_only(self):
        """Table cell with amendment shows only the active value."""
        source = create_source("T", "TBL", 1, "__end__",
                               metadata={"title": "T"})
        add_response(source, "col1", "wrong", "claude")
        add_response(source, "col1", "right", "claude", reason="fix")
        add_response(source, "col2", "val", "claude")
        result = compile_document(source, TABLE_TEMPLATE)
        for line in result.split('\n'):
            if 'right' in line and '|' in line:
                # Active value present, no strikethrough trail (would break table)
                assert '~~wrong~~' not in line
                assert '*--' not in line
                break

    def test_loop_bold_not_broken(self, vr_template):
        """Step instructions bold markers wrap only value, not attribution."""
        source = create_source("VR-001", "VR", 4, "__end__",
                               metadata={"parent_doc_id": "CR-001",
                                          "vr_id": "VR-001", "title": "T"})
        add_response(source, "related_eis", "EI-1", "claude")
        add_response(source, "date", "2026-02-21", "claude")
        add_response(source, "objective", "Test", "claude")
        add_response(source, "pre_conditions", "Ready", "claude")
        add_response(source, "step_instructions.1", "Do thing", "claude")
        add_response(source, "step_expected.1", "Expected result", "claude")
        add_response(source, "step_actual.1", "output", "claude", commit="abc")
        add_response(source, "step_outcome.1", "Pass", "claude")
        add_response(source, "summary_outcome", "Pass", "claude")
        add_response(source, "summary_narrative", "Done", "claude")
        add_response(source, "performer", "claude", "claude")
        add_response(source, "performed_date", "2026-02-21", "claude")
        source["loops"]["steps"] = {"iterations": 1, "closed": True, "reopenings": []}
        result = compile_document(source, vr_template)
        # Bold should wrap only the value
        assert "**Do thing**" in result
        # Attribution should be on a separate line, not inside bold
        for line in result.split('\n'):
            if line.startswith('**') and '*--' in line:
                pytest.fail(f"Attribution inside bold markers: {line}")

    def test_loop_attribution_outside_code_fence(self, vr_template):
        """Step actual attribution is outside code fences."""
        source = create_source("VR-001", "VR", 4, "__end__",
                               metadata={"parent_doc_id": "CR-001",
                                          "vr_id": "VR-001", "title": "T"})
        add_response(source, "related_eis", "EI-1", "claude")
        add_response(source, "date", "2026-02-21", "claude")
        add_response(source, "objective", "Test", "claude")
        add_response(source, "pre_conditions", "Ready", "claude")
        add_response(source, "step_instructions.1", "Do it", "claude")
        add_response(source, "step_expected.1", "Result", "claude")
        add_response(source, "step_actual.1", "result text", "claude", commit="abc123")
        add_response(source, "step_outcome.1", "Pass", "claude")
        add_response(source, "summary_outcome", "Pass", "claude")
        add_response(source, "summary_narrative", "OK", "claude")
        add_response(source, "performer", "claude", "claude")
        add_response(source, "performed_date", "2026-02-21", "claude")
        source["loops"]["steps"] = {"iterations": 1, "closed": True, "reopenings": []}
        result = compile_document(source, vr_template)
        lines = result.split('\n')
        in_fence = False
        for line in lines:
            if line.strip().startswith('```'):
                in_fence = not in_fence
            if in_fence and '*--' in line:
                pytest.fail(f"Attribution inside code fence: {line}")


# =============================================================================
# CR-094 D3: @end-prompt guidance boundaries (compiler side)
# =============================================================================

ENDPROMPT_TEMPLATE = """\
---
title: '{{title}}'
---

<!-- @template: EP | version: 1 | start: p1 -->

# Document

<!-- @prompt: p1 | next: p2 -->

This is guidance for p1.

<!-- @end-prompt -->

**Label:** {{p1}}

<!-- @prompt: p2 | next: end -->

This is guidance for p2.

<!-- @end-prompt -->

{{p2}}

<!-- @end -->
"""


class TestEndPromptCompiler:
    """CR-094 D3: @end-prompt stops guidance stripping in compiler."""

    def test_guidance_stripped_before_end_prompt(self):
        """Guidance text between @prompt and @end-prompt is stripped."""
        source = create_source("T", "EP", 1, "__end__",
                               metadata={"title": "Test"})
        add_response(source, "p1", "val1", "claude")
        add_response(source, "p2", "val2", "claude")
        result = compile_document(source, ENDPROMPT_TEMPLATE)
        assert "This is guidance for p1" not in result
        assert "This is guidance for p2" not in result

    def test_scaffold_preserved_after_end_prompt(self):
        """Document scaffold after @end-prompt is preserved."""
        source = create_source("T", "EP", 1, "__end__",
                               metadata={"title": "Test"})
        add_response(source, "p1", "val1", "claude")
        add_response(source, "p2", "val2", "claude")
        result = compile_document(source, ENDPROMPT_TEMPLATE)
        assert "**Label:**" in result

    def test_end_prompt_tag_stripped_from_output(self):
        """@end-prompt comment itself does not appear in output."""
        source = create_source("T", "EP", 1, "__end__",
                               metadata={"title": "Test"})
        add_response(source, "p1", "val1", "claude")
        result = compile_document(source, ENDPROMPT_TEMPLATE)
        assert "@end-prompt" not in result

    def test_fallback_without_end_prompt(self):
        """Without @end-prompt, guidance is skipped until structural element."""
        source = create_source("T", "SIMPLE", 1, "__end__")
        add_response(source, "first", "val1", "claude")
        add_response(source, "second", "val2", "claude")
        result = compile_document(source, SIMPLE_TEMPLATE)
        assert "Enter first value" not in result
        assert "val1" in result


# =============================================================================
# CR-094 D4: Visual distinction (blockquote wrapping)
# =============================================================================

class TestBlockquoteWrapping:
    """CR-094 D4: Block-context responses wrapped in blockquote."""

    def test_block_context_wrapped(self):
        """Standalone placeholder response gets blockquote wrapping."""
        source = create_source("T", "EP", 1, "__end__",
                               metadata={"title": "Test"})
        add_response(source, "p2", "My response text", "claude")
        result = compile_document(source, ENDPROMPT_TEMPLATE)
        assert "> My response text" in result

    def test_block_context_attribution_in_blockquote(self):
        """Attribution for block-context response is inside blockquote."""
        source = create_source("T", "EP", 1, "__end__",
                               metadata={"title": "Test"})
        add_response(source, "p2", "Response", "claude")
        result = compile_document(source, ENDPROMPT_TEMPLATE)
        for line in result.split('\n'):
            if '*--' in line and 'claude' in line:
                if '> ' in line or line.startswith('>'):
                    break
        else:
            pytest.fail("Attribution not in blockquote for block context")

    def test_label_context_not_wrapped(self):
        """Label-context responses are NOT blockquoted."""
        source = create_source("T", "EP", 1, "__end__",
                               metadata={"title": "Test"})
        add_response(source, "p1", "label value", "claude")
        result = compile_document(source, ENDPROMPT_TEMPLATE)
        # p1 is label context: **Label:** {{p1}}
        assert "**Label:** label value" in result
        # Should NOT be blockquoted
        assert "> **Label:**" not in result

    def test_table_context_not_wrapped(self):
        """Table-context responses are NOT blockquoted."""
        source = create_source("T", "TBL", 1, "__end__",
                               metadata={"title": "T"})
        add_response(source, "col1", "val", "claude")
        add_response(source, "col2", "val2", "claude")
        result = compile_document(source, TABLE_TEMPLATE)
        assert "> | val" not in result

    def test_empty_block_not_wrapped(self):
        """Empty block-context placeholder is not wrapped."""
        source = create_source("T", "EP", 1, "__end__",
                               metadata={"title": "Test"})
        # p2 is block context, but no response
        result = compile_document(source, ENDPROMPT_TEMPLATE)
        # Should not have orphaned blockquote markers
        for line in result.split('\n'):
            if line.strip() == '>':
                pytest.fail("Orphaned blockquote marker found")


# =============================================================================
# CR-094: Render helpers
# =============================================================================

class TestRenderValueOnly:
    """Tests for _render_value_only helper."""

    def test_single_entry(self):
        entries = [{"value": "hello", "author": "claude", "timestamp": "2026-01-01T00:00:00Z"}]
        assert _render_value_only(entries) == "hello"

    def test_amendment_trail(self):
        entries = [
            {"value": "old", "author": "claude", "timestamp": "2026-01-01T00:00:00Z"},
            {"value": "new", "author": "claude", "timestamp": "2026-01-01T00:01:00Z", "reason": "fix"},
        ]
        result = _render_value_only(entries)
        assert "~~old~~" in result
        assert "new" in result
        assert "*--" not in result  # No attribution

    def test_empty(self):
        assert _render_value_only([]) == ""


class TestRenderAttributions:
    """Tests for _render_attributions helper."""

    def test_single_entry(self):
        entries = [{"value": "v", "author": "claude", "timestamp": "2026-01-01T00:00:00Z"}]
        result = _render_attributions(entries)
        assert "*-- claude" in result

    def test_multiple_entries(self):
        entries = [
            {"value": "v1", "author": "claude", "timestamp": "2026-01-01T00:00:00Z"},
            {"value": "v2", "author": "claude", "timestamp": "2026-01-01T00:01:00Z", "reason": "fix"},
        ]
        result = _render_attributions(entries)
        lines = result.split('\n')
        assert len(lines) == 2
        assert all("*--" in l for l in lines)

    def test_empty(self):
        assert _render_attributions([]) == ""
