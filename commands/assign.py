"""
QMS Assign Command

Adds reviewers/approvers to an active workflow.

Created as part of CR-026: QMS CLI Extensibility Refactoring
"""
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from registry import CommandRegistry
from qms_config import Status, VALID_USERS
from qms_paths import get_doc_type, get_doc_path, get_inbox_path
from qms_auth import get_current_user, check_permission, verify_user_identity
from qms_templates import generate_review_task_content, generate_approval_task_content
from qms_meta import read_meta, write_meta


@CommandRegistry.register(
    name="assign",
    help="Add reviewers/approvers to an active workflow",
    requires_doc_id=True,
    doc_id_help="Document ID",
    arguments=[
        {"flags": ["--assignees"], "help": "Users to assign", "nargs": "+"},
    ],
)
def cmd_assign(args) -> int:
    """Add reviewers/approvers to an active workflow."""
    doc_id = args.doc_id
    user = get_current_user(args)

    if not verify_user_identity(user):
        return 1

    # Permission check - only QA can assign
    allowed, error = check_permission(user, "assign")
    if not allowed:
        print(error)
        return 1

    new_assignees = args.assignees
    if not new_assignees:
        print("""
Error: Must specify --assignees with at least one user to assign.

Usage: qms --user qa assign DOC-ID --assignees user1 user2 ...

Example:
  qms --user qa assign SOP-003 --assignees tu_ui tu_scene

Valid users to assign:
  Technical Units: tu_ui, tu_scene, tu_sketch, tu_sim
  Business Unit: bu
""")
        return 1

    # Validate assignees are valid users
    invalid_users = [u for u in new_assignees if u not in VALID_USERS]
    if invalid_users:
        print(f"""
Error: Invalid user(s): {', '.join(invalid_users)}

Valid users to assign:
  Technical Units: tu_ui, tu_scene, tu_sketch, tu_sim
  Business Unit: bu
  QA: qa
  Initiators: lead, claude
""")
        return 1

    draft_path = get_doc_path(doc_id, draft=True)
    if not draft_path.exists():
        print(f"""
Error: No draft found for {doc_id}.

You can only assign users to documents that are in an active workflow.
Check the document status: qms --user {user} status {doc_id}
""")
        return 1

    # Get workflow state from .meta (authoritative source) - CR-012 fix
    doc_type = get_doc_type(doc_id)
    meta = read_meta(doc_id, doc_type) or {}
    current_status = Status(meta.get("status", "DRAFT"))
    version = meta.get("version", "0.1")
    pending_assignees = meta.get("pending_assignees", [])

    # Determine if we're in a review or approval workflow
    review_statuses = [Status.IN_REVIEW, Status.IN_PRE_REVIEW, Status.IN_POST_REVIEW]
    approval_statuses = [Status.IN_APPROVAL, Status.IN_PRE_APPROVAL, Status.IN_POST_APPROVAL]

    if current_status in review_statuses:
        workflow_name = "review"
        # Determine workflow type from status
        if current_status == Status.IN_PRE_REVIEW:
            workflow_type = "PRE_REVIEW"
        elif current_status == Status.IN_POST_REVIEW:
            workflow_type = "POST_REVIEW"
        else:
            workflow_type = "REVIEW"
    elif current_status in approval_statuses:
        workflow_name = "approval"
        if current_status == Status.IN_PRE_APPROVAL:
            workflow_type = "PRE_APPROVAL"
        elif current_status == Status.IN_POST_APPROVAL:
            workflow_type = "POST_APPROVAL"
        else:
            workflow_type = "APPROVAL"
    else:
        print(f"Error: {doc_id} is not in an active workflow (status: {current_status.value})")
        print("Can only assign users during IN_REVIEW or IN_APPROVAL states.")
        return 1

    # Add new assignees to pending_assignees in .meta
    added = []
    for new_user in new_assignees:
        if new_user in pending_assignees:
            print(f"Note: {new_user} is already assigned")
        else:
            pending_assignees.append(new_user)
            added.append(new_user)

            # Create task in new assignee's inbox (CR-012: Use enhanced task content)
            inbox_path = get_inbox_path(new_user)
            inbox_path.mkdir(parents=True, exist_ok=True)

            task_type = "REVIEW" if workflow_name == "review" else "APPROVAL"
            task_id = f"task-{doc_id}-{workflow_type.lower()}-v{version.replace('.', '-')}"
            task_path = inbox_path / f"{task_id}.md"

            # Generate enhanced task content
            if task_type == "REVIEW":
                task_content = generate_review_task_content(
                    doc_id=doc_id,
                    version=version,
                    workflow_type=workflow_type,
                    assignee=new_user,
                    assigned_by=user,
                    task_id=task_id
                )
            else:
                task_content = generate_approval_task_content(
                    doc_id=doc_id,
                    version=version,
                    workflow_type=workflow_type,
                    assignee=new_user,
                    assigned_by=user,
                    task_id=task_id
                )

            task_path.write_text(task_content, encoding="utf-8")

    if added:
        # Update .meta with new pending_assignees
        meta["pending_assignees"] = pending_assignees
        write_meta(doc_id, doc_type, meta)
        print(f"Assigned to {doc_id} ({workflow_name}): {', '.join(added)}")
    else:
        print("No new users assigned (all already in workflow)")

    return 0
