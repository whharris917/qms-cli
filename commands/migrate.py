"""
QMS Migrate Command

Migrates existing documents to new metadata architecture.

Created as part of CR-026: QMS CLI Extensibility Refactoring
"""
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from registry import CommandRegistry
from qms_config import DOCUMENT_TYPES
from qms_paths import QMS_ROOT, get_doc_type
from qms_io import read_document
from qms_auth import get_current_user, verify_user_identity
from qms_meta import (
    read_meta, write_meta, create_initial_meta, get_meta_path
)
from qms_audit import (
    log_route_review, log_route_approval, log_review, log_approve, log_reject
)


@CommandRegistry.register(
    name="migrate",
    help="Migrate existing documents to new metadata architecture",
    arguments=[
        {"flags": ["--dry-run"], "help": "Preview migration without making changes", "action": "store_true"},
        {"flags": ["--force"], "help": "Re-migrate already-migrated documents", "action": "store_true"},
    ],
)
def cmd_migrate(args) -> int:
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
