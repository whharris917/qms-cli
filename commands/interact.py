"""
QMS Interact Command

Interactive document authoring via template-driven prompting.

REQ-INT-010: Entry point
REQ-INT-011: Response flags
REQ-INT-012: Navigation flags
REQ-INT-013: Query flags
REQ-INT-020: Engine-managed commits
REQ-INT-021: Commit staging scope

Created as part of CR-091: Interaction System Engine
Updated by CR-097: VR compilation rendering fixes (commit message format)
"""
import subprocess
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from registry import CommandRegistry
from qms_paths import PROJECT_ROOT, get_doc_type, get_workspace_path
from qms_auth import get_current_user, check_permission, verify_user_identity
from qms_meta import read_meta

from interact_parser import parse_template, PromptNode, GateNode
from interact_source import (
    load_session, save_session, get_cursor,
)
from interact_engine import InteractEngine, InteractError
from interact_compiler import compile_preview


def _get_session_path(user: str, doc_id: str) -> Path:
    """Get the .interact session file path for a user."""
    workspace_dir = get_workspace_path(user, doc_id).parent
    return workspace_dir / f"{doc_id}.interact"


def _load_template_for_doc(doc_id: str) -> str:
    """Load the interactive template for a document type."""
    doc_type = get_doc_type(doc_id)
    # Currently only VR is interactive
    if doc_type != "VR":
        raise InteractError(f"Document type '{doc_type}' does not support interactive authoring.")

    # Load the template from seed
    template_path = Path(__file__).parent.parent / "seed" / "templates" / f"TEMPLATE-{doc_type}.md"
    if not template_path.exists():
        raise InteractError(f"Template not found: {template_path}")
    return template_path.read_text(encoding="utf-8")


def _format_prompt_display(info: dict) -> str:
    """Format prompt info for terminal display."""
    lines = []

    if info.get("status") == "complete":
        lines.append("Document is COMPLETE. All prompts answered.")
        lines.append("Run `qms checkin` to compile and check in.")
        return '\n'.join(lines)

    if info.get("status") == "error":
        return f"Error: {info.get('message', 'Unknown error')}"

    prompt_id = info.get("prompt_id", "?")
    lines.append(f"--- Prompt: {prompt_id} ---")

    if info.get("mode") == "amendment":
        lines.append(f"[AMENDMENT MODE — return to {info.get('return_to', '?')} after response]")

    if info.get("loop"):
        lines.append(f"[Loop: {info['loop']}, Iteration: {info.get('iteration', '?')}]")

    if info.get("guidance"):
        lines.append("")
        lines.append(info["guidance"])

    if info.get("commit"):
        lines.append("")
        lines.append("[This prompt triggers an engine-managed commit]")

    if info.get("type") == "yesno":
        lines.append("")
        lines.append("Respond with: yes or no")

    lines.append("")
    lines.append("---")
    lines.append(f"  qms interact {info.get('doc_id', 'DOC_ID')} --respond \"your response\"")

    return '\n'.join(lines)


def _format_progress(items: list) -> str:
    """Format progress report for terminal display."""
    lines = ["Progress:"]
    for item in items:
        marker = "[x]" if item.get("filled") else "[ ]"
        suffix = ""
        if item.get("commit"):
            suffix += " (commit)"
        if item.get("loop"):
            suffix += f" [{item['loop']}.{item.get('iteration', '?')}]"
        lines.append(f"  {marker} {item['id']}{suffix}")
    return '\n'.join(lines)


def _do_engine_commit(doc_id: str, prompt_id: str) -> str:
    """
    Perform an engine-managed git commit (REQ-INT-020, REQ-INT-021).

    Stages changes in the project working tree, commits with system message,
    returns the commit hash.
    """
    if PROJECT_ROOT is None:
        return ""

    commit_msg = f"[QMS] auto-commit | {doc_id} | {prompt_id} | Evidence capture during VR execution"

    try:
        # Stage all changes in working tree (REQ-INT-021)
        subprocess.run(
            ["git", "add", "-A"],
            cwd=str(PROJECT_ROOT),
            capture_output=True, text=True, check=True,
        )

        # Check if there's anything to commit
        result = subprocess.run(
            ["git", "diff", "--cached", "--quiet"],
            cwd=str(PROJECT_ROOT),
            capture_output=True, text=True,
        )
        if result.returncode == 0:
            # Nothing staged — skip commit but don't error
            return ""

        # Commit
        result = subprocess.run(
            ["git", "commit", "-m", commit_msg],
            cwd=str(PROJECT_ROOT),
            capture_output=True, text=True, check=True,
        )

        # Get the commit hash
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=str(PROJECT_ROOT),
            capture_output=True, text=True, check=True,
        )
        return result.stdout.strip()[:7]  # Short hash

    except subprocess.CalledProcessError:
        return ""


@CommandRegistry.register(
    name="interact",
    help="Interactive document authoring",
    requires_doc_id=True,
    doc_id_help="Document ID",
    arguments=[
        {"flags": ["--respond"], "help": "Response value", "nargs": "?", "default": None},
        {"flags": ["--file"], "help": "Read response from file"},
        {"flags": ["--reason"], "help": "Reason for amendment or loop reopen"},
        {"flags": ["--goto"], "help": "Navigate to a prompt for amendment"},
        {"flags": ["--cancel-goto"], "help": "Cancel goto and return", "action": "store_true"},
        {"flags": ["--reopen"], "help": "Reopen a closed loop"},
        {"flags": ["--progress"], "help": "Show progress", "action": "store_true"},
        {"flags": ["--compile"], "help": "Preview compiled output", "action": "store_true"},
    ],
)
def cmd_interact(args) -> int:
    """Interactive document authoring command."""
    doc_id = args.doc_id
    user = get_current_user(args)

    if not verify_user_identity(user):
        return 1

    allowed, error = check_permission(user, "checkout")
    if not allowed:
        print(error)
        return 1

    # Verify document exists and is checked out
    doc_type = get_doc_type(doc_id)
    meta = read_meta(doc_id, doc_type)
    if not meta:
        print(f"Error: Document not found: {doc_id}")
        return 1

    if not meta.get("checked_out"):
        print(f"Error: {doc_id} is not checked out. Run `qms checkout {doc_id}` first.")
        return 1

    if meta.get("responsible_user") != user:
        print(f"Error: {doc_id} is checked out by {meta.get('responsible_user', 'unknown')}")
        return 1

    # Load session file
    session_path = _get_session_path(user, doc_id)
    source = load_session(session_path)
    if source is None:
        print(f"Error: No interact session found for {doc_id}.")
        print(f"This document may not be interactive, or checkout may not have created a session.")
        return 1

    try:
        # Load template and build engine
        template_text = _load_template_for_doc(doc_id)
        graph = parse_template(template_text)
        engine = InteractEngine(graph, source)

        # Dispatch based on flags
        respond_value = getattr(args, 'respond', None)
        file_path = getattr(args, 'file', None)
        reason = getattr(args, 'reason', None)
        goto_target = getattr(args, 'goto', None)
        cancel_goto = getattr(args, 'cancel_goto', False)
        reopen_target = getattr(args, 'reopen', None)
        show_progress = getattr(args, 'progress', False)
        show_compile = getattr(args, 'compile', False)

        if show_progress:
            # REQ-INT-013: --progress
            items = engine.get_progress()
            print(_format_progress(items))
            return 0

        if show_compile:
            # REQ-INT-013: --compile (preview only)
            output = compile_preview(source, template_text)
            print(output)
            return 0

        if cancel_goto:
            # REQ-INT-012: --cancel-goto
            result = engine.cancel_goto()
            save_session(source, session_path)
            print(f"Goto cancelled. Returned to: {result['returned_to']}")
            print()
            print(_format_prompt_display(result['prompt_info']))
            return 0

        if goto_target:
            # REQ-INT-012: --goto
            if not reason:
                print("Error: --goto requires --reason")
                return 1
            result = engine.goto(goto_target, reason)
            save_session(source, session_path)
            print(f"Navigated to: {result['target']}")
            print(f"Current value: {result['current_value']}")
            print()
            print(_format_prompt_display(result['prompt_info']))
            return 0

        if reopen_target:
            # REQ-INT-012: --reopen
            if not reason:
                print("Error: --reopen requires --reason")
                return 1
            result = engine.reopen_loop_cmd(reopen_target, reason, user)
            save_session(source, session_path)
            print(f"Reopened loop: {result['reopened']}, iteration: {result['iteration']}")
            print()
            print(_format_prompt_display(result['prompt_info']))
            return 0

        if respond_value is not None or file_path:
            # REQ-INT-011: --respond
            if file_path:
                # --respond --file path
                fp = Path(file_path)
                if not fp.exists():
                    print(f"Error: File not found: {file_path}")
                    return 1
                value = fp.read_text(encoding="utf-8").strip()
            else:
                value = respond_value

            if not value:
                print("Error: Response value is empty.")
                return 1

            # Check if current prompt is a gate
            cursor = get_cursor(source)
            node = graph.get_node(cursor)

            if isinstance(node, GateNode):
                result = engine.respond_gate(value, user)
                save_session(source, session_path)
                print(f"Gate: {result['gate_id']} = {result['decision']}")
                print()
                print(_format_prompt_display(result['next']))
                return 0

            # Check if this prompt triggers a commit (REQ-INT-020)
            commit_hash = None
            if isinstance(node, PromptNode) and node.commit:
                ctx = source.get("cursor_context", {})
                display_id = cursor
                if ctx.get("iteration"):
                    from interact_source import make_iteration_id
                    display_id = make_iteration_id(cursor, ctx["iteration"])
                commit_hash = _do_engine_commit(doc_id, display_id)

            result = engine.respond(value, user, reason=reason, commit_hash=commit_hash)
            save_session(source, session_path)

            print(f"Recorded: {result['prompt_id']}")
            entry = result['entry']
            if entry.get('commit'):
                print(f"Commit: {entry['commit']}")
            print()
            print(_format_prompt_display(result['next']))
            return 0

        # Default: show status and current prompt (REQ-INT-010)
        info = engine.get_current_prompt_info()
        info['doc_id'] = doc_id
        print(f"Document: {doc_id}")
        print(f"Template: {source.get('template', '?')} v{source.get('template_version', '?')}")
        print()
        print(_format_prompt_display(info))
        return 0

    except InteractError as e:
        print(f"Error: {e}")
        return 1
    except Exception as e:
        print(f"Error: {e}")
        return 1
