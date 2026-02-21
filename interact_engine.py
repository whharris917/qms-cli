"""
Interaction System — Engine

Core engine managing the authoring session: cursor management, response
recording, amendment logic, loop state, gate routing, sequential enforcement,
and contextual interpolation.

REQ-INT-010 through REQ-INT-016

Created as part of CR-091: Interaction System Engine
"""

from typing import Optional

from interact_parser import TemplateGraph, PromptNode, GateNode
from interact_source import (
    add_response, get_active_response, has_response,
    set_cursor, get_cursor, get_cursor_context,
    init_loop, increment_loop, get_loop_iteration, close_loop,
    is_loop_closed, reopen_loop, record_gate, get_gate_value,
    make_iteration_id, parse_iteration_id,
)


class InteractError(Exception):
    """Error raised by the interaction engine."""
    pass


class InteractEngine:
    """
    Manages the interaction session between an author and a template.

    The engine walks the template graph using cursor state from the source.
    It enforces sequential prompt ordering, manages loop iterations, handles
    gate routing, and records responses with attribution.
    """

    def __init__(self, graph: TemplateGraph, source: dict):
        self.graph = graph
        self.source = source

    # =========================================================================
    # Status and presentation (REQ-INT-010)
    # =========================================================================

    def get_current_prompt_info(self) -> dict:
        """Get information about the current prompt for display."""
        cursor = get_cursor(self.source)
        ctx = get_cursor_context(self.source)

        if cursor == '__end__' or cursor == 'end':
            return {
                "status": "complete",
                "message": "All prompts have been answered. Document is ready for checkin.",
            }

        # Resolve the actual node
        node = self._resolve_node(cursor)
        if node is None:
            return {
                "status": "error",
                "message": f"Unknown prompt: {cursor}",
            }

        # Build display ID (with iteration suffix if in a loop)
        display_id = self._get_display_id(cursor)

        info = {
            "status": "awaiting_response",
            "prompt_id": display_id,
            "raw_id": cursor,
        }

        if isinstance(node, PromptNode):
            info["guidance"] = self._interpolate(node.guidance)
            info["commit"] = node.commit
            if node.default is not None:
                info["default"] = self._resolve_default(node.default)
        elif isinstance(node, GateNode):
            info["guidance"] = self._interpolate(node.guidance)
            info["type"] = node.gate_type

        if ctx.get("goto_return"):
            info["mode"] = "amendment"
            info["return_to"] = ctx["goto_return"]

        if ctx.get("loop"):
            info["loop"] = ctx["loop"]
            info["iteration"] = ctx.get("iteration", 0)

        return info

    def get_progress(self) -> list:
        """Get progress report: all prompts with fill status (REQ-INT-013)."""
        items = []
        # Walk the graph from start, collecting all known prompt IDs
        visited = set()
        self._walk_progress(self.graph.header.start, visited, items)
        return items

    # =========================================================================
    # Response handling (REQ-INT-011, REQ-INT-014)
    # =========================================================================

    def respond(
        self,
        value: str,
        author: str,
        reason: Optional[str] = None,
        commit_hash: Optional[str] = None,
    ) -> dict:
        """
        Record a response to the current prompt.

        Returns a result dict with: prompt_id, entry, next_prompt_info.

        Raises InteractError if:
        - Document is already complete
        - Current node is a gate (use respond_gate instead)
        - Amendment without reason
        """
        cursor = get_cursor(self.source)
        ctx = get_cursor_context(self.source)

        if cursor == '__end__' or cursor == 'end':
            raise InteractError("Document is complete. No more prompts to answer.")

        node = self._resolve_node(cursor)
        if node is None:
            raise InteractError(f"Unknown prompt: {cursor}")

        if isinstance(node, GateNode):
            raise InteractError(
                f"Current prompt '{cursor}' is a gate. Use yes/no response."
            )

        # REQ-INT-014: Sequential enforcement
        display_id = self._get_display_id(cursor)

        # Check if this is an amendment (goto mode)
        is_amendment = bool(ctx.get("goto_return"))
        if is_amendment and not reason:
            raise InteractError("Amendments require a reason (--reason).")

        # Record response
        entry = add_response(
            self.source, display_id, value, author,
            reason=reason, commit=commit_hash,
        )

        # Advance cursor
        if is_amendment:
            # Return to the position we were at before the goto
            return_to = ctx["goto_return"]
            return_ctx = ctx.get("goto_return_ctx", {})
            set_cursor(self.source, return_to, return_ctx)
        else:
            self._advance_cursor(node)

        return {
            "prompt_id": display_id,
            "entry": entry,
            "next": self.get_current_prompt_info(),
        }

    def respond_gate(self, value: str, author: str) -> dict:
        """
        Record a gate decision (yes/no).

        Returns result dict with: gate_id, decision, next_prompt_info.
        """
        cursor = get_cursor(self.source)
        ctx = get_cursor_context(self.source)

        node = self._resolve_node(cursor)
        if not isinstance(node, GateNode):
            raise InteractError(f"Current prompt '{cursor}' is not a gate.")

        value_lower = value.lower().strip()
        if value_lower not in ("yes", "no"):
            raise InteractError(f"Gate expects 'yes' or 'no', got '{value}'")

        # Build display ID for the gate
        display_id = self._get_display_id(cursor)

        # Record gate decision
        record_gate(self.source, display_id, value_lower)

        # Route based on decision
        if value_lower == "yes":
            next_id = node.yes
        else:
            next_id = node.no

        # Handle loop closure
        if node.loop and value_lower == "no":
            close_loop(self.source, node.loop)

        # Advance cursor
        self._advance_to(next_id, node)

        return {
            "gate_id": display_id,
            "decision": value_lower,
            "next": self.get_current_prompt_info(),
        }

    # =========================================================================
    # Navigation (REQ-INT-012)
    # =========================================================================

    def goto(self, prompt_id: str, reason: str) -> dict:
        """
        Navigate to a previously-completed prompt for amendment.

        Saves current position for return after amendment.
        """
        if not reason:
            raise InteractError("goto requires a reason.")

        # Verify the target prompt has been answered
        if not has_response(self.source, prompt_id):
            raise InteractError(f"Prompt '{prompt_id}' has not been answered yet.")

        # Save return position
        current_cursor = get_cursor(self.source)
        current_ctx = get_cursor_context(self.source)

        # Parse the target to find the base node
        base_id, iteration = parse_iteration_id(prompt_id)
        node = self.graph.get_node(base_id)
        if node is None:
            raise InteractError(f"Unknown prompt: {base_id}")

        new_ctx = {
            "goto_return": current_cursor,
            "goto_return_ctx": current_ctx,
        }
        if iteration is not None and node.loop:
            new_ctx["loop"] = node.loop
            new_ctx["iteration"] = iteration

        set_cursor(self.source, base_id, new_ctx)

        return {
            "mode": "amendment",
            "target": prompt_id,
            "current_value": get_active_response(self.source, prompt_id),
            "prompt_info": self.get_current_prompt_info(),
        }

    def cancel_goto(self) -> dict:
        """Cancel an active goto and return to the previous position."""
        ctx = get_cursor_context(self.source)
        if not ctx.get("goto_return"):
            raise InteractError("No active goto to cancel.")

        return_to = ctx["goto_return"]
        return_ctx = ctx.get("goto_return_ctx", {})
        set_cursor(self.source, return_to, return_ctx)

        return {
            "cancelled": True,
            "returned_to": return_to,
            "prompt_info": self.get_current_prompt_info(),
        }

    def reopen_loop_cmd(self, loop_name: str, reason: str, author: str) -> dict:
        """Reopen a closed loop for additional iterations."""
        if not reason:
            raise InteractError("reopen requires a reason.")

        if loop_name not in self.source.get("loops", {}):
            raise InteractError(f"Unknown loop: {loop_name}")

        if not is_loop_closed(self.source, loop_name):
            raise InteractError(f"Loop '{loop_name}' is not closed.")

        loop_def = self.graph.loops.get(loop_name)
        if not loop_def:
            raise InteractError(f"Loop '{loop_name}' not found in template.")

        # Save current cursor for return
        current_cursor = get_cursor(self.source)
        current_ctx = get_cursor_context(self.source)

        # Reopen the loop
        reopen_loop(self.source, loop_name, reason, author)

        # Start a new iteration
        iteration = increment_loop(self.source, loop_name)

        # Move cursor to first prompt in loop
        first_prompt = loop_def.first_prompt
        set_cursor(self.source, first_prompt, {
            "loop": loop_name,
            "iteration": iteration,
            "reopen_return": current_cursor,
            "reopen_return_ctx": current_ctx,
        })

        return {
            "reopened": loop_name,
            "iteration": iteration,
            "prompt_info": self.get_current_prompt_info(),
        }

    # =========================================================================
    # Internal cursor management
    # =========================================================================

    def _resolve_node(self, cursor: str):
        """Resolve cursor to a template node."""
        if cursor == '__end__' or cursor == 'end':
            return self.graph.get_node('__end__')
        return self.graph.get_node(cursor)

    def _get_display_id(self, cursor: str) -> str:
        """Build the display ID, adding iteration suffix if in a loop."""
        node = self._resolve_node(cursor)
        if node and node.iteration_indexed:
            ctx = get_cursor_context(self.source)
            iteration = ctx.get("iteration", 0)
            if iteration > 0:
                return make_iteration_id(cursor, iteration)
        return cursor

    def _advance_cursor(self, node) -> None:
        """Advance cursor to the next node after responding."""
        if isinstance(node, PromptNode):
            self._advance_to(node.next, node)

    def _advance_to(self, next_id: str, from_node) -> None:
        """Move cursor to target, handling loop entry."""
        ctx = get_cursor_context(self.source)

        if next_id == 'end' or next_id == '__end__':
            # Check if we need to return from a reopen
            if ctx.get("reopen_return"):
                return_to = ctx["reopen_return"]
                return_ctx = ctx.get("reopen_return_ctx", {})
                set_cursor(self.source, return_to, return_ctx)
                return
            set_cursor(self.source, '__end__')
            return

        next_node = self.graph.get_node(next_id)
        if next_node is None:
            set_cursor(self.source, '__end__')
            return

        # If entering a loop prompt, ensure iteration tracking
        new_ctx = {}
        if next_node.loop:
            loop_name = next_node.loop
            init_loop(self.source, loop_name)

            # Check if this is the first prompt in the loop (entering new iteration)
            loop_def = self.graph.loops.get(loop_name)
            if loop_def and loop_def.first_prompt == next_id:
                # Starting a new iteration
                iteration = increment_loop(self.source, loop_name)
                new_ctx = {"loop": loop_name, "iteration": iteration}
            else:
                # Continuing current iteration
                current_iter = get_loop_iteration(self.source, loop_name)
                new_ctx = {"loop": loop_name, "iteration": current_iter}

            # Preserve reopen return if active
            if ctx.get("reopen_return"):
                new_ctx["reopen_return"] = ctx["reopen_return"]
                new_ctx["reopen_return_ctx"] = ctx.get("reopen_return_ctx", {})
        elif from_node and getattr(from_node, 'loop', None):
            # Leaving a loop — check for reopen return
            if ctx.get("reopen_return"):
                return_to = ctx["reopen_return"]
                return_ctx = ctx.get("reopen_return_ctx", {})
                set_cursor(self.source, return_to, return_ctx)
                return

        set_cursor(self.source, next_id, new_ctx)

    def _resolve_default(self, default_value) -> str:
        """Resolve a default value (e.g., 'today', 'current_user')."""
        if default_value == "today":
            from datetime import date
            return str(date.today())
        if default_value == "current_user":
            return self.source.get("metadata", {}).get("author", "unknown")
        return str(default_value)

    # =========================================================================
    # Contextual interpolation (REQ-INT-015)
    # =========================================================================

    def _interpolate(self, text: str) -> str:
        """Replace {{id}} placeholders with known response values."""
        import re

        def replace_match(m):
            ref_id = m.group(1)
            # Check for special variables
            if ref_id == '_n':
                ctx = get_cursor_context(self.source)
                return str(ctx.get("iteration", ""))
            # Check metadata
            metadata = self.source.get("metadata", {})
            if ref_id in metadata:
                return str(metadata[ref_id])
            # Check responses
            value = get_active_response(self.source, ref_id)
            if value is not None:
                return value
            # Check iteration-indexed responses
            ctx = get_cursor_context(self.source)
            if ctx.get("iteration"):
                iter_id = make_iteration_id(ref_id, ctx["iteration"])
                value = get_active_response(self.source, iter_id)
                if value is not None:
                    return value
            return m.group(0)  # Leave unresolved

        return re.sub(r'\{\{(\w+)\}\}', replace_match, text)

    # =========================================================================
    # Progress (REQ-INT-013)
    # =========================================================================

    def _walk_progress(self, node_id: str, visited: set, items: list) -> None:
        """Walk the graph collecting progress info."""
        if node_id in visited or node_id == '__end__' or node_id == 'end':
            return
        visited.add(node_id)

        node = self.graph.get_node(node_id)
        if node is None:
            return

        if isinstance(node, PromptNode):
            # For loop prompts, show all iterations
            if node.iteration_indexed:
                loop_name = node.loop
                iterations = get_loop_iteration(self.source, loop_name)
                for i in range(1, iterations + 1):
                    iter_id = make_iteration_id(node_id, i)
                    filled = has_response(self.source, iter_id)
                    items.append({
                        "id": iter_id,
                        "type": "prompt",
                        "filled": filled,
                        "commit": node.commit,
                        "loop": loop_name,
                        "iteration": i,
                    })
                # Check if current prompt matches (unfilled current iteration)
                cursor = get_cursor(self.source)
                if cursor == node_id and iterations > 0:
                    pass  # Already captured above
            else:
                filled = has_response(self.source, node_id)
                items.append({
                    "id": node_id,
                    "type": "prompt",
                    "filled": filled,
                    "commit": node.commit,
                })

            self._walk_progress(node.next, visited, items)

        elif isinstance(node, GateNode):
            items.append({
                "id": node_id,
                "type": "gate",
                "filled": node_id in self.source.get("gates", {})
                    or any(k.startswith(node_id + ".") for k in self.source.get("gates", {})),
            })
            # Walk both branches
            self._walk_progress(node.yes, visited, items)
            self._walk_progress(node.no, visited, items)
