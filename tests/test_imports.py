"""
Test Import Verification

Parameterized tests that verify all QMS CLI modules import cleanly.
These tests will catch missing imports that the linter would flag.

Created as part of CR-026: QMS CLI Extensibility Refactoring
"""
import importlib
import sys
from pathlib import Path

import pytest

# Add qms-cli to path for imports
QMS_CLI_DIR = Path(__file__).parent.parent
if str(QMS_CLI_DIR) not in sys.path:
    sys.path.insert(0, str(QMS_CLI_DIR))


# All QMS CLI modules that should import cleanly
QMS_MODULES = [
    "qms",
    "qms_config",
    "qms_paths",
    "qms_io",
    "qms_auth",
    "qms_templates",
    "qms_commands",
    "qms_meta",
    "qms_audit",
    "qms_schema",
    # CR-026 new modules
    "workflow",
    "prompts",
    "context",
    "registry",
    # CR-026 command modules
    "commands.status",
    "commands.inbox",
    "commands.workspace",
    "commands.create",
    "commands.read",
    "commands.checkout",
    "commands.checkin",
    "commands.route",
    "commands.assign",
    "commands.review",
    "commands.approve",
    "commands.reject",
    "commands.release",
    "commands.revert",
    "commands.close",
    "commands.fix",
    "commands.cancel",
    "commands.history",
    "commands.comments",
    "commands.migrate",
    "commands.verify_migration",
]


@pytest.mark.parametrize("module_name", QMS_MODULES)
def test_module_imports(module_name: str):
    """Verify each QMS module imports without error."""
    # Remove from cache if already imported (ensures fresh import)
    if module_name in sys.modules:
        del sys.modules[module_name]

    try:
        module = importlib.import_module(module_name)
        assert module is not None, f"Module {module_name} imported as None"
    except ImportError as e:
        pytest.fail(f"Failed to import {module_name}: {e}")
    except Exception as e:
        pytest.fail(f"Error importing {module_name}: {type(e).__name__}: {e}")


def test_qms_commands_has_all_commands():
    """Verify qms_commands exports all expected command functions."""
    import qms_commands

    expected_commands = [
        "cmd_create",
        "cmd_read",
        "cmd_checkout",
        "cmd_checkin",
        "cmd_route",
        "cmd_assign",
        "cmd_review",
        "cmd_approve",
        "cmd_reject",
        "cmd_release",
        "cmd_revert",
        "cmd_close",
        "cmd_status",
        "cmd_inbox",
        "cmd_workspace",
        "cmd_fix",
        "cmd_cancel",
        "cmd_history",
        "cmd_comments",
        "cmd_migrate",
        "cmd_verify_migration",
    ]

    for cmd_name in expected_commands:
        assert hasattr(qms_commands, cmd_name), f"qms_commands missing {cmd_name}"
        assert callable(getattr(qms_commands, cmd_name)), f"{cmd_name} is not callable"


def test_qms_config_has_required_exports():
    """Verify qms_config exports required constants and types."""
    import qms_config

    required_exports = [
        "Status",
        "TRANSITIONS",
        "DOCUMENT_TYPES",
        "VALID_USERS",
        "USER_GROUPS",
        "PERMISSIONS",
        "GROUP_GUIDANCE",
        "AUTHOR_FRONTMATTER_FIELDS",
    ]

    for export_name in required_exports:
        assert hasattr(qms_config, export_name), f"qms_config missing {export_name}"


def test_qms_paths_has_required_exports():
    """Verify qms_paths exports required paths and functions."""
    import qms_paths

    required_exports = [
        "PROJECT_ROOT",
        "QMS_ROOT",
        "ARCHIVE_ROOT",
        "USERS_ROOT",
        "get_doc_type",
        "get_doc_path",
        "get_archive_path",
        "get_workspace_path",
        "get_inbox_path",
        "get_next_number",
    ]

    for export_name in required_exports:
        assert hasattr(qms_paths, export_name), f"qms_paths missing {export_name}"


def test_qms_io_has_required_exports():
    """Verify qms_io exports required I/O functions."""
    import qms_io

    required_exports = [
        "parse_frontmatter",
        "serialize_frontmatter",
        "read_document",
        "write_document",
        "filter_author_frontmatter",
    ]

    for export_name in required_exports:
        assert hasattr(qms_io, export_name), f"qms_io missing {export_name}"


def test_qms_auth_has_required_exports():
    """Verify qms_auth exports required auth functions."""
    import qms_auth

    required_exports = [
        "get_current_user",
        "get_user_group",
        "check_permission",
        "verify_user_identity",
        "verify_folder_access",
    ]

    for export_name in required_exports:
        assert hasattr(qms_auth, export_name), f"qms_auth missing {export_name}"


def test_qms_templates_has_required_exports():
    """Verify qms_templates exports required template functions."""
    import qms_templates

    required_exports = [
        "load_template_for_type",
        "generate_review_task_content",
        "generate_approval_task_content",
    ]

    for export_name in required_exports:
        assert hasattr(qms_templates, export_name), f"qms_templates missing {export_name}"


def test_no_circular_imports():
    """
    Verify no circular import issues exist by importing all modules fresh.

    This test clears all QMS modules from cache and imports them in order.
    Circular imports would cause ImportError during this process.
    """
    # Clear all QMS modules from cache
    modules_to_clear = [m for m in sys.modules.keys() if m.startswith("qms")]
    for mod in modules_to_clear:
        del sys.modules[mod]

    # Import in dependency order (config first, then paths, etc.)
    import_order = [
        "qms_config",
        "qms_paths",
        "qms_io",
        "qms_auth",
        "qms_meta",
        "qms_audit",
        "qms_schema",
        "workflow",
        "prompts",
        "qms_templates",
        "context",
        "registry",
        "qms_commands",
        "qms",
    ]

    for module_name in import_order:
        try:
            importlib.import_module(module_name)
        except ImportError as e:
            pytest.fail(f"Circular import detected in {module_name}: {e}")
