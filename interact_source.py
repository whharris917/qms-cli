"""
Interaction System — Source Data Model

Manages .interact session files and .source.json permanent storage.
The source file is the authoritative record of all prompt responses,
amendments, and metadata for an interactive document.

REQ-INT-006: Source file structure
REQ-INT-007: Session file lifecycle
REQ-INT-008: Append-only responses
REQ-INT-009: Amendment trail

Created as part of CR-091: Interaction System Engine
"""

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional


# =============================================================================
# Source file structure (REQ-INT-006)
# =============================================================================

def create_source(
    doc_id: str,
    template_name: str,
    template_version: int,
    start_prompt: str,
    metadata: Optional[dict] = None,
) -> dict:
    """Create a new empty source data structure."""
    return {
        "doc_id": doc_id,
        "template": template_name,
        "template_version": template_version,
        "cursor": start_prompt,
        "cursor_context": {},
        "metadata": metadata or {},
        "responses": {},
        "loops": {},
        "gates": {},
    }


# =============================================================================
# Response operations (REQ-INT-008, REQ-INT-009)
# =============================================================================

def add_response(
    source: dict,
    prompt_id: str,
    value: str,
    author: str,
    reason: Optional[str] = None,
    commit: Optional[str] = None,
) -> dict:
    """
    Append a response entry to a prompt.

    For initial responses, creates the list. For amendments, appends.
    Responses are append-only — entries are never replaced or deleted.
    """
    entry = {
        "value": value,
        "author": author,
        "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }
    if reason:
        entry["reason"] = reason
    if commit:
        entry["commit"] = commit

    if prompt_id not in source["responses"]:
        source["responses"][prompt_id] = []

    source["responses"][prompt_id].append(entry)
    return entry


def get_active_response(source: dict, prompt_id: str) -> Optional[str]:
    """Get the active (most recent) response value for a prompt."""
    entries = source["responses"].get(prompt_id, [])
    if not entries:
        return None
    return entries[-1]["value"]


def get_response_entries(source: dict, prompt_id: str) -> list:
    """Get all response entries for a prompt (full history)."""
    return source["responses"].get(prompt_id, [])


def has_response(source: dict, prompt_id: str) -> bool:
    """Check if a prompt has any response."""
    return bool(source["responses"].get(prompt_id))


# =============================================================================
# Loop operations (REQ-INT-005)
# =============================================================================

def init_loop(source: dict, loop_name: str) -> None:
    """Initialize loop tracking if not already present."""
    if loop_name not in source["loops"]:
        source["loops"][loop_name] = {
            "iterations": 0,
            "closed": False,
            "reopenings": [],
        }


def increment_loop(source: dict, loop_name: str) -> int:
    """Increment loop iteration counter and return new count."""
    init_loop(source, loop_name)
    source["loops"][loop_name]["iterations"] += 1
    return source["loops"][loop_name]["iterations"]


def get_loop_iteration(source: dict, loop_name: str) -> int:
    """Get current iteration number for a loop."""
    loop = source["loops"].get(loop_name, {})
    return loop.get("iterations", 0)


def close_loop(source: dict, loop_name: str) -> None:
    """Mark a loop as closed."""
    init_loop(source, loop_name)
    source["loops"][loop_name]["closed"] = True


def is_loop_closed(source: dict, loop_name: str) -> bool:
    """Check if a loop is closed."""
    loop = source["loops"].get(loop_name, {})
    return loop.get("closed", False)


def reopen_loop(source: dict, loop_name: str, reason: str, author: str) -> None:
    """Reopen a closed loop for additional iterations."""
    init_loop(source, loop_name)
    source["loops"][loop_name]["closed"] = False
    source["loops"][loop_name]["reopenings"].append({
        "reason": reason,
        "author": author,
        "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    })


# =============================================================================
# Gate operations
# =============================================================================

def record_gate(source: dict, gate_id: str, value: str) -> None:
    """Record a gate decision."""
    source["gates"][gate_id] = {
        "value": value,
        "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }


def get_gate_value(source: dict, gate_id: str) -> Optional[str]:
    """Get a gate decision value."""
    gate = source["gates"].get(gate_id, {})
    return gate.get("value")


# =============================================================================
# Cursor operations
# =============================================================================

def set_cursor(source: dict, prompt_id: str, context: Optional[dict] = None) -> None:
    """Update the cursor position."""
    source["cursor"] = prompt_id
    source["cursor_context"] = context or {}


def get_cursor(source: dict) -> str:
    """Get the current cursor position."""
    return source.get("cursor", "")


def get_cursor_context(source: dict) -> dict:
    """Get the cursor context (loop name, iteration, etc.)."""
    return source.get("cursor_context", {})


# =============================================================================
# File I/O (REQ-INT-007)
# =============================================================================

def save_session(source: dict, session_path: Path) -> None:
    """Save source data to a .interact session file in workspace."""
    session_path.parent.mkdir(parents=True, exist_ok=True)
    with open(session_path, "w", encoding="utf-8") as f:
        json.dump(source, f, indent=2, ensure_ascii=False)


def load_session(session_path: Path) -> Optional[dict]:
    """Load source data from a .interact session file."""
    if not session_path.exists():
        return None
    with open(session_path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_source(source: dict, source_path: Path) -> None:
    """Save source data to a .source.json permanent file in .meta/."""
    source_path.parent.mkdir(parents=True, exist_ok=True)
    with open(source_path, "w", encoding="utf-8") as f:
        json.dump(source, f, indent=2, ensure_ascii=False)


def load_source(source_path: Path) -> Optional[dict]:
    """Load source data from a .source.json permanent file."""
    if not source_path.exists():
        return None
    with open(source_path, "r", encoding="utf-8") as f:
        return json.load(f)


# =============================================================================
# Iteration-indexed prompt IDs
# =============================================================================

def make_iteration_id(base_id: str, iteration: int) -> str:
    """Create an iteration-indexed prompt ID: base.N"""
    return f"{base_id}.{iteration}"


def parse_iteration_id(prompt_id: str) -> tuple:
    """Parse an iteration-indexed ID into (base, iteration). Returns (id, None) if not indexed."""
    if '.' in prompt_id:
        parts = prompt_id.rsplit('.', 1)
        if parts[1].isdigit():
            return parts[0], int(parts[1])
    return prompt_id, None
