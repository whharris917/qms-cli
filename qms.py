#!/usr/bin/env python3
"""
QMS - Quality Management System CLI

Document control system for the Flow State project.
See SOP-001 for complete documentation.

Usage:
    python qms-cli/qms.py <command> [options]

Commands:
    create, read, checkout, checkin, route, review, approve, reject,
    release, revert, close, status, inbox, workspace

Architecture (CR-026):
    Each command is defined in its own file under commands/ and self-registers
    via the CommandRegistry decorator. This module uses the registry for
    command discovery and dispatch while maintaining manual argparse definitions
    for complex argument configurations.
"""

import argparse
import sys

# Re-export functions from sub-modules for backward compatibility
# (Used by tests and external scripts that import from qms directly)
from qms_paths import (
    get_doc_type, get_doc_path, get_archive_path,
    get_workspace_path, get_inbox_path, get_next_number
)
from qms_io import (
    parse_frontmatter, serialize_frontmatter, read_document, write_document,
    filter_author_frontmatter
)
from qms_auth import (
    get_user_group, check_permission, verify_user_identity, verify_folder_access
)

# Import registry and commands package to trigger registration
from registry import CommandRegistry
import commands  # noqa: F401 - import triggers registration


# =============================================================================
# Main
# =============================================================================
def main():
    parser = argparse.ArgumentParser(
        description="QMS - Quality Management System CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  qms --user claude create SOP --title "New Procedure"
  qms --user claude checkout SOP-001
  qms --user claude route SOP-001 --review
  qms --user qa review SOP-001 --recommend --comment "Looks good"
  qms --user qa approve SOP-001
  qms --user claude status SOP-001
  qms --user qa inbox
  qms --user claude workspace

Valid users:
  Initiators: lead, claude
  QA:         qa
  Reviewers:  tu_ui, tu_scene, tu_sketch, tu_sim, bu
        """
    )

    # Global --user argument (required for most commands)
    parser.add_argument("--user", "-u", required=True,
                        help="Your QMS identity (required)")

    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    # create
    p_create = subparsers.add_parser("create", help="Create a new document")
    p_create.add_argument("type", help="Document type (SOP, CR, INV, RS, DS, etc.)")
    p_create.add_argument("--title", help="Document title")
    p_create.add_argument("--parent", help="Parent document ID (required for VAR/TP types)")
    p_create.add_argument("--name", help="Name for TEMPLATE type (e.g., CR, SOP)")  # CR-032

    # read
    p_read = subparsers.add_parser("read", help="Read a document")
    p_read.add_argument("doc_id", help="Document ID")
    p_read.add_argument("--draft", action="store_true", help="Read draft version")
    p_read.add_argument("--version", help="Read specific version (e.g., 1.0)")

    # checkout
    p_checkout = subparsers.add_parser("checkout", help="Check out a document")
    p_checkout.add_argument("doc_id", help="Document ID")

    # checkin
    p_checkin = subparsers.add_parser("checkin", help="Check in a document")
    p_checkin.add_argument("doc_id", help="Document ID")

    # route
    p_route = subparsers.add_parser("route", help="Route document for review/approval")
    p_route.add_argument("doc_id", help="Document ID")
    p_route.add_argument("--review", action="store_true", help="Route for review (pre/post inferred from status)")
    p_route.add_argument("--approval", action="store_true", help="Route for approval (pre/post inferred from status)")
    p_route.add_argument("--assign", nargs="+", help="Users to assign (optional, defaults to QA)")
    p_route.add_argument("--retire", action="store_true", help="Retirement approval (leads to RETIRED instead of EFFECTIVE/CLOSED)")

    # assign
    p_assign = subparsers.add_parser("assign", help="Add reviewers/approvers to active workflow (QA only)")
    p_assign.add_argument("doc_id", help="Document ID")
    p_assign.add_argument("--assignees", nargs="+", required=True, help="Users to add to workflow")

    # review
    p_review = subparsers.add_parser("review", help="Submit a review")
    p_review.add_argument("doc_id", help="Document ID")
    p_review.add_argument("--comment", required=True, help="Review comments")
    review_outcome = p_review.add_mutually_exclusive_group(required=True)
    review_outcome.add_argument("--recommend", action="store_true", help="Recommend for approval")
    review_outcome.add_argument("--request-updates", action="store_true", help="Request updates before approval")

    # approve
    p_approve = subparsers.add_parser("approve", help="Approve a document")
    p_approve.add_argument("doc_id", help="Document ID")

    # reject
    p_reject = subparsers.add_parser("reject", help="Reject a document")
    p_reject.add_argument("doc_id", help="Document ID")
    p_reject.add_argument("--comment", required=True, help="Rejection reason")

    # release
    p_release = subparsers.add_parser("release", help="Release for execution")
    p_release.add_argument("doc_id", help="Document ID")

    # revert
    p_revert = subparsers.add_parser("revert", help="Revert to execution")
    p_revert.add_argument("doc_id", help="Document ID")
    p_revert.add_argument("--reason", required=True, help="Revert reason")

    # close
    p_close = subparsers.add_parser("close", help="Close a document")
    p_close.add_argument("doc_id", help="Document ID")

    # status
    p_status = subparsers.add_parser("status", help="Show document status")
    p_status.add_argument("doc_id", help="Document ID")

    # inbox
    p_inbox = subparsers.add_parser("inbox", help="List inbox tasks")

    # workspace
    p_workspace = subparsers.add_parser("workspace", help="List workspace documents")

    # fix (admin)
    p_fix = subparsers.add_parser("fix", help="Administrative fix for EFFECTIVE documents (QA/lead only)")
    p_fix.add_argument("doc_id", help="Document ID to fix")

    # cancel (delete never-effective document)
    p_cancel = subparsers.add_parser("cancel", help="Cancel a never-effective document (version < 1.0)")
    p_cancel.add_argument("doc_id", help="Document ID to cancel")
    p_cancel.add_argument("--confirm", action="store_true", help="Confirm permanent deletion")

    # history (audit trail)
    p_history = subparsers.add_parser("history", help="Show full audit history for a document")
    p_history.add_argument("doc_id", help="Document ID")

    # comments
    p_comments = subparsers.add_parser("comments", help="Show review/approval comments")
    p_comments.add_argument("doc_id", help="Document ID")
    p_comments.add_argument("--version", help="Show comments for specific version (e.g., 1.1)")

    # migrate
    p_migrate = subparsers.add_parser("migrate", help="Migrate documents to new metadata architecture (lead only)")
    p_migrate.add_argument("--dry-run", action="store_true", help="Show what would be migrated without making changes")
    p_migrate.add_argument("--force", action="store_true", help="Re-migrate documents that already have .meta files")

    # verify-migration
    p_verify = subparsers.add_parser("verify-migration", help="Verify migration completed successfully")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 1

    # Use CommandRegistry for command dispatch (CR-026)
    # This enables single-file command changes while maintaining
    # the manual argparse definitions above for complex configurations
    return CommandRegistry.execute(args)


if __name__ == "__main__":
    sys.exit(main())
