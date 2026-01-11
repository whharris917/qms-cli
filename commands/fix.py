"""
QMS Fix Command

Administrative fix for EFFECTIVE documents (QA/lead only).

Created as part of CR-026: QMS CLI Extensibility Refactoring
"""
import re
import sys
from datetime import datetime
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from registry import CommandRegistry
from qms_paths import get_doc_path
from qms_io import read_document, write_document
from qms_auth import get_current_user


@CommandRegistry.register(
    name="fix",
    help="Administrative fix for EFFECTIVE documents (QA/lead only)",
    requires_doc_id=True,
    doc_id_help="Document ID to fix",
)
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
