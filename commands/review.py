"""
QMS Review Command

Submits a review for a document.

Created as part of CR-026: QMS CLI Extensibility Refactoring
"""
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from registry import CommandRegistry
from qms_config import Status
from qms_paths import get_doc_type, get_doc_path, get_inbox_path
from qms_auth import get_current_user, check_permission, verify_user_identity
from qms_meta import read_meta, write_meta, update_meta_review_complete
from qms_audit import log_review, log_status_change
from workflow import get_workflow_engine


@CommandRegistry.register(
    name="review",
    help="Submit a review for a document",
    requires_doc_id=True,
    doc_id_help="Document ID to review",
    arguments=[
        {"flags": ["--recommend"], "help": "Recommend for approval", "action": "store_true"},
        {"flags": ["--request-updates"], "help": "Request updates before approval", "action": "store_true"},
        {"flags": ["--comment"], "help": "Review comment", "required": False},
    ],
)
def cmd_review(args) -> int:
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

    # Use WorkflowEngine to verify document is in a review state (CR-026)
    engine = get_workflow_engine()
    if not engine.is_review_status(current_status):
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
        # Transition to REVIEWED state using WorkflowEngine (CR-026)
        new_status = engine.get_reviewed_status(current_status)
        if new_status:
            print(f"All reviews complete. Status: {current_status.value} -> {new_status.value}")
            # Log status change (CAPA-3: audit trail completeness)
            log_status_change(doc_id, doc_type, user, version, current_status.value, new_status.value)

    meta = update_meta_review_complete(
        meta, user, remaining_assignees, outcome,
        new_status=new_status.value if new_status else None
    )
    write_meta(doc_id, doc_type, meta)

    # Remove task from inbox
    inbox_path = get_inbox_path(user)
    for task_file in inbox_path.glob(f"task-{doc_id}-*.md"):
        task_file.unlink()

    print(f"Review submitted for {doc_id}")

    return 0
