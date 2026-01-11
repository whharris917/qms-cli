"""
QMS Inbox Command

Lists tasks in the current user's inbox.

Created as part of CR-026: QMS CLI Extensibility Refactoring
"""
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from registry import CommandRegistry
from qms_auth import get_current_user, verify_user_identity
from qms_paths import get_inbox_path
from qms_io import read_document


@CommandRegistry.register(
    name="inbox",
    help="List inbox tasks",
)
def cmd_inbox(args) -> int:
    """List tasks in current user's inbox."""
    user = get_current_user(args)

    if not verify_user_identity(user):
        return 1

    inbox_path = get_inbox_path(user)

    if not inbox_path.exists():
        print("Inbox is empty")
        return 0

    tasks = list(inbox_path.glob("*.md"))
    if not tasks:
        print("Inbox is empty")
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
