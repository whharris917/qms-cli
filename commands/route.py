"""
QMS Route Command

Routes a document for review or approval.

Created as part of CR-026: QMS CLI Extensibility Refactoring
"""
import sys
from pathlib import Path

import yaml

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from registry import CommandRegistry
from qms_config import Status, TRANSITIONS
from qms_paths import get_doc_type, get_doc_path, get_inbox_path
from qms_auth import get_current_user, check_permission, verify_user_identity
from qms_templates import generate_review_task_content, generate_approval_task_content
from qms_meta import read_meta, write_meta, update_meta_route, check_approval_gate
from qms_audit import log_route_review, log_route_approval, log_status_change
from workflow import get_workflow_engine, Action, ExecutionPhase


@CommandRegistry.register(
    name="route",
    help="Route a document for review or approval",
    requires_doc_id=True,
    doc_id_help="Document ID to route",
    arguments=[
        {"flags": ["--review"], "help": "Route for review", "action": "store_true"},
        {"flags": ["--approval"], "help": "Route for approval", "action": "store_true"},
        {"flags": ["--assign"], "help": "Assignees", "nargs": "+"},
        {"flags": ["--retire"], "help": "Route for retirement approval", "action": "store_true"},
    ],
)
def cmd_route(args) -> int:
    """Route a document for review or approval."""
    doc_id = args.doc_id
    user = get_current_user(args)

    if not verify_user_identity(user):
        return 1

    # Permission check (group level)
    allowed, error = check_permission(user, "route")
    if not allowed:
        print(error)
        return 1

    draft_path = get_doc_path(doc_id, draft=True)
    if not draft_path.exists():
        print(f"""
Error: No draft found for {doc_id}.

The document may not exist, or it may already be effective.
To create a new document: qms --user {user} create SOP --title "Title"
To check out an effective document for revision: qms --user {user} checkout {doc_id}
""")
        return 1

    # Get workflow state from .meta (authoritative source)
    doc_type = get_doc_type(doc_id)
    meta = read_meta(doc_id, doc_type) or {}

    # CR-036-VAR-005: Read document title from frontmatter
    doc_title = ""
    try:
        content = draft_path.read_text(encoding="utf-8")
        if content.startswith("---"):
            end_idx = content.find("---", 3)
            if end_idx > 0:
                frontmatter = yaml.safe_load(content[3:end_idx])
                doc_title = frontmatter.get("title", "") if frontmatter else ""
    except (IOError, yaml.YAMLError):
        pass

    # Verify document is checked in (not checked out)
    if meta.get("checked_out"):
        checked_out_by = meta.get("responsible_user", "unknown")
        print(f"""
Error: {doc_id} is still checked out by {checked_out_by}.

Documents must be checked in before routing for review/approval.
The workflow operates on the QMS copy, not the workspace copy.

If you are the owner, check it in first:
  qms --user {checked_out_by} checkin {doc_id}

Then route for review:
  qms --user {checked_out_by} route {doc_id} --review
""")
        return 1

    # CR-032 Gap 2: Enforce owner-only routing per REQ-SEC-003
    owner = meta.get("responsible_user")
    if owner and owner != user:
        print(f"Error: Only the document owner can route {doc_id}")
        print(f"Current owner: {owner}")
        return 1

    current_status = Status(meta.get("status", "DRAFT"))
    is_executable = meta.get("executable", False)
    # CAPA-4: Use execution_phase to determine workflow path (not just current status)
    execution_phase_str = meta.get("execution_phase")
    execution_phase = ExecutionPhase(execution_phase_str) if execution_phase_str else None

    # Use WorkflowEngine to determine transition (CR-026)
    engine = get_workflow_engine()

    # Determine action based on flags
    if args.review:
        action = Action.ROUTE_REVIEW
    elif args.approval:
        action = Action.ROUTE_APPROVAL
        # CR-034: Check approval gate before allowing approval routing
        can_route, gate_error = check_approval_gate(meta)
        if not can_route:
            print(f"Error: {gate_error}")
            return 1
    else:
        print("Error: Must specify workflow type (--review or --approval)")
        return 1

    # Get transition from workflow engine
    result = engine.get_transition(
        current_status=current_status,
        action=action,
        is_executable=is_executable,
        execution_phase=execution_phase,
    )

    if not result.success:
        print(f"Error: {result.error_message}")
        return 1

    target_status = result.to_status
    workflow_type = result.workflow_type.value if result.workflow_type else "UNKNOWN"

    # Handle --retire flag
    if getattr(args, 'retire', False):
        # --retire only applies to final approval routing
        if workflow_type not in ("APPROVAL", "POST_APPROVAL"):
            print("Error: --retire only applies to --approval routing (for final approval phase)")
            return 1
        # CR-034: Check version >= 1.0 (only once-effective documents can be retired)
        version = meta.get("version", "0.1")
        major_version = int(str(version).split(".")[0])
        if major_version < 1:
            print(f"""
Error: Cannot retire document that was never effective.

Current version: {version}
Required: Version >= 1.0

Only documents that have been approved at least once (effective) can be retired.
If you want to permanently delete an unapproved draft, use the cancel command:
  qms --user {user} cancel {doc_id} --confirm
""")
            return 1
        # Set retiring flag in meta (will be checked during approval)
        meta["retiring"] = True

    # Auto-assign QA if no --assign provided
    assignees = args.assign if args.assign else ["qa"]

    # Validate transition (redundant with engine, but kept for safety)
    if target_status not in TRANSITIONS.get(current_status, []):
        print(f"Error: Cannot transition from {current_status.value} to {target_status.value}")
        return 1

    # Update .meta file (authoritative workflow state)
    version = meta.get("version", "0.1")
    meta = update_meta_route(meta, target_status.value, assignees)
    write_meta(doc_id, doc_type, meta)

    # Log status change (CAPA-3: audit trail completeness)
    log_status_change(doc_id, doc_type, user, version, current_status.value, target_status.value)

    # Log routing event to audit trail
    if "REVIEW" in workflow_type:
        log_route_review(doc_id, doc_type, user, version, assignees, workflow_type)
    else:
        log_route_approval(doc_id, doc_type, user, version, assignees, workflow_type)

    # Create tasks in assignee inboxes (CR-012: Enhanced with QA Review Safeguards)
    for assignee in assignees:
        inbox_path = get_inbox_path(assignee)
        inbox_path.mkdir(parents=True, exist_ok=True)

        task_type = "REVIEW" if "REVIEW" in workflow_type else "APPROVAL"
        task_id = f"task-{doc_id}-{workflow_type.lower()}-v{version.replace('.', '-')}"
        task_path = inbox_path / f"{task_id}.md"

        # Generate enhanced task content with mandatory checklist and structured format
        # CR-027: Pass doc_type for prompt customization
        # CR-036-VAR-005: Pass title, status, responsible_user for task content
        if task_type == "REVIEW":
            task_content = generate_review_task_content(
                doc_id=doc_id,
                version=version,
                workflow_type=workflow_type,
                assignee=assignee,
                assigned_by=user,
                task_id=task_id,
                doc_type=doc_type,
                title=doc_title,
                status=target_status.value,
                responsible_user=meta.get("responsible_user", "")
            )
        else:
            task_content = generate_approval_task_content(
                doc_id=doc_id,
                version=version,
                workflow_type=workflow_type,
                assignee=assignee,
                assigned_by=user,
                task_id=task_id,
                doc_type=doc_type,
                title=doc_title,
                status=target_status.value,
                responsible_user=meta.get("responsible_user", "")
            )

        task_path.write_text(task_content, encoding="utf-8")

    print(f"Routed: {doc_id} for {workflow_type}")
    print(f"Status: {current_status.value} -> {target_status.value}")
    print(f"Assigned to: {', '.join(assignees)}")

    return 0
