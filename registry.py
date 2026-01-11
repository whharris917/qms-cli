"""
QMS Command Registry

Provides decorator-based command registration for self-registering commands.
Commands register themselves when their module is imported, enabling
single-file command definition.

Created as part of CR-026: QMS CLI Extensibility Refactoring

Usage:
    @CommandRegistry.register(
        name="create",
        help="Create a new document",
        arguments=[
            {"flags": ["type"], "help": "Document type"},
            {"flags": ["--title"], "help": "Document title"},
        ],
        permission="create"
    )
    def cmd_create(ctx: CommandContext) -> int:
        # Command implementation
        return 0
"""
from dataclasses import dataclass, field
from typing import (
    Optional, List, Dict, Any, Callable, TypeVar, Union
)
import argparse


# Type for command handler functions
CommandHandler = Callable[[Any], int]  # Takes args, returns exit code


@dataclass
class ArgumentSpec:
    """Specification for a command argument."""
    flags: List[str]  # e.g., ["type"] or ["--title", "-t"]
    help: str = ""
    action: Optional[str] = None  # e.g., "store_true"
    required: bool = False
    nargs: Optional[str] = None  # e.g., "+" for one or more
    default: Any = None
    choices: Optional[List[str]] = None
    metavar: Optional[str] = None

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "ArgumentSpec":
        """Create ArgumentSpec from dictionary."""
        return cls(
            flags=d.get("flags", []),
            help=d.get("help", ""),
            action=d.get("action"),
            required=d.get("required", False),
            nargs=d.get("nargs"),
            default=d.get("default"),
            choices=d.get("choices"),
            metavar=d.get("metavar"),
        )

    def add_to_parser(self, parser: argparse.ArgumentParser) -> None:
        """Add this argument to an argparse parser."""
        kwargs = {"help": self.help}

        if self.action:
            kwargs["action"] = self.action
        if self.required:
            kwargs["required"] = self.required
        if self.nargs:
            kwargs["nargs"] = self.nargs
        if self.default is not None:
            kwargs["default"] = self.default
        if self.choices:
            kwargs["choices"] = self.choices
        if self.metavar:
            kwargs["metavar"] = self.metavar

        parser.add_argument(*self.flags, **kwargs)


@dataclass
class CommandSpec:
    """
    Specification for a registered command.

    Attributes:
        name: Command name (e.g., "create")
        handler: Function that implements the command
        help: Help text for the command
        arguments: List of argument specifications
        permission: Permission required (e.g., "create", "approve")
        requires_doc_id: Whether command requires a doc_id argument
        doc_id_help: Help text for doc_id argument
    """
    name: str
    handler: CommandHandler
    help: str = ""
    arguments: List[ArgumentSpec] = field(default_factory=list)
    permission: Optional[str] = None
    requires_doc_id: bool = False
    doc_id_help: str = "Document ID"


class CommandRegistry:
    """
    Registry for command handlers.

    Provides decorator-based registration and argparse subparser generation.
    """

    # Class-level storage for registered commands
    _commands: Dict[str, CommandSpec] = {}
    _registration_order: List[str] = []

    @classmethod
    def register(
        cls,
        name: str,
        help: str = "",
        arguments: Optional[List[Union[ArgumentSpec, Dict[str, Any]]]] = None,
        permission: Optional[str] = None,
        requires_doc_id: bool = False,
        doc_id_help: str = "Document ID",
    ) -> Callable[[CommandHandler], CommandHandler]:
        """
        Decorator to register a command handler.

        Args:
            name: Command name
            help: Help text
            arguments: List of ArgumentSpec or dicts
            permission: Required permission
            requires_doc_id: Whether to add doc_id argument
            doc_id_help: Help text for doc_id

        Returns:
            Decorator function
        """
        def decorator(func: CommandHandler) -> CommandHandler:
            # Convert dict arguments to ArgumentSpec
            arg_specs = []
            if arguments:
                for arg in arguments:
                    if isinstance(arg, ArgumentSpec):
                        arg_specs.append(arg)
                    else:
                        arg_specs.append(ArgumentSpec.from_dict(arg))

            # Create command spec
            spec = CommandSpec(
                name=name,
                handler=func,
                help=help,
                arguments=arg_specs,
                permission=permission,
                requires_doc_id=requires_doc_id,
                doc_id_help=doc_id_help,
            )

            # Register
            cls._commands[name] = spec
            if name not in cls._registration_order:
                cls._registration_order.append(name)

            return func

        return decorator

    @classmethod
    def get_command(cls, name: str) -> Optional[CommandSpec]:
        """Get a command specification by name."""
        return cls._commands.get(name)

    @classmethod
    def get_all_commands(cls) -> List[CommandSpec]:
        """Get all registered commands in registration order."""
        return [cls._commands[name] for name in cls._registration_order if name in cls._commands]

    @classmethod
    def get_handler(cls, name: str) -> Optional[CommandHandler]:
        """Get a command handler by name."""
        spec = cls.get_command(name)
        return spec.handler if spec else None

    @classmethod
    def build_subparsers(
        cls,
        parent_parser: argparse.ArgumentParser
    ) -> argparse._SubParsersAction:
        """
        Build argparse subparsers for all registered commands.

        Args:
            parent_parser: Parent ArgumentParser to add subparsers to

        Returns:
            SubParsers action object
        """
        subparsers = parent_parser.add_subparsers(dest="command", help="Command to run")

        for spec in cls.get_all_commands():
            parser = subparsers.add_parser(spec.name, help=spec.help)

            # Add doc_id if required
            if spec.requires_doc_id:
                parser.add_argument("doc_id", help=spec.doc_id_help)

            # Add other arguments
            for arg in spec.arguments:
                arg.add_to_parser(parser)

        return subparsers

    @classmethod
    def execute(cls, args: argparse.Namespace) -> int:
        """
        Execute the command specified in args.

        Args:
            args: Parsed arguments with command name

        Returns:
            Exit code from command handler
        """
        if not args.command:
            return 1

        handler = cls.get_handler(args.command)
        if not handler:
            print(f"Error: Unknown command '{args.command}'")
            return 1

        return handler(args)

    @classmethod
    def clear(cls) -> None:
        """Clear all registered commands. Primarily for testing."""
        cls._commands.clear()
        cls._registration_order.clear()

    @classmethod
    def command_count(cls) -> int:
        """Get the number of registered commands."""
        return len(cls._commands)


# =============================================================================
# Convenience functions for command discovery
# =============================================================================

def import_commands_from_directory(commands_dir: str) -> None:
    """
    Import all command modules from a directory.

    This triggers the registration of all commands via decorators.

    Args:
        commands_dir: Path to commands directory
    """
    import importlib
    import pkgutil
    from pathlib import Path

    commands_path = Path(commands_dir)
    if not commands_path.exists():
        return

    # Import all modules in the commands directory
    for module_info in pkgutil.iter_modules([str(commands_path)]):
        if not module_info.name.startswith("_"):
            try:
                importlib.import_module(f"commands.{module_info.name}")
            except ImportError as e:
                print(f"Warning: Failed to import command module {module_info.name}: {e}")


def discover_commands() -> None:
    """
    Discover and import all command modules.

    Call this during application startup to register all commands.
    """
    from pathlib import Path

    # Get the commands directory relative to this file
    commands_dir = Path(__file__).parent / "commands"
    if commands_dir.exists():
        import_commands_from_directory(str(commands_dir))
