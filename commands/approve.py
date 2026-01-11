"""
QMS Approve Command

Approves a document.

Created as part of CR-026: QMS CLI Extensibility Refactoring
"""
import shutil
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from registry import CommandRegistry
from qms_config import Status
from qms_paths import (
    PROJECT_ROOT, get_doc_type, get_doc_path, get_archive_path, get_inbox_path
)
from qms_io import read_document, write_document_minimal
from qms_auth import get_current_user, check_permission, verify_user_identity
from qms_meta import read_meta, write_meta, update_meta_approval
from qms_audit import log_approve, log_effective, log_retire, log_status_change
from workflow import get_workflow_engine


@CommandRegistry.register(
    name="approve",
    help="Approve a document",
    requires_doc_id=True,
    doc_id_help="Document ID to approve",
)
def cmd_approve(args) -> int:
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

    # Use WorkflowEngine to verify document is in an approval state (CR-026)
    engine = get_workflow_engine()
    if not engine.is_approval_status(current_status):
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
        # Transition to APPROVED state using WorkflowEngine (CR-026)
        new_status = engine.get_approved_status(current_status)

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
