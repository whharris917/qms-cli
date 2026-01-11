"""
Test Command Registry

Tests for the CommandRegistry class and command registration.

Created as part of CR-026: QMS CLI Extensibility Refactoring
"""
import sys
from pathlib import Path

import pytest

# Add qms-cli to path for imports
QMS_CLI_DIR = Path(__file__).parent.parent
if str(QMS_CLI_DIR) not in sys.path:
    sys.path.insert(0, str(QMS_CLI_DIR))


class TestCommandRegistry:
    """Tests for the CommandRegistry class."""

    def test_all_commands_registered(self):
        """Verify all 21 commands are registered in the CommandRegistry."""
        from registry import CommandRegistry
        import commands  # noqa: F401 - triggers registration

        expected_commands = [
            "create",
            "read",
            "checkout",
            "checkin",
            "route",
            "assign",
            "review",
            "approve",
            "reject",
            "release",
            "revert",
            "close",
            "status",
            "inbox",
            "workspace",
            "fix",
            "cancel",
            "history",
            "comments",
            "migrate",
            "verify-migration",
        ]

        registered_commands = [spec.name for spec in CommandRegistry.get_all_commands()]

        for cmd in expected_commands:
            assert cmd in registered_commands, f"Command '{cmd}' not registered"

    def test_command_count(self):
        """Verify exactly 21 commands are registered."""
        from registry import CommandRegistry
        import commands  # noqa: F401 - triggers registration

        assert CommandRegistry.command_count() == 21, \
            f"Expected 21 commands, got {CommandRegistry.command_count()}"

    def test_get_command_returns_spec(self):
        """Verify get_command returns a CommandSpec."""
        from registry import CommandRegistry, CommandSpec
        import commands  # noqa: F401 - triggers registration

        spec = CommandRegistry.get_command("status")

        assert spec is not None
        assert isinstance(spec, CommandSpec)
        assert spec.name == "status"
        assert callable(spec.handler)

    def test_get_command_returns_none_for_unknown(self):
        """Verify get_command returns None for unknown commands."""
        from registry import CommandRegistry

        spec = CommandRegistry.get_command("nonexistent")

        assert spec is None

    def test_get_handler_returns_callable(self):
        """Verify get_handler returns a callable function."""
        from registry import CommandRegistry
        import commands  # noqa: F401 - triggers registration

        handler = CommandRegistry.get_handler("inbox")

        assert handler is not None
        assert callable(handler)

    def test_all_handlers_are_callable(self):
        """Verify all registered handlers are callable."""
        from registry import CommandRegistry
        import commands  # noqa: F401 - triggers registration

        for spec in CommandRegistry.get_all_commands():
            assert callable(spec.handler), f"Handler for '{spec.name}' is not callable"


class TestArgumentSpec:
    """Tests for the ArgumentSpec class."""

    def test_from_dict_basic(self):
        """Verify ArgumentSpec.from_dict works with basic args."""
        from registry import ArgumentSpec

        spec = ArgumentSpec.from_dict({
            "flags": ["--title"],
            "help": "Document title",
        })

        assert spec.flags == ["--title"]
        assert spec.help == "Document title"
        assert spec.action is None
        assert spec.required is False

    def test_from_dict_with_action(self):
        """Verify ArgumentSpec.from_dict handles action."""
        from registry import ArgumentSpec

        spec = ArgumentSpec.from_dict({
            "flags": ["--draft"],
            "help": "Read draft version",
            "action": "store_true",
        })

        assert spec.action == "store_true"

    def test_from_dict_with_nargs(self):
        """Verify ArgumentSpec.from_dict handles nargs."""
        from registry import ArgumentSpec

        spec = ArgumentSpec.from_dict({
            "flags": ["--assignees"],
            "help": "Users to assign",
            "nargs": "+",
        })

        assert spec.nargs == "+"


class TestCommandSpec:
    """Tests for the CommandSpec class."""

    def test_command_spec_has_required_fields(self):
        """Verify all registered commands have required fields."""
        from registry import CommandRegistry
        import commands  # noqa: F401 - triggers registration

        for spec in CommandRegistry.get_all_commands():
            assert spec.name, f"Command missing name"
            assert spec.handler, f"Command '{spec.name}' missing handler"
            assert spec.help, f"Command '{spec.name}' missing help text"


class TestRegistration:
    """Tests for the registration decorator."""

    def test_register_decorator_works(self):
        """Verify the @register decorator adds commands to registry."""
        from registry import CommandRegistry

        # Count before
        count_before = CommandRegistry.command_count()

        # Define a test command
        @CommandRegistry.register(
            name="test_command_unique",
            help="Test command",
        )
        def test_cmd(args):
            return 0

        # Count after
        count_after = CommandRegistry.command_count()

        assert count_after == count_before + 1
        assert CommandRegistry.get_command("test_command_unique") is not None

    def test_requires_doc_id_flag(self):
        """Verify requires_doc_id flag is set correctly."""
        from registry import CommandRegistry
        import commands  # noqa: F401 - triggers registration

        # Commands that require doc_id
        doc_id_commands = ["status", "read", "checkout", "checkin", "route",
                           "assign", "review", "approve", "reject", "release",
                           "revert", "close", "fix", "cancel", "history", "comments"]

        # Commands that don't require doc_id
        no_doc_id_commands = ["create", "inbox", "workspace", "migrate", "verify-migration"]

        for cmd_name in doc_id_commands:
            spec = CommandRegistry.get_command(cmd_name)
            if spec:  # Some might not be registered in this test
                assert spec.requires_doc_id, f"Command '{cmd_name}' should require doc_id"

        for cmd_name in no_doc_id_commands:
            spec = CommandRegistry.get_command(cmd_name)
            if spec:
                assert not spec.requires_doc_id, f"Command '{cmd_name}' should not require doc_id"
