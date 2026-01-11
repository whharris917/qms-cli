"""
QMS CLI Commands Module

Contains all command implementations for the QMS CLI.
"""
import shutil
import sys
from pathlib import Path
from typing import Optional, Dict, Any

from qms_config import (
    Status, TRANSITIONS, DOCUMENT_TYPES, VALID_USERS
)
from qms_paths import (
    PROJECT_ROOT, QMS_ROOT, ARCHIVE_ROOT,
    get_doc_type, get_doc_path, get_archive_path, get_workspace_path,
    get_inbox_path, get_next_number
)
from qms_io import (
    parse_frontmatter, read_document, write_document_minimal,
    filter_author_frontmatter
)
from qms_auth import (
    get_current_user, check_permission, verify_user_identity
)
from qms_templates import (
    load_template_for_type, generate_review_task_content, generate_approval_task_content
)
from qms_meta import (
    read_meta, write_meta, create_initial_meta,
    update_meta_checkout, update_meta_checkin, update_meta_route,
    update_meta_review_complete, update_meta_approval
)
from qms_audit import (
    get_comments, get_latest_version_comments,
    log_create, log_checkout, log_checkin, log_route_review, log_route_approval,
    log_review, log_approve, log_reject, log_effective, log_release, log_revert, log_close,
    log_retire, log_status_change, format_audit_history, format_comments
)
from qms_schema import get_doc_type_from_id, increment_minor_version, increment_major_version


def build_full_frontmatter(
    minimal_fm: Dict[str, Any],
    doc_id: str,
    doc_type: str,
    meta: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Build full frontmatter by merging author fields with workflow state from .meta.

    Used when displaying documents (e.g., qms read).
    """
    if meta is None:
        meta = read_meta(doc_id, doc_type) or {}

    # Start with identity fields
    full_fm = {
        "doc_id": doc_id,
        "document_type": doc_type,
    }

    # Add workflow state from .meta
    if meta:
        full_fm["version"] = meta.get("version", "0.1")
        full_fm["status"] = meta.get("status", "DRAFT")
        full_fm["executable"] = meta.get("executable", False)
        full_fm["responsible_user"] = meta.get("responsible_user")
        full_fm["checked_out"] = meta.get("checked_out", False)
        if meta.get("effective_version"):
            full_fm["effective_version"] = meta["effective_version"]

    # Add author-maintained fields
    full_fm.update(filter_author_frontmatter(minimal_fm))

    return full_fm


# =============================================================================
# Commands
# =============================================================================

def cmd_create(args):
    """Create a new document."""
    user = get_current_user(args)

    if not verify_user_identity(user):
        return 1

    # Permission check
    allowed, error = check_permission(user, "create")
    if not allowed:
        print(error)
        return 1

    doc_type = args.type.upper()

    if doc_type not in DOCUMENT_TYPES:
        print(f"Error: Unknown document type '{doc_type}'")
        print(f"Valid types: {', '.join(DOCUMENT_TYPES.keys())}")
        return 1

    config = DOCUMENT_TYPES[doc_type]

    # Generate doc_id
    if config.get("singleton"):
        doc_id = config["prefix"]
    else:
        next_num = get_next_number(doc_type)
        doc_id = f"{config['prefix']}-{next_num:03d}"

    # Check if already exists
    effective_path = get_doc_path(doc_id, draft=False)
    draft_path = get_doc_path(doc_id, draft=True)

    if effective_path.exists() or draft_path.exists():
        print(f"Error: {doc_id} already exists")
        return 1

    # Create directory structure if needed
    if config.get("folder_per_doc"):
        folder_path = QMS_ROOT / config["path"] / doc_id
        folder_path.mkdir(parents=True, exist_ok=True)

    # Load template for document type (CR-019)
    # Falls back to minimal template if TEMPLATE-{type} doesn't exist
    title = args.title or f"{doc_type} - [Title]"
    frontmatter, body = load_template_for_type(doc_type, doc_id, title)

    # Write to draft path (minimal frontmatter only)
    write_document_minimal(draft_path, frontmatter, body)

    # DUAL-WRITE: Create .meta file
    meta = create_initial_meta(
        doc_id=doc_id,
        doc_type=doc_type,
        version="0.1",
        status="DRAFT",
        executable=config["executable"],
        responsible_user=user
    )
    write_meta(doc_id, doc_type, meta)

    # DUAL-WRITE: Log CREATE event to audit trail
    title = args.title or f"{doc_type} - [Title]"
    log_create(doc_id, doc_type, user, "0.1", title)

    # Copy to user's workspace
    workspace_path = get_workspace_path(user, doc_id)
    workspace_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy(draft_path, workspace_path)

    print(f"Created: {doc_id} (v0.1, DRAFT)")
    print(f"Location: {draft_path.relative_to(PROJECT_ROOT)}")
    print(f"Workspace: {workspace_path.relative_to(PROJECT_ROOT)}")
    print(f"Responsible User: {user}")

    return 0


def cmd_read(args):
    """Read a document."""
    doc_id = args.doc_id

    try:
        if args.version:
            # Read specific archived version
            path = get_archive_path(doc_id, args.version)
        elif args.draft:
            path = get_doc_path(doc_id, draft=True)
        else:
            # Read effective version, fall back to draft
            path = get_doc_path(doc_id, draft=False)
            if not path.exists():
                path = get_doc_path(doc_id, draft=True)

        if not path.exists():
            print(f"Error: Document not found: {doc_id}")
            return 1

        content = path.read_text(encoding="utf-8")
        print(content)
        return 0

    except Exception as e:
        print(f"Error: {e}")
        return 1


def cmd_checkout(args):
    """Check out a document for editing."""
    doc_id = args.doc_id
    user = get_current_user(args)

    if not verify_user_identity(user):
        return 1

    # Permission check
    allowed, error = check_permission(user, "checkout")
    if not allowed:
        print(error)
        return 1

    # Find the document (effective or draft)
    effective_path = get_doc_path(doc_id, draft=False)
    draft_path = get_doc_path(doc_id, draft=True)

    doc_type = get_doc_type(doc_id)
    meta = read_meta(doc_id, doc_type) or {}

    if draft_path.exists():
        # Already a draft - check if already checked out (from .meta)
        if meta.get("checked_out"):
            current_owner = meta.get("responsible_user", "unknown")
            if current_owner == user:
                print(f"You already have {doc_id} checked out")
            else:
                print(f"Error: {doc_id} is checked out by {current_owner}")
            return 1

        # Read content for workspace
        content = draft_path.read_text(encoding="utf-8")
        frontmatter, body = parse_frontmatter(content)

        # Check out existing draft - update .meta
        version = meta.get("version", "0.1")
        meta = update_meta_checkout(meta, user)
        write_meta(doc_id, doc_type, meta)

        # Log CHECKOUT event
        log_checkout(doc_id, doc_type, user, version)

        # Write content to workspace
        workspace_path = get_workspace_path(user, doc_id)
        workspace_path.parent.mkdir(parents=True, exist_ok=True)
        write_document_minimal(workspace_path, frontmatter, body)

    elif effective_path.exists():
        # Create new draft from effective
        content = effective_path.read_text(encoding="utf-8")
        frontmatter, body = parse_frontmatter(content)

        current_version = meta.get("version", "1.0")
        major = int(str(current_version).split(".")[0])
        new_version = f"{major}.1"

        # Archive effective version before creating draft (per CR-005)
        archive_path = get_archive_path(doc_id, current_version)
        archive_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(effective_path, archive_path)
        print(f"Archived: v{current_version}")

        # Update .meta file for new draft
        meta = update_meta_checkout(meta, user, new_version=new_version)
        meta["status"] = "DRAFT"
        meta["effective_version"] = current_version
        write_meta(doc_id, doc_type, meta)

        # Log CHECKOUT event
        log_checkout(doc_id, doc_type, user, new_version, from_version=current_version)

        # Create draft from effective
        draft_path.parent.mkdir(parents=True, exist_ok=True)
        write_document_minimal(draft_path, frontmatter, body)

        # Write content to workspace
        workspace_path = get_workspace_path(user, doc_id)
        workspace_path.parent.mkdir(parents=True, exist_ok=True)
        write_document_minimal(workspace_path, frontmatter, body)

        print(f"Created draft v{new_version} from effective v{current_version}")
    else:
        print(f"Error: Document not found: {doc_id}")
        return 1

    print(f"Checked out: {doc_id}")
    print(f"Workspace: {workspace_path.relative_to(PROJECT_ROOT)}")

    return 0


def cmd_checkin(args):
    """Check in a document from workspace."""
    doc_id = args.doc_id
    user = get_current_user(args)

    if not verify_user_identity(user):
        return 1

    # Permission check (group level)
    allowed, error = check_permission(user, "checkin")
    if not allowed:
        print(error)
        return 1

    workspace_path = get_workspace_path(user, doc_id)
    if not workspace_path.exists():
        print(f"""
Error: {doc_id} not found in your workspace.

Your workspace contains documents you have checked out for editing.
To check out a document: qms --user {user} checkout {doc_id}
To see your workspace: qms --user {user} workspace
""")
        return 1

    draft_path = get_doc_path(doc_id, draft=True)
    doc_type = get_doc_type(doc_id)
    meta = read_meta(doc_id, doc_type) or {}

    # Verify user has it checked out (ownership check via .meta)
    doc_owner = meta.get("responsible_user")
    allowed, error = check_permission(user, "checkin", doc_owner=doc_owner)
    if not allowed:
        print(error)
        return 1

    # Read workspace version
    frontmatter, body = read_document(workspace_path)

    # Get version from .meta (authoritative source)
    version = meta.get("version", frontmatter.get("version", "0.1"))

    # Write content to QMS draft with minimal frontmatter
    write_document_minimal(draft_path, frontmatter, body)

    # Update .meta file
    meta = update_meta_checkin(meta)
    write_meta(doc_id, doc_type, meta)

    # Log CHECKIN event
    log_checkin(doc_id, doc_type, user, version)

    # Remove from workspace
    workspace_path.unlink()

    print(f"Checked in: {doc_id} (v{version})")

    return 0


def cmd_route(args):
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

    current_status = Status(meta.get("status", "DRAFT"))
    is_executable = meta.get("executable", False)
    # CAPA-4: Use execution_phase to determine workflow path (not just current status)
    # This ensures documents that were checked out and back in after release
    # continue in the post-release workflow
    execution_phase = meta.get("execution_phase")

    # Determine target status based on flags
    # For executable docs, use execution_phase to determine pre vs post workflow
    if args.review:
        if is_executable:
            # CAPA-4: Use execution_phase (if set) to determine workflow path
            # Also handle legacy documents without execution_phase by checking status
            is_post_release = (execution_phase == "post_release" or
                               current_status == Status.IN_EXECUTION)
            if is_post_release:
                # Post-release: route to post-review (even if status is DRAFT after checkout/checkin)
                if current_status in (Status.DRAFT, Status.IN_EXECUTION):
                    target_status = Status.IN_POST_REVIEW
                    workflow_type = "POST_REVIEW"
                else:
                    print(f"Error: Cannot route for post-review from {current_status.value}")
                    print("  Post-review routing is valid from: DRAFT, IN_EXECUTION")
                    return 1
            else:
                # Pre-release: route to pre-review
                if current_status == Status.DRAFT:
                    target_status = Status.IN_PRE_REVIEW
                    workflow_type = "PRE_REVIEW"
                else:
                    print(f"Error: Cannot route for pre-review from {current_status.value}")
                    print("  Pre-review routing is valid from: DRAFT")
                    return 1
        else:
            target_status = Status.IN_REVIEW
            workflow_type = "REVIEW"
    elif args.approval:
        if is_executable:
            # CAPA-4: Use execution_phase to determine workflow path
            # Also handle legacy documents without execution_phase by checking status
            is_post_release = (execution_phase == "post_release" or
                               current_status == Status.POST_REVIEWED)
            if is_post_release:
                # Post-release: route to post-approval
                if current_status == Status.POST_REVIEWED:
                    target_status = Status.IN_POST_APPROVAL
                    workflow_type = "POST_APPROVAL"
                else:
                    print(f"Error: Cannot route for post-approval from {current_status.value}")
                    print("  Post-approval routing is valid from: POST_REVIEWED")
                    return 1
            else:
                # Pre-release: route to pre-approval
                if current_status == Status.PRE_REVIEWED:
                    target_status = Status.IN_PRE_APPROVAL
                    workflow_type = "PRE_APPROVAL"
                else:
                    print(f"Error: Cannot route for pre-approval from {current_status.value}")
                    print("  Pre-approval routing is valid from: PRE_REVIEWED")
                    return 1
        else:
            if current_status != Status.REVIEWED:
                print(f"Error: Must be REVIEWED before approval (currently {current_status.value})")
                return 1
            target_status = Status.IN_APPROVAL
            workflow_type = "APPROVAL"
    else:
        print("Error: Must specify workflow type (--review or --approval)")
        return 1

    # Handle --retire flag
    if getattr(args, 'retire', False):
        # --retire only applies to final approval routing
        if workflow_type not in ("APPROVAL", "POST_APPROVAL"):
            print("Error: --retire only applies to --approval routing (for final approval phase)")
            return 1
        # Set retiring flag in meta (will be checked during approval)
        meta["retiring"] = True

    # Auto-assign QA if no --assign provided
    assignees = args.assign if args.assign else ["qa"]

    # Validate transition
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
        if task_type == "REVIEW":
            task_content = generate_review_task_content(
                doc_id=doc_id,
                version=version,
                workflow_type=workflow_type,
                assignee=assignee,
                assigned_by=user,
                task_id=task_id
            )
        else:
            task_content = generate_approval_task_content(
                doc_id=doc_id,
                version=version,
                workflow_type=workflow_type,
                assignee=assignee,
                assigned_by=user,
                task_id=task_id
            )

        task_path.write_text(task_content, encoding="utf-8")

    print(f"Routed: {doc_id} for {workflow_type}")
    print(f"Status: {current_status.value} -> {target_status.value}")
    print(f"Assigned to: {', '.join(assignees)}")

    return 0


def cmd_assign(args):
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


def cmd_review(args):
    """Submit a review for a document."""
    doc_id = args.doc_id
    user = get_current_user(args)

    if not verify_user_identity(user):
        return 1

    # Permission check (group level - assigned check done later)
    allowed, error = check_permission(user, "review")
    if not allowed:
        print(error)
        return 1

    comment = args.comment

    if not comment:
        print(f"""
Error: Must provide --comment with review.

Usage:
  qms --user {user} review DOC-ID --recommend --comment "Your comments"
  qms --user {user} review DOC-ID --request-updates --comment "Changes needed"

The comment should explain your review findings and rationale.
""")
        return 1

    # Determine outcome
    if args.recommend:
        outcome = "RECOMMEND"
    elif args.request_updates:
        outcome = "UPDATES_REQUIRED"
    else:
        print(f"""
Error: Must specify review outcome.

Options:
  --recommend        Recommend the document for approval
  --request-updates  Request changes before approval

Usage:
  qms --user {user} review DOC-ID --recommend --comment "Approved. No issues found."
  qms --user {user} review DOC-ID --request-updates --comment "Section 3 needs clarification."
""")
        return 1

    draft_path = get_doc_path(doc_id, draft=True)
    if not draft_path.exists():
        print(f"""
Error: No draft found for {doc_id}.

Check your inbox for assigned review tasks: qms --user {user} inbox
Check document status: qms --user {user} status {doc_id}
""")
        return 1

    # Get workflow state from .meta (authoritative source)
    doc_type = get_doc_type(doc_id)
    meta = read_meta(doc_id, doc_type) or {}
    current_status = Status(meta.get("status", "DRAFT"))
    version = meta.get("version", "0.1")
    pending_assignees = meta.get("pending_assignees", [])

    # Verify document is in a review state
    review_statuses = [Status.IN_REVIEW, Status.IN_PRE_REVIEW, Status.IN_POST_REVIEW]
    if current_status not in review_statuses:
        print(f"""
Error: {doc_id} is not in review.

Current status: {current_status.value}

Documents can only be reviewed when in one of these states:
  - IN_REVIEW (non-executable documents)
  - IN_PRE_REVIEW (executable documents, before execution)
  - IN_POST_REVIEW (executable documents, after execution)

Check document status: qms --user {user} status {doc_id}
""")
        return 1

    # Check if user is assigned to review
    if user not in pending_assignees:
        print(f"""
Error: You ({user}) are not assigned to review {doc_id}.

Currently assigned reviewers: {', '.join(pending_assignees) if pending_assignees else 'None'}

You can only review documents you are assigned to.
Check your inbox for assigned tasks: qms --user {user} inbox

If you should be reviewing this document, ask QA to assign you:
  (QA) qms --user qa assign {doc_id} --assignees {user}
""")
        return 1

    # Log REVIEW event to audit trail (comments only live here now)
    log_review(doc_id, doc_type, user, version, outcome, comment)

    # Update .meta file - remove this user from pending assignees
    remaining_assignees = [u for u in pending_assignees if u != user]
    all_complete = len(remaining_assignees) == 0

    new_status = None
    if all_complete:
        # Transition to REVIEWED state
        status_map = {
            Status.IN_REVIEW: Status.REVIEWED,
            Status.IN_PRE_REVIEW: Status.PRE_REVIEWED,
            Status.IN_POST_REVIEW: Status.POST_REVIEWED,
        }
        new_status = status_map.get(current_status)
        if new_status:
            print(f"All reviews complete. Status: {current_status.value} -> {new_status.value}")
            # Log status change (CAPA-3: audit trail completeness)
            log_status_change(doc_id, doc_type, user, version, current_status.value, new_status.value)

    meta = update_meta_review_complete(
        meta, user, remaining_assignees,
        new_status=new_status.value if new_status else None
    )
    write_meta(doc_id, doc_type, meta)

    # Remove task from inbox
    inbox_path = get_inbox_path(user)
    for task_file in inbox_path.glob(f"task-{doc_id}-*.md"):
        task_file.unlink()

    print(f"Review submitted for {doc_id}")

    return 0


def cmd_approve(args):
    """Approve a document."""
    doc_id = args.doc_id
    user = get_current_user(args)

    if not verify_user_identity(user):
        return 1

    # Permission check (group level)
    allowed, error = check_permission(user, "approve")
    if not allowed:
        print(error)
        return 1

    draft_path = get_doc_path(doc_id, draft=True)
    if not draft_path.exists():
        print(f"""
Error: No draft found for {doc_id}.

Check your inbox for assigned approval tasks: qms --user {user} inbox
Check document status: qms --user {user} status {doc_id}
""")
        return 1

    # Get workflow state from .meta (authoritative source)
    doc_type = get_doc_type(doc_id)
    meta = read_meta(doc_id, doc_type) or {}
    current_status = Status(meta.get("status", "DRAFT"))
    current_version = meta.get("version", "0.1")
    is_executable = meta.get("executable", False)
    pending_assignees = meta.get("pending_assignees", [])

    # Verify document is in an approval state
    approval_statuses = [Status.IN_APPROVAL, Status.IN_PRE_APPROVAL, Status.IN_POST_APPROVAL]
    if current_status not in approval_statuses:
        print(f"""
Error: {doc_id} is not in approval.

Current status: {current_status.value}

Documents can only be approved when in one of these states:
  - IN_APPROVAL (non-executable documents)
  - IN_PRE_APPROVAL (executable documents, before execution)
  - IN_POST_APPROVAL (executable documents, after execution)

Check document status: qms --user {user} status {doc_id}
""")
        return 1

    # Check if user is assigned to approve
    if user not in pending_assignees:
        print(f"""
Error: You ({user}) are not assigned to approve {doc_id}.

Currently assigned approvers: {', '.join(pending_assignees) if pending_assignees else 'None'}

You can only approve documents you are assigned to.
Check your inbox for assigned tasks: qms --user {user} inbox
""")
        return 1

    # Log APPROVE event to audit trail
    log_approve(doc_id, doc_type, user, current_version)

    # Update .meta file - remove this user from pending assignees
    remaining_assignees = [u for u in pending_assignees if u != user]
    all_approved = len(remaining_assignees) == 0

    if all_approved:
        # Transition to APPROVED state and bump version
        status_map = {
            Status.IN_APPROVAL: Status.APPROVED,
            Status.IN_PRE_APPROVAL: Status.PRE_APPROVED,
            Status.IN_POST_APPROVAL: Status.POST_APPROVED,
        }
        new_status = status_map.get(current_status)

        if new_status:
            # Bump to major version
            major = int(str(current_version).split(".")[0])
            new_version = f"{major + 1}.0"

            # Archive current draft
            archive_path = get_archive_path(doc_id, current_version)
            archive_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy(draft_path, archive_path)

            print(f"All approvals complete. Status: {current_status.value} -> {new_status.value}")
            print(f"Version: {current_version} -> {new_version}")

            # Log status change (CAPA-3: audit trail completeness)
            log_status_change(doc_id, doc_type, user, new_version, current_status.value, new_status.value)

            # Check if this is a retirement approval
            is_retiring = meta.get("retiring", False)

            if is_retiring:
                # Retirement workflow: archive and set RETIRED status
                archive_path = get_archive_path(doc_id, new_version)
                archive_path.parent.mkdir(parents=True, exist_ok=True)

                # Read document and archive it
                frontmatter, body = read_document(draft_path)
                write_document_minimal(archive_path, frontmatter, body)
                print(f"Archived: {archive_path.relative_to(PROJECT_ROOT)}")

                # Delete working copy (draft)
                draft_path.unlink()

                # Also delete effective copy if it exists (for previously-effective docs being retired)
                effective_path = get_doc_path(doc_id, draft=False)
                if effective_path.exists():
                    effective_path.unlink()

                # Update meta - set RETIRED status, clear owner
                meta = update_meta_approval(meta, new_status=Status.RETIRED.value, new_version=new_version, clear_owner=True)
                meta.pop("retiring", None)  # Clear the retiring flag
                write_meta(doc_id, doc_type, meta)
                log_retire(doc_id, doc_type, user, current_version, new_version)
                # Log additional status change to RETIRED (CAPA-3)
                log_status_change(doc_id, doc_type, user, new_version, new_status.value, Status.RETIRED.value)
                print(f"Document is now RETIRED")
                # No metadata injection for RETIRED docs (files are deleted)

            elif new_status == Status.APPROVED:
                # Non-executable normal workflow: transition to EFFECTIVE
                frontmatter, body = read_document(draft_path)
                effective_path = get_doc_path(doc_id, draft=False)
                write_document_minimal(effective_path, frontmatter, body)
                draft_path.unlink()
                print(f"Document is now EFFECTIVE at {effective_path.relative_to(PROJECT_ROOT)}")

                # Update meta - clear owner for effective docs
                meta = update_meta_approval(meta, new_status=Status.EFFECTIVE.value, new_version=new_version, clear_owner=True)
                log_effective(doc_id, doc_type, user, current_version, new_version)
                # Log additional status change to EFFECTIVE (CAPA-3)
                log_status_change(doc_id, doc_type, user, new_version, new_status.value, Status.EFFECTIVE.value)

                write_meta(doc_id, doc_type, meta)
            else:
                # Executable document - stays as draft until closed
                meta = update_meta_approval(meta, new_status=new_status.value, new_version=new_version, clear_owner=False)
                write_meta(doc_id, doc_type, meta)
    else:
        # Still waiting for more approvals
        meta["pending_assignees"] = remaining_assignees
        write_meta(doc_id, doc_type, meta)

    # Remove task from inbox
    inbox_path = get_inbox_path(user)
    for task_file in inbox_path.glob(f"task-{doc_id}-*.md"):
        task_file.unlink()

    print(f"Approval submitted for {doc_id}")

    return 0


def cmd_reject(args):
    """Reject a document."""
    doc_id = args.doc_id
    user = get_current_user(args)

    if not verify_user_identity(user):
        return 1

    # Permission check (group level)
    allowed, error = check_permission(user, "reject")
    if not allowed:
        print(error)
        return 1

    comment = args.comment

    if not comment:
        print(f"""
Error: Must provide --comment with rejection.

Usage:
  qms --user {user} reject DOC-ID --comment "Reason for rejection"

The comment should explain why the document is being rejected
and what changes are needed before re-submission.
""")
        return 1

    draft_path = get_doc_path(doc_id, draft=True)
    if not draft_path.exists():
        print(f"""
Error: No draft found for {doc_id}.

Check your inbox for assigned approval tasks: qms --user {user} inbox
Check document status: qms --user {user} status {doc_id}
""")
        return 1

    # Get workflow state from .meta (authoritative source)
    doc_type = get_doc_type(doc_id)
    meta = read_meta(doc_id, doc_type) or {}
    current_status = Status(meta.get("status", "DRAFT"))
    version = meta.get("version", "0.1")
    pending_assignees = meta.get("pending_assignees", [])

    # Verify document is in an approval state
    approval_statuses = [Status.IN_APPROVAL, Status.IN_PRE_APPROVAL, Status.IN_POST_APPROVAL]
    if current_status not in approval_statuses:
        print(f"""
Error: {doc_id} is not in approval.

Current status: {current_status.value}

Documents can only be rejected when in an approval state.
Check document status: qms --user {user} status {doc_id}
""")
        return 1

    # Check if user is assigned to approve
    if user not in pending_assignees:
        print(f"Error: You are not assigned to approve {doc_id}")
        return 1

    # Log REJECT event to audit trail (comment goes here)
    log_reject(doc_id, doc_type, user, version, comment)

    # Transition back to REVIEWED state
    status_map = {
        Status.IN_APPROVAL: Status.REVIEWED,
        Status.IN_PRE_APPROVAL: Status.PRE_REVIEWED,
        Status.IN_POST_APPROVAL: Status.POST_REVIEWED,
    }
    new_status = status_map.get(current_status)

    if new_status:
        print(f"Document rejected. Status: {current_status.value} -> {new_status.value}")
        # Log status change (CAPA-3: audit trail completeness)
        log_status_change(doc_id, doc_type, user, version, current_status.value, new_status.value)

    # Update .meta file
    meta = update_meta_approval(meta, new_status=new_status.value if new_status else None)
    meta["pending_assignees"] = []  # Clear pending assignees on rejection
    write_meta(doc_id, doc_type, meta)

    # Remove all pending approval tasks for this document
    for user_dir in USERS_ROOT.iterdir():
        if user_dir.is_dir():
            inbox = user_dir / "inbox"
            if inbox.exists():
                for task_file in inbox.glob(f"task-{doc_id}-*approval*.md"):
                    task_file.unlink()

    print(f"Rejected: {doc_id}")
    print(f"Reason: {comment}")

    return 0


def cmd_release(args):
    """Release an executable document for execution."""
    doc_id = args.doc_id
    user = get_current_user(args)

    if not verify_user_identity(user):
        return 1

    # Permission check (group level)
    allowed, error = check_permission(user, "release")
    if not allowed:
        print(error)
        return 1

    draft_path = get_doc_path(doc_id, draft=True)
    if not draft_path.exists():
        print(f"""
Error: No draft found for {doc_id}.

Check document status: qms --user {user} status {doc_id}
""")
        return 1

    # Get workflow state from .meta (authoritative source)
    doc_type = get_doc_type(doc_id)
    meta = read_meta(doc_id, doc_type) or {}
    current_status = Status(meta.get("status", "DRAFT"))
    version = meta.get("version", "0.1")
    is_executable = meta.get("executable", False)

    if not is_executable:
        print(f"""
Error: {doc_id} is not an executable document.

Only executable documents (CR, INV, CAPA, TP, ER) can be released.
Non-executable documents (SOP, RS, DS, etc.) become EFFECTIVE after approval.
""")
        return 1

    # Check ownership
    doc_owner = meta.get("responsible_user")
    allowed, error = check_permission(user, "release", doc_owner=doc_owner)
    if not allowed:
        print(error)
        return 1

    if current_status != Status.PRE_APPROVED:
        print(f"""
Error: {doc_id} must be PRE_APPROVED to release.

Current status: {current_status.value}

Workflow for executable documents:
  DRAFT -> IN_PRE_REVIEW -> PRE_REVIEWED -> IN_PRE_APPROVAL -> PRE_APPROVED -> release -> IN_EXECUTION
""")
        return 1

    # Log RELEASE event to audit trail
    log_release(doc_id, doc_type, user, version)

    # Log status change (CAPA-3: audit trail completeness)
    log_status_change(doc_id, doc_type, user, version, Status.PRE_APPROVED.value, Status.IN_EXECUTION.value)

    # Update .meta file
    meta["status"] = Status.IN_EXECUTION.value
    # CAPA-4: Set execution_phase to post_release on release
    meta["execution_phase"] = "post_release"
    write_meta(doc_id, doc_type, meta)

    print(f"Released: {doc_id}")
    print(f"Status: PRE_APPROVED -> IN_EXECUTION")

    return 0


def cmd_revert(args):
    """Revert an executable document back to execution."""
    doc_id = args.doc_id
    user = get_current_user(args)

    if not verify_user_identity(user):
        return 1

    # Permission check (group level)
    allowed, error = check_permission(user, "revert")
    if not allowed:
        print(error)
        return 1

    reason = args.reason

    if not reason:
        print(f"""
Error: Must provide --reason for revert.

Usage:
  qms --user {user} revert DOC-ID --reason "Reason for reverting to execution"

The reason should explain why additional execution work is needed.
""")
        return 1

    draft_path = get_doc_path(doc_id, draft=True)
    if not draft_path.exists():
        print(f"""
Error: No draft found for {doc_id}.

Check document status: qms --user {user} status {doc_id}
""")
        return 1

    # Get workflow state from .meta (authoritative source)
    doc_type = get_doc_type(doc_id)
    meta = read_meta(doc_id, doc_type) or {}
    current_status = Status(meta.get("status", "DRAFT"))
    version = meta.get("version", "0.1")

    # Check ownership
    doc_owner = meta.get("responsible_user")
    allowed, error = check_permission(user, "revert", doc_owner=doc_owner)
    if not allowed:
        print(error)
        return 1

    if current_status != Status.POST_REVIEWED:
        print(f"""
Error: {doc_id} must be POST_REVIEWED to revert.

Current status: {current_status.value}

Revert moves a document from POST_REVIEWED back to IN_EXECUTION
when additional execution work is discovered during post-review.
""")
        return 1

    # Log REVERT event to audit trail
    log_revert(doc_id, doc_type, user, version, reason)

    # Update .meta file
    meta["status"] = Status.IN_EXECUTION.value
    write_meta(doc_id, doc_type, meta)

    print(f"Reverted: {doc_id}")
    print(f"Status: POST_REVIEWED -> IN_EXECUTION")
    print(f"Reason: {reason}")

    return 0


def cmd_close(args):
    """Close an executable document."""
    doc_id = args.doc_id
    user = get_current_user(args)

    if not verify_user_identity(user):
        return 1

    # Permission check (group level)
    allowed, error = check_permission(user, "close")
    if not allowed:
        print(error)
        return 1

    draft_path = get_doc_path(doc_id, draft=True)
    if not draft_path.exists():
        print(f"""
Error: No draft found for {doc_id}.

Check document status: qms --user {user} status {doc_id}
""")
        return 1

    # Get workflow state from .meta (authoritative source)
    doc_type = get_doc_type(doc_id)
    meta = read_meta(doc_id, doc_type) or {}
    current_status = Status(meta.get("status", "DRAFT"))
    version = meta.get("version", "0.1")
    is_executable = meta.get("executable", False)

    if not is_executable:
        print(f"""
Error: {doc_id} is not an executable document.

Only executable documents (CR, INV, CAPA, TP, ER) can be closed.
Non-executable documents (SOP, RS, DS, etc.) become EFFECTIVE after approval.
""")
        return 1

    # Check ownership
    doc_owner = meta.get("responsible_user")
    allowed, error = check_permission(user, "close", doc_owner=doc_owner)
    if not allowed:
        print(error)
        return 1

    if current_status != Status.POST_APPROVED:
        print(f"""
Error: {doc_id} must be POST_APPROVED to close.

Current status: {current_status.value}

Workflow for executable documents:
  ... -> IN_POST_REVIEW -> POST_REVIEWED -> IN_POST_APPROVAL -> POST_APPROVED -> close -> CLOSED
""")
        return 1

    # Move to effective location with minimal frontmatter
    frontmatter, body = read_document(draft_path)
    effective_path = get_doc_path(doc_id, draft=False)
    write_document_minimal(effective_path, frontmatter, body)
    draft_path.unlink()

    # Log CLOSE event to audit trail
    log_close(doc_id, doc_type, user, version)

    # Log status change (CAPA-3: audit trail completeness)
    log_status_change(doc_id, doc_type, user, version, current_status.value, Status.CLOSED.value)

    # Update .meta file (clear ownership on close)
    meta["status"] = Status.CLOSED.value
    meta["responsible_user"] = None
    meta["checked_out"] = False
    meta["checked_out_date"] = None
    meta["pending_assignees"] = []
    write_meta(doc_id, doc_type, meta)

    # Remove from workspace
    workspace_path = get_workspace_path(user, doc_id)
    if workspace_path.exists():
        workspace_path.unlink()

    print(f"Closed: {doc_id}")
    print(f"Location: {effective_path.relative_to(PROJECT_ROOT)}")

    return 0


def cmd_status(args):
    """Show document status."""
    doc_id = args.doc_id

    # Try draft first, then effective
    draft_path = get_doc_path(doc_id, draft=True)
    effective_path = get_doc_path(doc_id, draft=False)

    if draft_path.exists():
        path = draft_path
        location = "draft"
    elif effective_path.exists():
        path = effective_path
        location = "effective"
    else:
        print(f"Error: Document not found: {doc_id}")
        return 1

    # Read title from document frontmatter
    frontmatter, _ = read_document(path)

    # Get workflow state from .meta (authoritative source)
    doc_type = get_doc_type(doc_id)
    meta = read_meta(doc_id, doc_type) or {}

    print(f"Document: {doc_id}")
    print(f"Title: {frontmatter.get('title', 'N/A')}")
    print(f"Version: {meta.get('version', 'N/A')}")
    print(f"Status: {meta.get('status', 'N/A')}")
    print(f"Location: {location}")
    print(f"Type: {doc_type}")
    print(f"Executable: {meta.get('executable', False)}")
    print(f"Responsible User: {meta.get('responsible_user') or 'N/A'}")
    print(f"Checked Out: {meta.get('checked_out', False)}")

    if meta.get("effective_version"):
        print(f"Effective Version: {meta.get('effective_version')}")

    # Show pending assignees from .meta
    pending_assignees = meta.get("pending_assignees", [])
    if pending_assignees:
        status = meta.get("status", "")
        if "REVIEW" in status:
            print(f"\nPending Reviewers: {', '.join(pending_assignees)}")
        elif "APPROVAL" in status:
            print(f"\nPending Approvers: {', '.join(pending_assignees)}")

    return 0


def cmd_inbox(args):
    """List tasks in current user's inbox."""
    user = get_current_user(args)

    if not verify_user_identity(user):
        return 1

    inbox_path = get_inbox_path(user)

    if not inbox_path.exists():
        print(f"Inbox is empty")
        return 0

    tasks = list(inbox_path.glob("*.md"))
    if not tasks:
        print(f"Inbox is empty")
        return 0

    print(f"Inbox for {user}:")
    print("-" * 60)

    for task_path in sorted(tasks):
        frontmatter, _ = read_document(task_path)
        print(f"  [{frontmatter.get('task_type', '?')}] {frontmatter.get('doc_id', '?')}")
        print(f"    Workflow: {frontmatter.get('workflow_type', '?')}")
        print(f"    From: {frontmatter.get('assigned_by', '?')}")
        print(f"    Date: {frontmatter.get('assigned_date', '?')}")
        print()

    return 0


def cmd_workspace(args):
    """List documents in current user's workspace."""
    user = get_current_user(args)

    if not verify_user_identity(user):
        return 1

    workspace_path = USERS_ROOT / user / "workspace"

    if not workspace_path.exists():
        print(f"Workspace is empty")
        return 0

    docs = list(workspace_path.glob("*.md"))
    if not docs:
        print(f"Workspace is empty")
        return 0

    print(f"Workspace for {user}:")
    print("-" * 60)

    for doc_path in sorted(docs):
        frontmatter, _ = read_document(doc_path)
        print(f"  {frontmatter.get('doc_id', doc_path.stem)}")
        print(f"    Version: {frontmatter.get('version', '?')}")
        print(f"    Status: {frontmatter.get('status', '?')}")
        print()

    return 0


def cmd_fix(args) -> int:
    """Administrative fix for EFFECTIVE documents (QA/lead only)."""
    current_user = get_current_user(args)

    if current_user not in {"qa", "lead"}:
        print("Error: Only QA or lead can run administrative fixes.", file=sys.stderr)
        return 1

    doc_id = args.doc_id
    doc_path = get_doc_path(doc_id, draft=False)

    if not doc_path.exists():
        print(f"Error: Document not found: {doc_id}", file=sys.stderr)
        return 1

    frontmatter, body = read_document(doc_path)
    status = frontmatter.get("status", "")

    if status not in ("EFFECTIVE", "CLOSED"):
        print(f"Error: Fix only applies to EFFECTIVE/CLOSED documents (current: {status})", file=sys.stderr)
        return 1

    changes = []

    # Fix 1: Clear checked_out if set
    if frontmatter.get("checked_out"):
        frontmatter["checked_out"] = False
        frontmatter.pop("checked_out_date", None)
        changes.append("cleared checked_out flag")

    # Fix 2: Sync body version header with frontmatter
    version = frontmatter.get("version", "1.0")
    old_version_pattern = r"\*\*Version:\*\* [^\n]+"
    new_version_line = f"**Version:** {version}"
    if re.search(old_version_pattern, body):
        new_body = re.sub(old_version_pattern, new_version_line, body, count=1)
        if new_body != body:
            body = new_body
            changes.append(f"updated body version to {version}")

    # Fix 3: Update Effective Date if TBD
    if status == "EFFECTIVE":
        old_date_pattern = r"\*\*Effective Date:\*\* TBD"
        today = datetime.now().strftime("%Y-%m-%d")
        new_date_line = f"**Effective Date:** {today}"
        if re.search(old_date_pattern, body):
            body = re.sub(old_date_pattern, new_date_line, body, count=1)
            changes.append(f"set effective date to {today}")

    if not changes:
        print(f"No fixes needed for {doc_id}")
        return 0

    write_document(doc_path, frontmatter, body)
    print(f"Fixed {doc_id}:")
    for change in changes:
        print(f"  - {change}")

    return 0


def cmd_cancel(args) -> int:
    """Cancel a never-effective document (version < 1.0)."""
    user = get_current_user(args)

    # Only initiators can cancel
    if user not in USER_GROUPS["initiators"]:
        print("Error: Only initiators can cancel documents.", file=sys.stderr)
        return 1

    doc_id = args.doc_id
    doc_type = get_doc_type(doc_id)

    # Get document metadata
    meta = read_meta(doc_id, doc_type)
    if meta is None:
        print(f"Error: Document {doc_id} not found.", file=sys.stderr)
        return 1

    # Check version < 1.0 (never effective)
    version = meta.get("version", "0.1")
    major = int(version.split(".")[0])
    if major >= 1:
        print(f"Error: Cannot cancel {doc_id} - it was effective (v{version}).", file=sys.stderr)
        print("Use the retire workflow instead (checkout, edit, route --approval --retire).")
        return 1

    # Check not checked out by someone else
    if meta.get("checked_out"):
        responsible = meta.get("responsible_user", "unknown")
        print(f"Error: {doc_id} is checked out by {responsible}.", file=sys.stderr)
        print("Document must be checked in before canceling.")
        return 1

    # Require --confirm
    if not args.confirm:
        print(f"This will permanently delete {doc_id} (v{version}) and free the doc ID.")
        print("The following will be deleted:")
        print(f"  - Document file(s)")
        print(f"  - Metadata (.meta/{doc_type}/{doc_id}.json)")
        print(f"  - Audit trail (.audit/{doc_type}/{doc_id}.jsonl)")
        print()
        print("Run with --confirm to proceed.")
        return 1

    # Delete document file(s)
    draft_path = get_doc_path(doc_id, draft=True)
    effective_path = get_doc_path(doc_id, draft=False)

    deleted_files = []
    if draft_path.exists():
        draft_path.unlink()
        deleted_files.append(str(draft_path.relative_to(PROJECT_ROOT)))

    if effective_path.exists():
        effective_path.unlink()
        deleted_files.append(str(effective_path.relative_to(PROJECT_ROOT)))

    # For CR documents, also try to remove the directory if empty
    if doc_type == "CR":
        cr_dir = QMS_ROOT / "CR" / doc_id
        if cr_dir.exists() and not any(cr_dir.iterdir()):
            cr_dir.rmdir()
            deleted_files.append(str(cr_dir.relative_to(PROJECT_ROOT)))

    # Delete .meta file
    meta_path = get_meta_path(doc_id, doc_type)
    if meta_path.exists():
        meta_path.unlink()
        deleted_files.append(str(meta_path.relative_to(PROJECT_ROOT)))

    # Delete .audit file
    audit_dir = QMS_ROOT / ".audit" / doc_type
    audit_path = audit_dir / f"{doc_id}.jsonl"
    if audit_path.exists():
        audit_path.unlink()
        deleted_files.append(str(audit_path.relative_to(PROJECT_ROOT)))

    # Also clean up any workspace copies
    for username in ["lead", "claude", "qa"]:
        workspace_path = Path(f".claude/users/{username}/workspace/{doc_id}.md")
        full_workspace_path = PROJECT_ROOT / workspace_path
        if full_workspace_path.exists():
            full_workspace_path.unlink()
            deleted_files.append(str(workspace_path))

    # Clean up inbox tasks
    for username in os.listdir(PROJECT_ROOT / ".claude" / "users"):
        inbox_dir = PROJECT_ROOT / ".claude" / "users" / username / "inbox"
        if inbox_dir.exists():
            for task_file in inbox_dir.glob(f"task-{doc_id}-*.md"):
                task_file.unlink()
                deleted_files.append(str(task_file.relative_to(PROJECT_ROOT)))

    print(f"Canceled: {doc_id}")
    print("Deleted:")
    for f in deleted_files:
        print(f"  - {f}")

    return 0


# =============================================================================
# New Audit/History Commands
# =============================================================================

def cmd_history(args):
    """Show full audit history for a document."""
    user = get_current_user(args)

    if not verify_user_identity(user):
        return 1

    doc_id = args.doc_id
    doc_type = get_doc_type(doc_id)

    # Read audit log
    events = read_audit_log(doc_id, doc_type)

    if not events:
        # Check if document exists but has no audit log (pre-migration)
        draft_path = get_doc_path(doc_id, draft=True)
        effective_path = get_doc_path(doc_id, draft=False)
        if draft_path.exists() or effective_path.exists():
            print(f"Document {doc_id} exists but has no audit log.")
            print("Run 'qms migrate' to generate audit logs from frontmatter history.")
        else:
            print(f"Document not found: {doc_id}")
        return 1

    print(f"Audit History: {doc_id}")
    print("=" * 70)
    print(format_audit_history(events))

    return 0


def cmd_comments(args):
    """Show review/approval comments for a document."""
    user = get_current_user(args)

    if not verify_user_identity(user):
        return 1

    doc_id = args.doc_id
    doc_type = get_doc_type(doc_id)

    # Get document status to enforce visibility rules
    draft_path = get_doc_path(doc_id, draft=True)
    effective_path = get_doc_path(doc_id, draft=False)

    if draft_path.exists():
        frontmatter, _ = read_document(draft_path)
    elif effective_path.exists():
        frontmatter, _ = read_document(effective_path)
    else:
        print(f"Document not found: {doc_id}")
        return 1

    status = frontmatter.get("status", "")
    version = frontmatter.get("version", "")

    # Enforce visibility rule: comments only visible after REVIEWED state
    review_states = {"IN_REVIEW", "IN_PRE_REVIEW", "IN_POST_REVIEW"}
    if status in review_states:
        print(f"Comments are not visible while document is in {status}.")
        print("Comments become visible after review phase completes.")
        return 1

    # Get comments
    if args.version:
        comments = get_comments(doc_id, doc_type, version=args.version)
        print(f"Comments for {doc_id} v{args.version}:")
    else:
        comments = get_latest_version_comments(doc_id, doc_type, version)
        print(f"Comments for {doc_id} (current version {version}):")

    print("=" * 70)

    if not comments:
        print("No comments found.")
        # Check if there's frontmatter history (pre-migration)
        if frontmatter.get("review_history") or frontmatter.get("approval_history"):
            print("\nNote: This document has legacy frontmatter comments.")
            print("Run 'qms migrate' to convert them to the new audit system.")
    else:
        print(format_comments(comments))

    return 0


def cmd_migrate(args):
    """Migrate existing documents to new metadata architecture."""
    user = get_current_user(args)

    if not verify_user_identity(user):
        return 1

    # Only lead can run migration
    if user != "lead":
        print("Error: Only 'lead' can run document migration.")
        return 1

    dry_run = args.dry_run if hasattr(args, 'dry_run') else False

    if dry_run:
        print("DRY RUN - No changes will be made")
        print("=" * 70)

    # Find all documents
    migrated = 0
    skipped = 0
    errors = 0

    for doc_type, config in DOCUMENT_TYPES.items():
        doc_path = QMS_ROOT / config["path"]
        if not doc_path.exists():
            continue

        # Find all markdown files
        for md_file in doc_path.rglob("*.md"):
            # Skip archive
            if ".archive" in str(md_file):
                continue

            try:
                frontmatter, body = read_document(md_file)
                doc_id = frontmatter.get("doc_id")

                if not doc_id:
                    continue

                # Check if already migrated (has .meta file)
                actual_type = get_doc_type(doc_id)
                meta_path = get_meta_path(doc_id, actual_type)

                if meta_path.exists() and not args.force:
                    skipped += 1
                    continue

                print(f"Migrating: {doc_id}")

                if not dry_run:
                    # Create .meta file
                    meta = create_initial_meta(
                        doc_id=doc_id,
                        doc_type=frontmatter.get("document_type", actual_type),
                        version=frontmatter.get("version", "0.1"),
                        status=frontmatter.get("status", "DRAFT"),
                        executable=frontmatter.get("executable", False),
                        responsible_user=frontmatter.get("responsible_user")
                    )
                    meta["checked_out"] = frontmatter.get("checked_out", False)
                    meta["checked_out_date"] = frontmatter.get("checked_out_date")
                    meta["effective_version"] = frontmatter.get("effective_version")
                    meta["supersedes"] = frontmatter.get("supersedes")

                    write_meta(doc_id, actual_type, meta)

                    # Convert review_history to audit events
                    for review in frontmatter.get("review_history", []):
                        review_type = review.get("type", "REVIEW")
                        version = frontmatter.get("version", "0.1")

                        # Log routing event
                        assignees = [a.get("user") for a in review.get("assignees", [])]
                        log_route_review(doc_id, actual_type, "system", version, assignees, review_type)

                        # Log individual reviews
                        for assignee in review.get("assignees", []):
                            if assignee.get("status") == "COMPLETE":
                                outcome = assignee.get("outcome", "RECOMMEND")
                                comment = assignee.get("comments", "")
                                log_review(doc_id, actual_type, assignee.get("user"), version, outcome, comment)

                    # Convert approval_history to audit events
                    for approval in frontmatter.get("approval_history", []):
                        approval_type = approval.get("type", "APPROVAL")
                        version = frontmatter.get("version", "0.1")

                        # Log routing event
                        assignees = [a.get("user") for a in approval.get("assignees", [])]
                        log_route_approval(doc_id, actual_type, "system", version, assignees, approval_type)

                        # Log individual approvals/rejections
                        for assignee in approval.get("assignees", []):
                            if assignee.get("status") == "APPROVED":
                                log_approve(doc_id, actual_type, assignee.get("user"), version)
                            elif assignee.get("status") == "REJECTED":
                                comment = assignee.get("comments", "")
                                log_reject(doc_id, actual_type, assignee.get("user"), version, comment)

                migrated += 1

            except Exception as e:
                print(f"  Error: {e}")
                errors += 1

    print()
    print("=" * 70)
    print(f"Migration complete:")
    print(f"  Migrated: {migrated}")
    print(f"  Skipped (already migrated): {skipped}")
    print(f"  Errors: {errors}")

    if dry_run:
        print("\nThis was a dry run. Run without --dry-run to apply changes.")

    return 0 if errors == 0 else 1


def cmd_verify_migration(args):
    """Verify migration completed successfully."""
    user = get_current_user(args)

    if not verify_user_identity(user):
        return 1

    print("Verifying migration...")
    print("=" * 70)

    issues = []

    for doc_type, config in DOCUMENT_TYPES.items():
        doc_path = QMS_ROOT / config["path"]
        if not doc_path.exists():
            continue

        for md_file in doc_path.rglob("*.md"):
            if ".archive" in str(md_file):
                continue

            try:
                frontmatter, _ = read_document(md_file)
                doc_id = frontmatter.get("doc_id")

                if not doc_id:
                    continue

                actual_type = get_doc_type(doc_id)
                meta_path = get_meta_path(doc_id, actual_type)

                if not meta_path.exists():
                    issues.append(f"{doc_id}: Missing .meta file")
                else:
                    # Verify meta matches frontmatter
                    meta = read_meta(doc_id, actual_type)
                    if meta:
                        if meta.get("version") != frontmatter.get("version"):
                            issues.append(f"{doc_id}: Version mismatch (meta={meta.get('version')}, fm={frontmatter.get('version')})")
                        if meta.get("status") != frontmatter.get("status"):
                            issues.append(f"{doc_id}: Status mismatch (meta={meta.get('status')}, fm={frontmatter.get('status')})")

            except Exception as e:
                issues.append(f"{md_file}: Error - {e}")

    if issues:
        print("Issues found:")
        for issue in issues:
            print(f"  - {issue}")
        return 1
    else:
        print("All documents verified successfully.")
        return 0

