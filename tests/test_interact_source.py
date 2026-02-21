"""
Test Interaction System — Source Data Model

Qualification tests for REQ-INT-006 through REQ-INT-009.

Created as part of CR-091: Interaction System Engine
"""
import json
import sys
from pathlib import Path

import pytest

# Add qms-cli to path for imports
QMS_CLI_DIR = Path(__file__).parent.parent
if str(QMS_CLI_DIR) not in sys.path:
    sys.path.insert(0, str(QMS_CLI_DIR))

from interact_source import (
    create_source,
    add_response, get_active_response, get_response_entries, has_response,
    init_loop, increment_loop, get_loop_iteration, close_loop,
    is_loop_closed, reopen_loop,
    record_gate, get_gate_value,
    set_cursor, get_cursor, get_cursor_context,
    save_session, load_session, save_source, load_source,
    make_iteration_id, parse_iteration_id,
)


# =============================================================================
# REQ-INT-006: Source File Structure
# =============================================================================

class TestSourceFileStructure:
    """REQ-INT-006: Interactive documents shall produce .source.json files
    containing doc_id, template reference, cursor state, responses, loop state,
    gate decisions, and metadata."""

    def test_create_source_has_doc_id(self):
        """Source contains doc_id."""
        source = create_source("CR-091-VR-001", "VR", 3, "start")
        assert source["doc_id"] == "CR-091-VR-001"

    def test_create_source_has_template_reference(self):
        """Source contains template name and version."""
        source = create_source("CR-091-VR-001", "VR", 3, "start")
        assert source["template"] == "VR"
        assert source["template_version"] == 3

    def test_create_source_has_cursor(self):
        """Source contains cursor state."""
        source = create_source("CR-091-VR-001", "VR", 3, "first_prompt")
        assert source["cursor"] == "first_prompt"
        assert source["cursor_context"] == {}

    def test_create_source_has_responses(self):
        """Source contains empty responses dict."""
        source = create_source("CR-091-VR-001", "VR", 3, "start")
        assert source["responses"] == {}

    def test_create_source_has_loops(self):
        """Source contains empty loops dict."""
        source = create_source("CR-091-VR-001", "VR", 3, "start")
        assert source["loops"] == {}

    def test_create_source_has_gates(self):
        """Source contains empty gates dict."""
        source = create_source("CR-091-VR-001", "VR", 3, "start")
        assert source["gates"] == {}

    def test_create_source_has_metadata(self):
        """Source contains metadata."""
        meta = {"parent_doc_id": "CR-091", "title": "Test VR"}
        source = create_source("CR-091-VR-001", "VR", 3, "start", metadata=meta)
        assert source["metadata"]["parent_doc_id"] == "CR-091"
        assert source["metadata"]["title"] == "Test VR"

    def test_create_source_default_metadata(self):
        """Source has empty metadata when none provided."""
        source = create_source("CR-091-VR-001", "VR", 3, "start")
        assert source["metadata"] == {}

    def test_source_serializes_to_json(self):
        """Source can be serialized to JSON."""
        source = create_source("CR-091-VR-001", "VR", 3, "start")
        add_response(source, "p1", "test value", "claude")
        serialized = json.dumps(source)
        deserialized = json.loads(serialized)
        assert deserialized["doc_id"] == "CR-091-VR-001"
        assert "p1" in deserialized["responses"]


# =============================================================================
# REQ-INT-007: Session File Lifecycle
# =============================================================================

class TestSessionFileLifecycle:
    """REQ-INT-007: Checkout produces .interact session files; checkin moves
    to .source.json in .meta/."""

    def test_save_and_load_session(self, tmp_path):
        """Session files round-trip correctly."""
        source = create_source("TEST-VR-001", "VR", 3, "p1")
        add_response(source, "p1", "hello", "claude")

        session_path = tmp_path / "TEST-VR-001.interact"
        save_session(source, session_path)

        loaded = load_session(session_path)
        assert loaded is not None
        assert loaded["doc_id"] == "TEST-VR-001"
        assert has_response(loaded, "p1")
        assert get_active_response(loaded, "p1") == "hello"

    def test_save_and_load_source(self, tmp_path):
        """Source files round-trip correctly."""
        source = create_source("TEST-VR-001", "VR", 3, "p1")
        add_response(source, "p1", "world", "claude")

        source_path = tmp_path / "TEST-VR-001.source.json"
        save_source(source, source_path)

        loaded = load_source(source_path)
        assert loaded is not None
        assert loaded["doc_id"] == "TEST-VR-001"
        assert get_active_response(loaded, "p1") == "world"

    def test_load_nonexistent_session_returns_none(self, tmp_path):
        """Loading a nonexistent session file returns None."""
        result = load_session(tmp_path / "nonexistent.interact")
        assert result is None

    def test_load_nonexistent_source_returns_none(self, tmp_path):
        """Loading a nonexistent source file returns None."""
        result = load_source(tmp_path / "nonexistent.source.json")
        assert result is None

    def test_session_creates_parent_dirs(self, tmp_path):
        """save_session creates parent directories if needed."""
        session_path = tmp_path / "nested" / "dir" / "test.interact"
        source = create_source("X-001", "VR", 1, "p1")
        save_session(source, session_path)
        assert session_path.exists()

    def test_source_creates_parent_dirs(self, tmp_path):
        """save_source creates parent directories if needed."""
        source_path = tmp_path / "nested" / "dir" / "test.source.json"
        source = create_source("X-001", "VR", 1, "p1")
        save_source(source, source_path)
        assert source_path.exists()

    def test_session_file_is_valid_json(self, tmp_path):
        """Session file is valid JSON."""
        source = create_source("X-001", "VR", 1, "p1")
        session_path = tmp_path / "test.interact"
        save_session(source, session_path)

        content = session_path.read_text(encoding="utf-8")
        parsed = json.loads(content)
        assert parsed["doc_id"] == "X-001"


# =============================================================================
# REQ-INT-008: Append-Only Responses
# =============================================================================

class TestAppendOnlyResponses:
    """REQ-INT-008: Each response shall be stored as a list of entries
    with value, author, timestamp, and optional reason and commit fields."""

    def test_response_entry_has_value(self):
        """Response entry contains the value."""
        source = create_source("X", "VR", 1, "p1")
        entry = add_response(source, "p1", "test value", "claude")
        assert entry["value"] == "test value"

    def test_response_entry_has_author(self):
        """Response entry contains the author."""
        source = create_source("X", "VR", 1, "p1")
        entry = add_response(source, "p1", "val", "claude")
        assert entry["author"] == "claude"

    def test_response_entry_has_timestamp(self):
        """Response entry contains a timestamp."""
        source = create_source("X", "VR", 1, "p1")
        entry = add_response(source, "p1", "val", "claude")
        assert "timestamp" in entry
        assert "T" in entry["timestamp"]  # ISO format

    def test_response_entry_optional_reason(self):
        """Response entry includes reason when provided."""
        source = create_source("X", "VR", 1, "p1")
        entry = add_response(source, "p1", "val", "claude", reason="correction")
        assert entry["reason"] == "correction"

    def test_response_entry_no_reason_by_default(self):
        """Response entry omits reason when not provided."""
        source = create_source("X", "VR", 1, "p1")
        entry = add_response(source, "p1", "val", "claude")
        assert "reason" not in entry

    def test_response_entry_optional_commit(self):
        """Response entry includes commit hash when provided."""
        source = create_source("X", "VR", 1, "p1")
        entry = add_response(source, "p1", "val", "claude", commit="abc1234")
        assert entry["commit"] == "abc1234"

    def test_response_entry_no_commit_by_default(self):
        """Response entry omits commit when not provided."""
        source = create_source("X", "VR", 1, "p1")
        entry = add_response(source, "p1", "val", "claude")
        assert "commit" not in entry

    def test_responses_stored_as_list(self):
        """Responses are stored as a list of entries."""
        source = create_source("X", "VR", 1, "p1")
        add_response(source, "p1", "first", "claude")
        entries = get_response_entries(source, "p1")
        assert isinstance(entries, list)
        assert len(entries) == 1

    def test_append_only_multiple_entries(self):
        """Multiple responses append to the list (never replace)."""
        source = create_source("X", "VR", 1, "p1")
        add_response(source, "p1", "first", "claude")
        add_response(source, "p1", "second", "claude", reason="correction")

        entries = get_response_entries(source, "p1")
        assert len(entries) == 2
        assert entries[0]["value"] == "first"
        assert entries[1]["value"] == "second"

    def test_get_active_response_returns_last(self):
        """get_active_response returns the most recent entry's value."""
        source = create_source("X", "VR", 1, "p1")
        add_response(source, "p1", "first", "claude")
        add_response(source, "p1", "second", "claude", reason="amendment")
        assert get_active_response(source, "p1") == "second"

    def test_get_active_response_none_for_missing(self):
        """get_active_response returns None for unresponded prompts."""
        source = create_source("X", "VR", 1, "p1")
        assert get_active_response(source, "p1") is None

    def test_has_response_true(self):
        """has_response returns True for answered prompts."""
        source = create_source("X", "VR", 1, "p1")
        add_response(source, "p1", "val", "claude")
        assert has_response(source, "p1") is True

    def test_has_response_false(self):
        """has_response returns False for unanswered prompts."""
        source = create_source("X", "VR", 1, "p1")
        assert has_response(source, "p1") is False


# =============================================================================
# REQ-INT-009: Amendment Trail
# =============================================================================

class TestAmendmentTrail:
    """REQ-INT-009: Amendments require a reason; original entries are preserved;
    compiled output renders superseded entries with strikethrough."""

    def test_amendment_preserves_original(self):
        """Amendments preserve the original entry."""
        source = create_source("X", "VR", 1, "p1")
        add_response(source, "p1", "original", "claude")
        add_response(source, "p1", "amended", "claude", reason="typo fix")

        entries = get_response_entries(source, "p1")
        assert len(entries) == 2
        assert entries[0]["value"] == "original"
        assert entries[1]["value"] == "amended"

    def test_amendment_has_reason(self):
        """Amendment entries include a reason."""
        source = create_source("X", "VR", 1, "p1")
        add_response(source, "p1", "original", "claude")
        add_response(source, "p1", "amended", "claude", reason="wrong value")

        entries = get_response_entries(source, "p1")
        assert entries[1]["reason"] == "wrong value"

    def test_original_entry_has_no_reason(self):
        """Original (first) entry has no reason field."""
        source = create_source("X", "VR", 1, "p1")
        add_response(source, "p1", "original", "claude")
        entries = get_response_entries(source, "p1")
        assert "reason" not in entries[0]

    def test_multiple_amendments_all_preserved(self):
        """Multiple amendments all preserve history."""
        source = create_source("X", "VR", 1, "p1")
        add_response(source, "p1", "v1", "claude")
        add_response(source, "p1", "v2", "claude", reason="first fix")
        add_response(source, "p1", "v3", "claude", reason="second fix")

        entries = get_response_entries(source, "p1")
        assert len(entries) == 3
        assert [e["value"] for e in entries] == ["v1", "v2", "v3"]


# =============================================================================
# Cursor operations
# =============================================================================

class TestCursorOperations:
    """Tests for cursor state management."""

    def test_set_and_get_cursor(self):
        source = create_source("X", "VR", 1, "p1")
        set_cursor(source, "p2")
        assert get_cursor(source) == "p2"

    def test_cursor_context(self):
        source = create_source("X", "VR", 1, "p1")
        set_cursor(source, "p2", {"loop": "steps", "iteration": 1})
        ctx = get_cursor_context(source)
        assert ctx["loop"] == "steps"
        assert ctx["iteration"] == 1

    def test_cursor_context_cleared_on_set(self):
        source = create_source("X", "VR", 1, "p1")
        set_cursor(source, "p2", {"loop": "steps"})
        set_cursor(source, "p3")
        assert get_cursor_context(source) == {}


# =============================================================================
# Loop operations
# =============================================================================

class TestLoopOperations:
    """Tests for loop state management."""

    def test_init_loop(self):
        source = create_source("X", "VR", 1, "p1")
        init_loop(source, "steps")
        assert "steps" in source["loops"]
        assert source["loops"]["steps"]["iterations"] == 0

    def test_increment_loop(self):
        source = create_source("X", "VR", 1, "p1")
        n = increment_loop(source, "steps")
        assert n == 1
        n = increment_loop(source, "steps")
        assert n == 2

    def test_get_loop_iteration(self):
        source = create_source("X", "VR", 1, "p1")
        increment_loop(source, "steps")
        increment_loop(source, "steps")
        assert get_loop_iteration(source, "steps") == 2

    def test_close_loop(self):
        source = create_source("X", "VR", 1, "p1")
        init_loop(source, "steps")
        close_loop(source, "steps")
        assert is_loop_closed(source, "steps") is True

    def test_reopen_loop(self):
        source = create_source("X", "VR", 1, "p1")
        init_loop(source, "steps")
        close_loop(source, "steps")
        reopen_loop(source, "steps", "missed step", "claude")
        assert is_loop_closed(source, "steps") is False
        assert len(source["loops"]["steps"]["reopenings"]) == 1


# =============================================================================
# Gate operations
# =============================================================================

class TestGateOperations:
    """Tests for gate state management."""

    def test_record_gate(self):
        source = create_source("X", "VR", 1, "p1")
        record_gate(source, "g1", "yes")
        assert get_gate_value(source, "g1") == "yes"

    def test_gate_not_recorded(self):
        source = create_source("X", "VR", 1, "p1")
        assert get_gate_value(source, "g1") is None


# =============================================================================
# Iteration ID helpers
# =============================================================================

class TestIterationIds:
    """Tests for iteration-indexed prompt ID helpers."""

    def test_make_iteration_id(self):
        assert make_iteration_id("step_actual", 1) == "step_actual.1"
        assert make_iteration_id("step_actual", 3) == "step_actual.3"

    def test_parse_iteration_id(self):
        base, n = parse_iteration_id("step_actual.2")
        assert base == "step_actual"
        assert n == 2

    def test_parse_non_iteration_id(self):
        base, n = parse_iteration_id("related_eis")
        assert base == "related_eis"
        assert n is None
