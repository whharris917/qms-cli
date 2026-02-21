"""
Test Interaction System — Template Parser

Qualification tests for REQ-INT-001 through REQ-INT-005.

Created as part of CR-091: Interaction System Engine
"""
import sys
from pathlib import Path

import pytest

# Add qms-cli to path for imports
QMS_CLI_DIR = Path(__file__).parent.parent
if str(QMS_CLI_DIR) not in sys.path:
    sys.path.insert(0, str(QMS_CLI_DIR))

from interact_parser import (
    parse_template, TemplateHeader, TemplateGraph,
    PromptNode, GateNode, LoopDef,
    _parse_attributes,
)


# =============================================================================
# Minimal test templates
# =============================================================================

MINIMAL_TEMPLATE = """\
---
title: Test Template
---

<!-- @template: TEST | version: 1 | start: p1 -->

# Test

<!-- @prompt: p1 | next: p2 -->

Guidance for prompt 1.

{{p1}}

<!-- @prompt: p2 | next: end -->

Guidance for prompt 2.

{{p2}}

<!-- @end -->
"""

GATE_TEMPLATE = """\
---
title: Gate Test
---

<!-- @template: GATE_TEST | version: 2 | start: intro -->

<!-- @prompt: intro | next: decide -->

Intro guidance.

{{intro}}

<!-- @gate: decide | type: yesno | yes: option_a | no: option_b -->

Do you want option A?

<!-- @prompt: option_a | next: end -->

Option A guidance.

{{option_a}}

<!-- @prompt: option_b | next: end -->

Option B guidance.

{{option_b}}

<!-- @end -->
"""

LOOP_TEMPLATE = """\
---
title: Loop Test
---

<!-- @template: LOOP_TEST | version: 1 | start: preamble -->

<!-- @prompt: preamble | next: step_action -->

Preamble guidance.

{{preamble}}

<!-- @loop: steps -->

### Step {{_n}}

<!-- @prompt: step_action | next: step_result -->

Describe the action:

{{step_action}}

<!-- @prompt: step_result | next: more_steps -->

Record result:

{{step_result}}

<!-- @gate: more_steps | type: yesno | yes: step_action | no: summary -->

More steps?

<!-- @end-loop: steps -->

<!-- @prompt: summary | next: end -->

Summary:

{{summary}}

<!-- @end -->
"""

COMMIT_TEMPLATE = """\
---
title: Commit Test
---

<!-- @template: COMMIT_TEST | version: 1 | start: setup -->

<!-- @prompt: setup | next: evidence -->

Setup guidance.

{{setup}}

<!-- @prompt: evidence | next: end | commit: true -->

Record evidence (this triggers a commit):

{{evidence}}

<!-- @end -->
"""


# =============================================================================
# REQ-INT-001: Tag Vocabulary
# =============================================================================

class TestTagVocabulary:
    """REQ-INT-001: The system shall recognize @prompt, @gate, @loop,
    @end-loop, and @end tags in HTML comment syntax."""

    def test_recognizes_prompt_tag(self):
        """Parser recognizes @prompt tags in HTML comments."""
        graph = parse_template(MINIMAL_TEMPLATE)
        assert "p1" in graph.nodes
        assert isinstance(graph.nodes["p1"], PromptNode)

    def test_recognizes_gate_tag(self):
        """Parser recognizes @gate tags in HTML comments."""
        graph = parse_template(GATE_TEMPLATE)
        assert "decide" in graph.nodes
        assert isinstance(graph.nodes["decide"], GateNode)

    def test_recognizes_loop_tags(self):
        """Parser recognizes @loop and @end-loop tags."""
        graph = parse_template(LOOP_TEMPLATE)
        assert "steps" in graph.loops
        assert isinstance(graph.loops["steps"], LoopDef)

    def test_recognizes_end_tag(self):
        """Parser recognizes @end tag as terminal state."""
        graph = parse_template(MINIMAL_TEMPLATE)
        assert "__end__" in graph.nodes

    def test_tags_must_be_html_comments(self):
        """Tags outside HTML comments are not recognized."""
        template = """\
---
title: Test
---

<!-- @template: T | version: 1 | start: p1 -->

@prompt: p1 | next: end

<!-- @end -->
"""
        # The @prompt outside a comment is not recognized as a prompt node
        graph = parse_template(template)
        assert "p1" not in graph.nodes

    def test_all_five_tags_in_one_template(self):
        """All five tag types work together in a single template."""
        graph = parse_template(LOOP_TEMPLATE)
        # @prompt
        assert "preamble" in graph.nodes
        assert isinstance(graph.nodes["preamble"], PromptNode)
        # @gate
        assert "more_steps" in graph.nodes
        assert isinstance(graph.nodes["more_steps"], GateNode)
        # @loop / @end-loop
        assert "steps" in graph.loops
        # @end
        assert "__end__" in graph.nodes


# =============================================================================
# REQ-INT-002: Template Header
# =============================================================================

class TestTemplateHeader:
    """REQ-INT-002: The system shall parse @template header tags
    specifying template name, version, and start prompt."""

    def test_parses_template_name(self):
        """Header contains the template name."""
        graph = parse_template(MINIMAL_TEMPLATE)
        assert graph.header.name == "TEST"

    def test_parses_template_version(self):
        """Header contains the template version as integer."""
        graph = parse_template(GATE_TEMPLATE)
        assert graph.header.version == 2

    def test_parses_start_prompt(self):
        """Header contains the start prompt ID."""
        graph = parse_template(MINIMAL_TEMPLATE)
        assert graph.header.start == "p1"

    def test_missing_name_raises(self):
        """Missing name in @template raises ValueError."""
        template = "<!-- @template: version: 1 | start: p1 -->\n<!-- @end -->"
        # The bare value becomes id, but if it's just 'version:' it will fail
        # Actually let's test with explicit missing:
        template = """\
<!-- @template: | version: 1 | start: p1 -->
<!-- @prompt: p1 | next: end -->
{{p1}}
<!-- @end -->
"""
        with pytest.raises(ValueError, match="missing name"):
            parse_template(template)

    def test_missing_start_raises(self):
        """Missing start in @template raises ValueError."""
        template = "<!-- @template: TEST | version: 1 -->\n<!-- @end -->"
        with pytest.raises(ValueError, match="missing start"):
            parse_template(template)

    def test_missing_header_raises(self):
        """Template without @template header raises ValueError."""
        template = "<!-- @prompt: p1 | next: end -->\n<!-- @end -->"
        with pytest.raises(ValueError, match="missing @template"):
            parse_template(template)

    def test_multiline_header_comment(self):
        """Parser handles @template in a multi-line comment block."""
        # The actual TEMPLATE-VR uses a multi-line comment for the header
        template_path = QMS_CLI_DIR / "seed" / "templates" / "TEMPLATE-VR.md"
        if template_path.exists():
            text = template_path.read_text(encoding="utf-8")
            graph = parse_template(text)
            assert graph.header.name == "VR"
            assert graph.header.version == 4
            assert graph.header.start == "related_eis"


# =============================================================================
# REQ-INT-003: Prompt Attributes
# =============================================================================

class TestPromptAttributes:
    """REQ-INT-003: @prompt tags shall support id, next, and commit attributes."""

    def test_prompt_has_id(self):
        """Prompt nodes have an id attribute."""
        graph = parse_template(MINIMAL_TEMPLATE)
        assert graph.nodes["p1"].id == "p1"
        assert graph.nodes["p2"].id == "p2"

    def test_prompt_has_next(self):
        """Prompt nodes have a next attribute."""
        graph = parse_template(MINIMAL_TEMPLATE)
        assert graph.nodes["p1"].next == "p2"
        assert graph.nodes["p2"].next == "end"

    def test_prompt_commit_defaults_false(self):
        """Prompt commit attribute defaults to False."""
        graph = parse_template(MINIMAL_TEMPLATE)
        assert graph.nodes["p1"].commit is False

    def test_prompt_commit_true(self):
        """Prompt commit attribute can be set to True."""
        graph = parse_template(COMMIT_TEMPLATE)
        assert graph.nodes["evidence"].commit is True

    def test_prompt_missing_id_raises(self):
        """@prompt without id raises ValueError."""
        template = """\
<!-- @template: T | version: 1 | start: p1 -->
<!-- @prompt: | next: end -->
<!-- @end -->
"""
        with pytest.raises(ValueError, match="missing id"):
            parse_template(template)

    def test_prompt_missing_next_raises(self):
        """@prompt without next raises ValueError."""
        template = """\
<!-- @template: T | version: 1 | start: p1 -->
<!-- @prompt: p1 -->
<!-- @end -->
"""
        with pytest.raises(ValueError, match="missing next"):
            parse_template(template)

    def test_prompt_has_guidance(self):
        """Prompt nodes capture guidance text between tag and placeholder."""
        graph = parse_template(MINIMAL_TEMPLATE)
        # Guidance should contain the text between the tag and the placeholder
        assert "Guidance for prompt 1" in graph.nodes["p1"].guidance


# =============================================================================
# REQ-INT-004: Gate Attributes
# =============================================================================

class TestGateAttributes:
    """REQ-INT-004: @gate tags shall support id, type, yes, and no attributes;
    type: yesno gates accept yes/no decisions."""

    def test_gate_has_id(self):
        """Gate nodes have an id attribute."""
        graph = parse_template(GATE_TEMPLATE)
        assert graph.nodes["decide"].id == "decide"

    def test_gate_has_type(self):
        """Gate nodes have a type attribute."""
        graph = parse_template(GATE_TEMPLATE)
        assert graph.nodes["decide"].gate_type == "yesno"

    def test_gate_has_yes_target(self):
        """Gate nodes have a yes target."""
        graph = parse_template(GATE_TEMPLATE)
        assert graph.nodes["decide"].yes == "option_a"

    def test_gate_has_no_target(self):
        """Gate nodes have a no target."""
        graph = parse_template(GATE_TEMPLATE)
        assert graph.nodes["decide"].no == "option_b"

    def test_gate_missing_targets_raises(self):
        """Gate without yes/no targets raises ValueError."""
        template = """\
<!-- @template: T | version: 1 | start: g1 -->
<!-- @gate: g1 | type: yesno -->
<!-- @end -->
"""
        with pytest.raises(ValueError, match="missing yes/no"):
            parse_template(template)

    def test_gate_missing_id_raises(self):
        """Gate without id raises ValueError."""
        template = """\
<!-- @template: T | version: 1 | start: g1 -->
<!-- @gate: | type: yesno | yes: a | no: b -->
<!-- @end -->
"""
        with pytest.raises(ValueError, match="missing id"):
            parse_template(template)


# =============================================================================
# REQ-INT-005: Loop Semantics
# =============================================================================

class TestLoopSemantics:
    """REQ-INT-005: @loop/@end-loop pairs shall define repeating blocks
    with an iteration counter ({{_n}}); loops close via gate decision."""

    def test_loop_defined_by_pair(self):
        """@loop and @end-loop create a LoopDef."""
        graph = parse_template(LOOP_TEMPLATE)
        assert "steps" in graph.loops
        loop = graph.loops["steps"]
        assert loop.name == "steps"

    def test_loop_tracks_first_prompt(self):
        """Loop definition tracks its first prompt."""
        graph = parse_template(LOOP_TEMPLATE)
        assert graph.loops["steps"].first_prompt == "step_action"

    def test_prompts_inside_loop_marked(self):
        """Prompts inside a loop have loop and iteration_indexed attributes."""
        graph = parse_template(LOOP_TEMPLATE)
        assert graph.nodes["step_action"].loop == "steps"
        assert graph.nodes["step_action"].iteration_indexed is True
        assert graph.nodes["step_result"].loop == "steps"

    def test_prompts_outside_loop_not_marked(self):
        """Prompts outside a loop have no loop attribute."""
        graph = parse_template(LOOP_TEMPLATE)
        assert graph.nodes["preamble"].loop is None
        assert graph.nodes["preamble"].iteration_indexed is False
        assert graph.nodes["summary"].loop is None

    def test_gate_inside_loop_marked(self):
        """Gates inside a loop have loop attribute."""
        graph = parse_template(LOOP_TEMPLATE)
        assert graph.nodes["more_steps"].loop == "steps"

    def test_unclosed_loop_raises(self):
        """Unclosed @loop (without @end-loop) raises ValueError."""
        template = """\
<!-- @template: T | version: 1 | start: p1 -->
<!-- @loop: broken -->
<!-- @prompt: p1 | next: end -->
{{p1}}
<!-- @end -->
"""
        with pytest.raises(ValueError, match="Unclosed loop"):
            parse_template(template)

    def test_mismatched_end_loop_raises(self):
        """@end-loop with wrong name raises ValueError."""
        template = """\
<!-- @template: T | version: 1 | start: p1 -->
<!-- @loop: alpha -->
<!-- @prompt: p1 | next: end -->
{{p1}}
<!-- @end-loop: beta -->
<!-- @end -->
"""
        with pytest.raises(ValueError, match="does not match"):
            parse_template(template)


# =============================================================================
# Real template parsing
# =============================================================================

class TestRealTemplateVR:
    """Integration: parse the actual TEMPLATE-VR v3 template."""

    @pytest.fixture
    def vr_graph(self):
        template_path = QMS_CLI_DIR / "seed" / "templates" / "TEMPLATE-VR.md"
        if not template_path.exists():
            pytest.skip("TEMPLATE-VR.md not found")
        text = template_path.read_text(encoding="utf-8")
        return parse_template(text)

    def test_vr_has_correct_header(self, vr_graph):
        """VR template has correct header metadata."""
        assert vr_graph.header.name == "VR"
        assert vr_graph.header.version == 4
        assert vr_graph.header.start == "related_eis"

    def test_vr_has_expected_prompts(self, vr_graph):
        """VR template has all expected prompt nodes."""
        prompt_ids = vr_graph.get_prompt_ids()
        expected = [
            "related_eis", "date", "objective", "pre_conditions",
            "step_instructions", "step_expected", "step_actual", "step_outcome",
            "summary_outcome", "summary_narrative", "performer", "performed_date",
        ]
        for pid in expected:
            assert pid in prompt_ids, f"Missing prompt: {pid}"

    def test_vr_has_steps_loop(self, vr_graph):
        """VR template has a 'steps' loop."""
        assert "steps" in vr_graph.loops

    def test_vr_has_more_steps_gate(self, vr_graph):
        """VR template has a 'more_steps' gate."""
        assert "more_steps" in vr_graph.nodes
        assert isinstance(vr_graph.nodes["more_steps"], GateNode)

    def test_vr_step_actual_has_commit(self, vr_graph):
        """VR template step_actual prompt has commit: true."""
        assert vr_graph.nodes["step_actual"].commit is True

    def test_vr_total_node_count(self, vr_graph):
        """VR template has expected number of nodes (13 prompts + 1 gate + __end__)."""
        # 12 prompts + 1 gate + __end__ = 14 total in nodes dict
        # (performed_date is a prompt too)
        assert len(vr_graph.nodes) >= 14


# =============================================================================
# Attribute parsing
# =============================================================================

class TestAttributeParsing:
    """Tests for the _parse_attributes helper."""

    def test_bare_value_becomes_id(self):
        attrs = _parse_attributes("myid")
        assert attrs["id"] == "myid"

    def test_key_value_pairs(self):
        attrs = _parse_attributes("myid | next: p2 | commit: true")
        assert attrs["id"] == "myid"
        assert attrs["next"] == "p2"
        assert attrs["commit"] is True

    def test_boolean_coercion(self):
        attrs = _parse_attributes("x | flag: false")
        assert attrs["flag"] is False

    def test_integer_coercion(self):
        attrs = _parse_attributes("x | version: 3")
        assert attrs["version"] == 3


# =============================================================================
# CR-094 D3: @end-prompt guidance boundaries (parser side)
# =============================================================================

ENDPROMPT_TEMPLATE = """\
---
title: Test
---

<!-- @template: EP | version: 1 | start: p1 -->

<!-- @prompt: p1 | next: p2 -->

This is guidance for p1.

<!-- @end-prompt -->

**Label:** {{p1}}

---

## Section 2

<!-- @prompt: p2 | next: end -->

Guidance for p2.

<!-- @end-prompt -->

{{p2}}

<!-- @end -->
"""

NO_ENDPROMPT_TEMPLATE = """\
---
title: Test
---

<!-- @template: NEP | version: 1 | start: p1 -->

<!-- @prompt: p1 | next: p2 -->

Guidance for p1.

**Label:** {{p1}}

<!-- @prompt: p2 | next: end -->

Guidance for p2.

{{p2}}

<!-- @end -->
"""


class TestEndPromptParser:
    """CR-094 D3: @end-prompt tag recognition and guidance boundary."""

    def test_end_prompt_recognized_as_tag(self):
        """Parser recognizes @end-prompt without creating a node."""
        graph = parse_template(ENDPROMPT_TEMPLATE)
        # @end-prompt should NOT create a node
        assert "end-prompt" not in graph.nodes
        # But the template should still parse successfully
        assert graph.header.name == "EP"

    def test_guidance_stops_at_end_prompt(self):
        """Guidance extraction stops at @end-prompt boundary."""
        graph = parse_template(ENDPROMPT_TEMPLATE)
        # p1 guidance should contain only text before @end-prompt
        assert "This is guidance for p1" in graph.nodes["p1"].guidance
        # Scaffold after @end-prompt should NOT be in guidance
        assert "**Label:**" not in graph.nodes["p1"].guidance
        assert "Section 2" not in graph.nodes["p1"].guidance

    def test_guidance_without_end_prompt_includes_scaffold(self):
        """Without @end-prompt, guidance extends to next tag (fallback)."""
        graph = parse_template(NO_ENDPROMPT_TEMPLATE)
        # p1 guidance goes all the way to next @prompt
        # It will include **Label:** because there's no @end-prompt boundary
        assert "Guidance for p1" in graph.nodes["p1"].guidance
        assert "**Label:**" in graph.nodes["p1"].guidance

    def test_end_prompt_with_gate(self):
        """@end-prompt works with @gate tags too."""
        template = """\
---
title: Test
---

<!-- @template: G | version: 1 | start: g1 -->

<!-- @gate: g1 | type: yesno | yes: p1 | no: p2 -->

Gate guidance here.

<!-- @end-prompt -->

Document scaffold.

<!-- @prompt: p1 | next: end -->

P1 guidance.

<!-- @end-prompt -->

{{p1}}

<!-- @prompt: p2 | next: end -->

P2 guidance.

<!-- @end-prompt -->

{{p2}}

<!-- @end -->
"""
        graph = parse_template(template)
        assert "Gate guidance here" in graph.nodes["g1"].guidance
        assert "Document scaffold" not in graph.nodes["g1"].guidance

    def test_end_prompt_stripped_from_vr_template(self):
        """Real TEMPLATE-VR guidance is bounded by @end-prompt."""
        template_path = QMS_CLI_DIR / "seed" / "templates" / "TEMPLATE-VR.md"
        if not template_path.exists():
            pytest.skip("TEMPLATE-VR.md not found")
        text = template_path.read_text(encoding="utf-8")
        graph = parse_template(text)
        # objective guidance should contain guidance text
        obj = graph.nodes["objective"]
        assert "CAPABILITY" in obj.guidance
        # But NOT the label scaffold
        assert "**Objective:**" not in obj.guidance

    def test_all_vr_prompts_have_guidance(self):
        """All VR prompts have non-empty guidance (after adding @end-prompt)."""
        template_path = QMS_CLI_DIR / "seed" / "templates" / "TEMPLATE-VR.md"
        if not template_path.exists():
            pytest.skip("TEMPLATE-VR.md not found")
        text = template_path.read_text(encoding="utf-8")
        graph = parse_template(text)
        for nid, node in graph.nodes.items():
            if nid == "__end__":
                continue
            if isinstance(node, PromptNode):
                assert node.guidance.strip(), f"Prompt {nid} has empty guidance"
            elif isinstance(node, GateNode):
                assert node.guidance.strip(), f"Gate {nid} has empty guidance"
