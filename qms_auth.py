"""
QMS CLI Authentication and Authorization Module

Contains functions for user authentication, permission checking,
and access control.

CR-036: Added agent-based user management. Users are now defined via:
  - Hardcoded: lead and claude are always administrators
  - Agent files: .claude/agents/{user}.md with group: frontmatter
"""
import sys
from pathlib import Path
from typing import List, Optional

from qms_config import (
    PERMISSIONS, GROUP_GUIDANCE, GROUP_HIERARCHY
)


# =============================================================================
# Hardcoded Administrator Users
# =============================================================================

# These users are always administrators and do not require agent files
HARDCODED_ADMINS = {"lead", "claude"}


# =============================================================================
# Agent File Management
# =============================================================================

def get_agents_dir() -> Optional[Path]:
    """Get the .claude/agents directory, if project root can be found."""
    try:
        from qms_paths import PROJECT_ROOT
        return PROJECT_ROOT / ".claude" / "agents"
    except (ImportError, FileNotFoundError):
        return None


def get_agent_file_path(user: str) -> Optional[Path]:
    """Get the path to a user's agent definition file."""
    agents_dir = get_agents_dir()
    if agents_dir:
        return agents_dir / f"{user}.md"
    return None


def read_agent_group(user: str) -> Optional[str]:
    """
    Read the group assignment from a user's agent definition file.

    Returns the group if found, None if file doesn't exist or has no group.
    """
    agent_path = get_agent_file_path(user)
    if not agent_path or not agent_path.exists():
        return None

    try:
        from qms_io import read_document
        frontmatter, _ = read_document(agent_path)
        return frontmatter.get("group")
    except Exception:
        return None


# =============================================================================
# User Identity
# =============================================================================

def get_current_user(args) -> str:
    """Get the current QMS user from the --user command-line argument."""
    user = getattr(args, 'user', None)
    if not user:
        print("Error: --user argument is required.")
        print("Specify your identity with: --user <username>")
        print()
        print("Hardcoded administrators: lead, claude")
        print("Other users: defined via .claude/agents/{user}.md")
        print()
        print("To add a new user: python qms-cli/qms.py user --add <username> --group <group>")
        sys.exit(1)
    return user


def get_user_group(user: str) -> str:
    """
    Get the group a user belongs to.

    Resolution order:
    1. Hardcoded admins (lead, claude) -> administrator
    2. Agent file with group: frontmatter -> that group
    3. Unknown -> "unknown"
    """
    # 1. Hardcoded administrators
    if user in HARDCODED_ADMINS:
        return "administrator"

    # 2. Agent file lookup
    agent_group = read_agent_group(user)
    if agent_group:
        return agent_group

    return "unknown"


def verify_user_identity(user: str) -> bool:
    """
    Verify that the user is a valid QMS user.

    A user is valid if:
    1. They are a hardcoded admin (lead, claude), or
    2. They have an agent file with a valid group
    """
    # Hardcoded admins are always valid
    if user in HARDCODED_ADMINS:
        return True

    # Check for agent file
    agent_group = read_agent_group(user)
    if agent_group:
        valid_groups = {"administrator", "initiator", "quality", "reviewer"}
        if agent_group in valid_groups:
            return True
        else:
            print(f"""
Error: Invalid group '{agent_group}' in agent file for user '{user}'.

Valid groups: administrator, initiator, quality, reviewer

Check .claude/agents/{user}.md and ensure the 'group:' frontmatter is valid.
""")
            return False

    # User not found - provide helpful error
    agent_path = get_agent_file_path(user)
    print(f"""
Error: User '{user}' not found.

To use qms-cli, you must be either:
  - A hardcoded administrator: lead, claude
  - Defined via an agent file: .claude/agents/{user}.md

To add this user, run:
  python qms-cli/qms.py user --add {user} --group <group>

Or create the agent file manually at:
  {agent_path or f'.claude/agents/{user}.md'}

With frontmatter:
  ---
  name: {user}
  group: <administrator|initiator|quality|reviewer>
  ---
""")
    return False


# =============================================================================
# Permission Checking
# =============================================================================

def has_group_permission(user_group: str, allowed_groups: list) -> bool:
    """
    Check if a user's group has permission, considering hierarchy.
    Higher groups inherit permissions from lower groups.
    Hierarchy: administrator > initiator > quality > reviewer
    """
    if user_group in allowed_groups:
        return True

    # Check hierarchy inheritance
    try:
        user_level = GROUP_HIERARCHY.index(user_group)
        for allowed in allowed_groups:
            if allowed in GROUP_HIERARCHY:
                allowed_level = GROUP_HIERARCHY.index(allowed)
                if user_level < allowed_level:  # Lower index = higher privilege
                    return True
    except ValueError:
        pass  # Unknown group, no hierarchy benefit

    return False


def check_permission(user: str, command: str, doc_owner: str = None, assigned_users: List[str] = None) -> tuple[bool, str]:
    """
    Check if user has permission to execute a command.
    Returns (allowed, error_message).
    """
    if command not in PERMISSIONS:
        return True, ""  # Unknown command, let it through

    perm = PERMISSIONS[command]
    user_group = get_user_group(user)
    allowed_groups = perm.get("groups", [])

    # Check group membership with hierarchy
    if not has_group_permission(user_group, allowed_groups):
        group_names = ", ".join(allowed_groups)
        error = f"""
Permission Denied: '{command}' command

Your role: {user_group} ({user})
Required role(s): {group_names}

{GROUP_GUIDANCE.get(user_group, '')}
"""
        return False, error

    # Check owner requirement (CC-001: strict ownership, no cross-user exception)
    if perm.get("owner_only") and doc_owner and doc_owner != user:
        error = f"""
Permission Denied: '{command}' command

You ({user}) are not the responsible user for this document.
Responsible user: {doc_owner}

Only the document owner can perform this action.
"""
        return False, error

    # Check assignment requirement
    if perm.get("assigned_only") and assigned_users is not None:
        if user not in assigned_users:
            error = f"""
Permission Denied: '{command}' command

You ({user}) are not assigned to this workflow.
Assigned users: {', '.join(assigned_users) if assigned_users else 'None'}

You can only {command} documents you are assigned to.
Check your inbox for assigned tasks: qms --user {user} inbox
"""
            return False, error

    return True, ""


# =============================================================================
# Folder Access Control
# =============================================================================

def verify_folder_access(user: str, target_user: str, operation: str) -> bool:
    """Verify that user has access to target_user's folder."""
    if user != target_user:
        print(f"""
Error: Access denied.

User '{user}' cannot {operation} for user '{target_user}'.
You can only access your own inbox and workspace.

Commands:
  qms --user {user} inbox      - View your pending tasks
  qms --user {user} workspace  - View your checked-out documents
""")
        return False
    return True
