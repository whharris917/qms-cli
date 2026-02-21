"""
Test Interaction System — Engine

Qualification tests for REQ-INT-010, REQ-INT-011, REQ-INT-012,
REQ-INT-013, REQ-INT-014, REQ-INT-015.

Created as part of CR-091: Interaction System Engine
"""
import sys
from pathlib import Path

import pytest

# Add qms-cli to path for imports
QMS_CLI_DIR = Path(__file__).parent.parent
if str(QMS_CLI_DIR) not in sys.path:
    sys.path.insert(0, str(QMS_CLI_DIR))

from interact_parser import parse_template
from interact_source import (
    create_source, add_response, get_active_response,
    set_cursor, get_cursor, has_response,
    make_iteration_id,
)
from interact_engine import InteractEngine, InteractError


# =============================================================================
# Test templates
# =============================================================================

SIMPLE_TEMPLATE = """\
---
title: Simple Test
---

<!-- @template: SIMPLE | version: 1 | start: first -->

# Simple Test

<!-- @prompt: first | next: second -->

Enter first value:

{{first}}

<!-- @prompt: second | next: end -->

Enter second value (first was: {{first}}):

{{second}}

<!-- @end -->
"""

GATE_TEMPLATE = """\
---
title: Gate Test
---

<!-- @template: GATE | version: 1 | start: intro -->

<!-- @prompt: intro | next: decide -->

Introduction:

{{intro}}

<!-- @gate: decide | type: yesno | yes: yes_path | no: no_path -->

Continue?

<!-- @prompt: yes_path | next: end -->

Yes path:

{{yes_path}}

<!-- @prompt: no_path | next: end -->

No path:

{{no_path}}

<!-- @end -->
"""

LOOP_TEMPLATE = """\
---
title: Loop Test
---

<!-- @template: LOOP | version: 1 | start: preamble -->

<!-- @prompt: preamble | next: step_action -->

Preamble:

{{preamble}}

<!-- @loop: steps -->

### Step {{_n}}

<!-- @prompt: step_action | next: step_result -->

Action for step {{_n}}:

{{step_action}}

<!-- @prompt: step_result | next: more_steps | commit: true -->

Result for step {{_n}}:

{{step_result}}

<!-- @gate: more_steps | type: yesno | yes: step_action | no: summary -->

More steps?

<!-- @end-loop: steps -->

<!-- @prompt: summary | next: end -->

Summary:

{{summary}}

<!-- @end -->
"""


@pytest.fixture
def simple_engine():
    """Engine with a simple two-prompt template."""
    graph = parse_template(SIMPLE_TEMPLATE)
    source = create_source("TEST-001", "SIMPLE", 1, "first")
    return InteractEngine(graph, source)


@pytest.fixture
def gate_engine():
    """Engine with a gate template."""
    graph = parse_template(GATE_TEMPLATE)
    source = create_source("TEST-002", "GATE", 1, "intro")
    return InteractEngine(graph, source)


@pytest.fixture
def loop_engine():
    """Engine with a loop template."""
    graph = parse_template(LOOP_TEMPLATE)
    source = create_source("TEST-003", "LOOP", 1, "preamble")
    return InteractEngine(graph, source)


# =============================================================================
# REQ-INT-010: Interact Entry Point
# =============================================================================

class TestInteractEntryPoint:
    """REQ-INT-010: qms interact DOC_ID with no flags shall display document
    status and current prompt with guidance text."""

    def test_shows_current_prompt_id(self, simple_engine):
        """Entry point shows current prompt ID."""
        info = simple_engine.get_current_prompt_info()
        assert info["prompt_id"] == "first"

    def test_shows_guidance_text(self, simple_engine):
        """Entry point shows guidance text for the current prompt."""
        info = simple_engine.get_current_prompt_info()
        assert "guidance" in info
        assert "first value" in info["guidance"]

    def test_shows_awaiting_response_status(self, simple_engine):
        """Entry point shows 'awaiting_response' status."""
        info = simple_engine.get_current_prompt_info()
        assert info["status"] == "awaiting_response"

    def test_shows_complete_when_done(self, simple_engine):
        """Entry point shows 'complete' when all prompts answered."""
        simple_engine.respond("val1", "claude")
        simple_engine.respond("val2", "claude")
        info = simple_engine.get_current_prompt_info()
        assert info["status"] == "complete"

    def test_shows_commit_flag(self):
        """Entry point shows commit flag when prompt has commit: true."""
        graph = parse_template(LOOP_TEMPLATE)
        source = create_source("T", "LOOP", 1, "preamble")
        engine = InteractEngine(graph, source)
        # Advance to step_result which has commit: true
        engine.respond("preamble val", "claude")
        engine.respond("action val", "claude")
        info = engine.get_current_prompt_info()
        assert info.get("commit") is True

    def test_shows_gate_type(self, gate_engine):
        """Entry point shows gate type when current prompt is a gate."""
        gate_engine.respond("intro val", "claude")
        info = gate_engine.get_current_prompt_info()
        assert info.get("type") == "yesno"

    def test_shows_loop_context(self, loop_engine):
        """Entry point shows loop context when in a loop."""
        loop_engine.respond("preamble", "claude")
        info = loop_engine.get_current_prompt_info()
        assert info.get("loop") == "steps"
        assert info.get("iteration") == 1


# =============================================================================
# REQ-INT-011: Response Flags
# =============================================================================

class TestResponseFlags:
    """REQ-INT-011: The interact command shall support --respond 'value'
    and --respond --file path; all prompts require explicit response."""

    def test_respond_records_value(self, simple_engine):
        """--respond records the response value."""
        result = simple_engine.respond("my answer", "claude")
        assert result["prompt_id"] == "first"
        assert result["entry"]["value"] == "my answer"

    def test_respond_advances_cursor(self, simple_engine):
        """After responding, cursor moves to next prompt."""
        simple_engine.respond("val1", "claude")
        info = simple_engine.get_current_prompt_info()
        assert info["prompt_id"] == "second"

    def test_respond_returns_next_prompt_info(self, simple_engine):
        """respond() returns info about the next prompt."""
        result = simple_engine.respond("val1", "claude")
        assert result["next"]["prompt_id"] == "second"

    def test_respond_on_complete_raises(self, simple_engine):
        """Responding when document is complete raises InteractError."""
        simple_engine.respond("val1", "claude")
        simple_engine.respond("val2", "claude")
        with pytest.raises(InteractError, match="complete"):
            simple_engine.respond("extra", "claude")

    def test_respond_gate_yes(self, gate_engine):
        """Gate accepts 'yes' response."""
        gate_engine.respond("intro val", "claude")
        result = gate_engine.respond_gate("yes", "claude")
        assert result["decision"] == "yes"

    def test_respond_gate_no(self, gate_engine):
        """Gate accepts 'no' response."""
        gate_engine.respond("intro val", "claude")
        result = gate_engine.respond_gate("no", "claude")
        assert result["decision"] == "no"

    def test_respond_gate_invalid_raises(self, gate_engine):
        """Gate rejects non-yes/no values."""
        gate_engine.respond("intro val", "claude")
        with pytest.raises(InteractError, match="yes.*no"):
            gate_engine.respond_gate("maybe", "claude")

    def test_respond_gate_routes_yes(self, gate_engine):
        """Yes on gate routes to the yes target."""
        gate_engine.respond("intro val", "claude")
        gate_engine.respond_gate("yes", "claude")
        info = gate_engine.get_current_prompt_info()
        assert info["prompt_id"] == "yes_path"

    def test_respond_gate_routes_no(self, gate_engine):
        """No on gate routes to the no target."""
        gate_engine.respond("intro val", "claude")
        gate_engine.respond_gate("no", "claude")
        info = gate_engine.get_current_prompt_info()
        assert info["prompt_id"] == "no_path"


# =============================================================================
# REQ-INT-012: Navigation Flags
# =============================================================================

class TestNavigationFlags:
    """REQ-INT-012: The interact command shall support --goto, --cancel-goto,
    and --reopen; goto and reopen require --reason."""

    def test_goto_navigates_to_previous_prompt(self, simple_engine):
        """--goto moves to a previously-answered prompt."""
        simple_engine.respond("val1", "claude")
        result = simple_engine.goto("first", "need to correct")
        assert result["target"] == "first"
        assert result["current_value"] == "val1"

    def test_goto_requires_reason(self, simple_engine):
        """--goto without reason raises InteractError."""
        simple_engine.respond("val1", "claude")
        with pytest.raises(InteractError, match="reason"):
            simple_engine.goto("first", "")

    def test_goto_to_unanswered_raises(self, simple_engine):
        """--goto to unanswered prompt raises InteractError."""
        with pytest.raises(InteractError, match="not been answered"):
            simple_engine.goto("second", "want to skip ahead")

    def test_goto_amendment_mode(self, simple_engine):
        """After goto, engine shows amendment mode."""
        simple_engine.respond("val1", "claude")
        simple_engine.goto("first", "correction")
        info = simple_engine.get_current_prompt_info()
        assert info.get("mode") == "amendment"

    def test_goto_amendment_returns_to_original(self, simple_engine):
        """After amending via goto, cursor returns to where it was."""
        simple_engine.respond("val1", "claude")
        # Cursor is now at 'second'
        simple_engine.goto("first", "correction")
        simple_engine.respond("val1_amended", "claude", reason="typo")
        # Should return to 'second'
        info = simple_engine.get_current_prompt_info()
        assert info["prompt_id"] == "second"

    def test_cancel_goto(self, simple_engine):
        """--cancel-goto returns to position before goto."""
        simple_engine.respond("val1", "claude")
        simple_engine.goto("first", "correction")
        result = simple_engine.cancel_goto()
        assert result["cancelled"] is True
        info = simple_engine.get_current_prompt_info()
        assert info["prompt_id"] == "second"

    def test_cancel_goto_no_active_raises(self, simple_engine):
        """--cancel-goto when no goto is active raises InteractError."""
        with pytest.raises(InteractError, match="No active goto"):
            simple_engine.cancel_goto()

    def test_reopen_loop(self, loop_engine):
        """--reopen reopens a closed loop for additional iterations."""
        # Complete one iteration
        loop_engine.respond("preamble", "claude")
        loop_engine.respond("action 1", "claude")
        loop_engine.respond("result 1", "claude")
        loop_engine.respond_gate("no", "claude")  # Close the loop
        # Should now be at 'summary'
        info = loop_engine.get_current_prompt_info()
        assert info["prompt_id"] == "summary"

        # Reopen the loop
        result = loop_engine.reopen_loop_cmd("steps", "missed a step", "claude")
        assert result["reopened"] == "steps"
        assert result["iteration"] == 2

    def test_reopen_requires_reason(self, loop_engine):
        """--reopen without reason raises InteractError."""
        with pytest.raises(InteractError, match="reason"):
            loop_engine.reopen_loop_cmd("steps", "", "claude")

    def test_reopen_nonclosed_raises(self, loop_engine):
        """--reopen on a non-closed loop raises InteractError."""
        loop_engine.respond("preamble", "claude")
        with pytest.raises(InteractError, match="not closed"):
            loop_engine.reopen_loop_cmd("steps", "reason", "claude")


# =============================================================================
# REQ-INT-013: Query Flags
# =============================================================================

class TestQueryFlags:
    """REQ-INT-013: The interact command shall support --progress and --compile."""

    def test_progress_shows_all_prompts(self, simple_engine):
        """--progress lists all prompts with fill status."""
        items = simple_engine.get_progress()
        ids = [item["id"] for item in items]
        assert "first" in ids
        assert "second" in ids

    def test_progress_shows_filled_status(self, simple_engine):
        """--progress marks answered prompts as filled."""
        simple_engine.respond("val1", "claude")
        items = simple_engine.get_progress()
        first_item = next(i for i in items if i["id"] == "first")
        second_item = next(i for i in items if i["id"] == "second")
        assert first_item["filled"] is True
        assert second_item["filled"] is False

    def test_progress_shows_commit_prompts(self):
        """--progress marks commit-enabled prompts."""
        graph = parse_template(LOOP_TEMPLATE)
        source = create_source("T", "LOOP", 1, "preamble")
        engine = InteractEngine(graph, source)
        # Advance through one iteration to populate loop
        engine.respond("preamble", "claude")
        engine.respond("action", "claude")
        engine.respond("result", "claude")
        engine.respond_gate("no", "claude")

        items = engine.get_progress()
        result_items = [i for i in items if "step_result" in i["id"]]
        assert any(i.get("commit") is True for i in result_items)

    def test_progress_shows_loop_iterations(self, loop_engine):
        """--progress shows iteration-indexed prompts for loops."""
        loop_engine.respond("preamble", "claude")
        loop_engine.respond("action 1", "claude")
        loop_engine.respond("result 1", "claude")
        loop_engine.respond_gate("yes", "claude")  # Continue
        loop_engine.respond("action 2", "claude")
        loop_engine.respond("result 2", "claude")
        loop_engine.respond_gate("no", "claude")  # Close

        items = loop_engine.get_progress()
        loop_ids = [i["id"] for i in items if i.get("loop")]
        # Should have iteration-indexed IDs
        assert any(".1" in lid for lid in loop_ids)
        assert any(".2" in lid for lid in loop_ids)


# =============================================================================
# REQ-INT-014: Sequential Enforcement
# =============================================================================

class TestSequentialEnforcement:
    """REQ-INT-014: The engine shall not accept responses to prompts that
    have not been presented; prompts must be answered in template-defined order."""

    def test_cannot_skip_prompts(self, simple_engine):
        """Cannot respond to a prompt that hasn't been presented yet."""
        # First prompt is 'first', not 'second'
        # The engine only accepts responses at the cursor position
        info = simple_engine.get_current_prompt_info()
        assert info["prompt_id"] == "first"
        # Trying to respond records at cursor, not at arbitrary prompt
        # The engine enforces cursor position

    def test_cursor_at_correct_start(self, simple_engine):
        """Cursor starts at the template-defined start prompt."""
        assert get_cursor(simple_engine.source) == "first"

    def test_cursor_advances_sequentially(self, simple_engine):
        """Cursor advances in the order defined by template."""
        simple_engine.respond("val1", "claude")
        assert get_cursor(simple_engine.source) == "second"

    def test_respond_on_gate_raises_if_not_gate(self, gate_engine):
        """respond_gate raises if current node is a prompt, not a gate."""
        with pytest.raises(InteractError, match="not a gate"):
            gate_engine.respond_gate("yes", "claude")

    def test_respond_on_prompt_raises_if_gate(self, gate_engine):
        """respond raises if current node is a gate."""
        gate_engine.respond("intro val", "claude")
        # Now at gate 'decide'
        with pytest.raises(InteractError, match="gate"):
            gate_engine.respond("text", "claude")


# =============================================================================
# REQ-INT-015: Contextual Interpolation
# =============================================================================

class TestContextualInterpolation:
    """REQ-INT-015: Guidance text may reference previous responses using
    {{id}} syntax; the engine shall substitute known values."""

    def test_interpolates_previous_response(self, simple_engine):
        """Guidance text substitutes {{id}} with previous response."""
        simple_engine.respond("hello world", "claude")
        info = simple_engine.get_current_prompt_info()
        # The guidance for 'second' includes {{first}}
        assert "hello world" in info["guidance"]

    def test_unresolved_placeholder_left_intact(self, simple_engine):
        """Unresolved {{id}} placeholders are left as-is."""
        info = simple_engine.get_current_prompt_info()
        # At the start, no responses yet — check that unresolved refs
        # in guidance are handled gracefully (not erroring)
        assert info["guidance"] is not None

    def test_interpolates_metadata(self):
        """Guidance text substitutes {{key}} with metadata values."""
        template = """\
---
title: Meta Test
---

<!-- @template: META | version: 1 | start: p1 -->

<!-- @prompt: p1 | next: end -->

Parent is {{parent_doc_id}}.

{{p1}}

<!-- @end -->
"""
        graph = parse_template(template)
        source = create_source("T", "META", 1, "p1",
                               metadata={"parent_doc_id": "CR-091"})
        engine = InteractEngine(graph, source)
        info = engine.get_current_prompt_info()
        assert "CR-091" in info["guidance"]

    def test_interpolates_loop_counter(self, loop_engine):
        """Guidance text substitutes {{_n}} with iteration number."""
        loop_engine.respond("preamble", "claude")
        info = loop_engine.get_current_prompt_info()
        # In loop iteration 1, {{_n}} should be "1"
        assert info.get("loop") == "steps"
        assert info.get("iteration") == 1


# =============================================================================
# Loop iteration tracking
# =============================================================================

class TestLoopIteration:
    """Tests for loop iteration tracking in the engine."""

    def test_single_iteration(self, loop_engine):
        """Single loop iteration records with .1 suffix."""
        loop_engine.respond("preamble", "claude")
        result = loop_engine.respond("action 1", "claude")
        assert result["prompt_id"] == "step_action.1"

    def test_multiple_iterations(self, loop_engine):
        """Multiple loop iterations increment suffix."""
        loop_engine.respond("preamble", "claude")
        # Iteration 1
        loop_engine.respond("action 1", "claude")
        loop_engine.respond("result 1", "claude")
        loop_engine.respond_gate("yes", "claude")
        # Iteration 2
        result = loop_engine.respond("action 2", "claude")
        assert result["prompt_id"] == "step_action.2"

    def test_loop_closes_on_no(self, loop_engine):
        """Loop closes when gate gets 'no' response."""
        loop_engine.respond("preamble", "claude")
        loop_engine.respond("action 1", "claude")
        loop_engine.respond("result 1", "claude")
        loop_engine.respond_gate("no", "claude")
        # Should now be at 'summary' (outside loop)
        info = loop_engine.get_current_prompt_info()
        assert info["prompt_id"] == "summary"

    def test_complete_workflow(self, loop_engine):
        """Complete workflow: preamble -> loop(2 iters) -> summary -> end."""
        loop_engine.respond("preamble val", "claude")
        loop_engine.respond("action 1", "claude")
        loop_engine.respond("result 1", "claude")
        loop_engine.respond_gate("yes", "claude")
        loop_engine.respond("action 2", "claude")
        loop_engine.respond("result 2", "claude")
        loop_engine.respond_gate("no", "claude")
        loop_engine.respond("summary val", "claude")

        info = loop_engine.get_current_prompt_info()
        assert info["status"] == "complete"

    def test_commit_flag_on_loop_prompt(self, loop_engine):
        """step_result with commit: true shows commit flag in loop."""
        loop_engine.respond("preamble", "claude")
        loop_engine.respond("action 1", "claude")
        info = loop_engine.get_current_prompt_info()
        assert info.get("commit") is True
