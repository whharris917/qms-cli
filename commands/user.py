"""
QMS User Command

Manages QMS users via agent definition files.

Created as part of CR-036: Add qms-cli initialization and bootstrapping functionality
"""
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from registry import CommandRegistry


# =============================================================================
# Constants
# =============================================================================

VALID_GROUPS = {"administrator", "initiator", "quality", "reviewer"}


# =============================================================================
# Helper Functions
# =============================================================================

def get_project_paths():
    """Get project root and related paths."""
    from qms_paths import PROJECT_ROOT
    return {
        "root": PROJECT_ROOT,
        "agents_dir": PROJECT_ROOT / ".claude" / "agents",
        "users_dir": PROJECT_ROOT / ".claude" / "users",
    }


def create_agent_file(agents_dir: Path, username: str, group: str) -> Path:
    """Create an agent definition file for a user."""
    agents_dir.mkdir(parents=True, exist_ok=True)

    agent_path = agents_dir / f"{username}.md"

    content = f"""---
name: {username}
group: {group}
description: QMS user
---

# {username.upper()} Agent

You are the {username} user for this QMS project.

## Group

You belong to the **{group}** group.

## Commands

Check your inbox:
```
python qms-cli/qms.py --user {username} inbox
```

Check your workspace:
```
python qms-cli/qms.py --user {username} workspace
```
"""

    with open(agent_path, "w", encoding="utf-8") as f:
        f.write(content)

    return agent_path


def create_user_directories(users_dir: Path, username: str) -> tuple[Path, Path]:
    """Create workspace and inbox directories for a user."""
    workspace = users_dir / username / "workspace"
    inbox = users_dir / username / "inbox"

    workspace.mkdir(parents=True, exist_ok=True)
    inbox.mkdir(parents=True, exist_ok=True)

    return workspace, inbox


# =============================================================================
# User Command
# =============================================================================

@CommandRegistry.register(
    name="user",
    help="Manage QMS users (administrator only)",
    arguments=[
        {"flags": ["--add"], "help": "Username to add"},
        {"flags": ["--group"], "help": "Group for new user (administrator, initiator, quality, reviewer)"},
        {"flags": ["--list"], "action": "store_true", "help": "List all users"},
    ],
)
def cmd_user(args) -> int:
    """
    Manage QMS users (administrator only).

    Add a new user:
        qms --user lead user --add alice --group reviewer

    List users:
        qms --user lead user --list
    """
    from qms_auth import get_current_user, verify_user_identity, get_user_group

    # Require --user and verify identity
    user = get_current_user(args)  # Exits if --user not provided
    if not verify_user_identity(user):
        return 1

    # Verify administrator permission
    user_group = get_user_group(user)
    if user_group != "administrator":
        print(f"""
Error: Permission denied.

The 'user' command requires administrator privileges.
Your role: {user_group} ({user})

Only administrators (lead, claude) can manage users.
""")
        return 1

    # Handle --list
    if getattr(args, 'list', False):
        return list_users()

    # Handle --add
    add_username = getattr(args, 'add', None)
    if add_username:
        group = getattr(args, 'group', None)
        return add_user(add_username, group)

    # No action specified
    print("Usage:")
    print("  qms --user <admin> user --add <username> --group <group>  Add a new user")
    print("  qms --user <admin> user --list                            List all users")
    print()
    print("Valid groups: administrator, initiator, quality, reviewer")
    return 1


def add_user(username: str, group: str) -> int:
    """Add a new user to the QMS."""
    from qms_auth import HARDCODED_ADMINS

    # Validate username
    if not username:
        print("Error: Username is required.")
        print("Usage: qms user --add <username> --group <group>")
        return 1

    # Check if username is a hardcoded admin
    if username in HARDCODED_ADMINS:
        print(f"Error: '{username}' is a hardcoded administrator.")
        print("Hardcoded admins do not need agent files.")
        return 1

    # Validate group
    if not group:
        print("Error: --group is required when adding a user.")
        print("Usage: qms user --add <username> --group <group>")
        print()
        print("Valid groups: administrator, initiator, quality, reviewer")
        return 1

    if group not in VALID_GROUPS:
        print(f"Error: Invalid group '{group}'.")
        print()
        print("Valid groups:")
        print("  administrator - Full system access")
        print("  initiator     - Create, checkout, checkin, route documents")
        print("  quality       - Assign reviewers, review, approve, reject")
        print("  reviewer      - Review, approve, reject when assigned")
        return 1

    # Get paths
    try:
        paths = get_project_paths()
    except FileNotFoundError as e:
        print(f"Error: {e}")
        print("Run 'qms init' to initialize a QMS project first.")
        return 1

    # Check if user already exists
    agent_path = paths["agents_dir"] / f"{username}.md"
    if agent_path.exists():
        print(f"Error: User '{username}' already exists.")
        print(f"Agent file: {agent_path}")
        return 1

    # Create user
    print(f"Adding user '{username}' to group '{group}'...")

    try:
        agent_path = create_agent_file(paths["agents_dir"], username, group)
        print(f"  Created: {agent_path}")

        workspace, inbox = create_user_directories(paths["users_dir"], username)
        print(f"  Created: {workspace}")
        print(f"  Created: {inbox}")
    except Exception as e:
        print(f"Error: Failed to create user: {e}")
        return 1

    print()
    print(f"User '{username}' added successfully!")
    print()
    print("Commands for this user:")
    print(f"  python qms-cli/qms.py --user {username} inbox")
    print(f"  python qms-cli/qms.py --user {username} workspace")

    return 0


def list_users() -> int:
    """List all QMS users."""
    from qms_auth import HARDCODED_ADMINS, read_agent_group

    try:
        paths = get_project_paths()
    except FileNotFoundError as e:
        print(f"Error: {e}")
        return 1

    print("QMS Users:")
    print("-" * 40)

    # Hardcoded admins
    print()
    print("Hardcoded Administrators:")
    for user in sorted(HARDCODED_ADMINS):
        print(f"  {user}: administrator")

    # Agent file users
    agents_dir = paths["agents_dir"]
    if agents_dir.exists():
        agent_files = list(agents_dir.glob("*.md"))
        if agent_files:
            print()
            print("Agent File Users:")
            for agent_file in sorted(agent_files):
                username = agent_file.stem
                group = read_agent_group(username) or "unknown"
                print(f"  {username}: {group}")

    return 0
