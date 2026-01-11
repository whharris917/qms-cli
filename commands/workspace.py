"""
QMS Workspace Command

Lists documents in the current user's workspace.

Created as part of CR-026: QMS CLI Extensibility Refactoring
"""
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from registry import CommandRegistry
from qms_auth import get_current_user, verify_user_identity
from qms_paths import USERS_ROOT
from qms_io import read_document


@CommandRegistry.register(
    name="workspace",
    help="List workspace documents",
)
def cmd_workspace(args) -> int:
    """List documents in current user's workspace."""
    user = get_current_user(args)

    if not verify_user_identity(user):
        return 1

    workspace_path = USERS_ROOT / user / "workspace"

    if not workspace_path.exists():
        print("Workspace is empty")
        return 0

    docs = list(workspace_path.glob("*.md"))
    if not docs:
        print("Workspace is empty")
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
