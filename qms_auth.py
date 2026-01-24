"""
QMS CLI Authentication and Authorization Module

Contains functions for user authentication, permission checking,
and access control.
"""
import sys
from typing import List

from qms_config import (
    VALID_USERS, USER_GROUPS, PERMISSIONS, GROUP_GUIDANCE, GROUP_HIERARCHY
)


# =============================================================================
# User Identity
# =============================================================================

def get_current_user(args) -> str:
    """Get the current QMS user from the --user command-line argument."""
    user = getattr(args, 'user', None)
    if not user:
        print("Error: --user argument is required.")
        print("Specify your identity with: --user <username>")
        print("Valid users: lead, claude, qa, bu, tu_ui, tu_scene, tu_sketch, tu_sim")
        sys.exit(1)
    return user


def get_user_group(user: str) -> str:
    """Get the group a user belongs to."""
    for group_name, members in USER_GROUPS.items():
        if user in members:
            return group_name
    return "unknown"


def verify_user_identity(user: str) -> bool:
    """Verify that the user is a valid QMS user."""
    if user not in VALID_USERS:
        print(f"""
Error: '{user}' is not a valid QMS user.

Valid users by group:
  Administrator: {', '.join(sorted(USER_GROUPS['administrator']))}
  Initiator:     {', '.join(sorted(USER_GROUPS['initiator']))}
  Quality:       {', '.join(sorted(USER_GROUPS['quality']))}
  Reviewer:      {', '.join(sorted(USER_GROUPS['reviewer']))}

Specify your identity with: qms --user <username> <command>
""")
        return False
    return True


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
