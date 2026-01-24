"""
QMS Namespace Command

Manages SDLC namespaces for document types (RS, RTM).

Created as part of CR-034: Implement RS validation code changes
"""
import json
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from registry import CommandRegistry
from qms_paths import QMS_ROOT, PROJECT_ROOT
from qms_auth import get_current_user, verify_user_identity, get_user_group


# Path to persistent namespace configuration
NAMESPACE_CONFIG_PATH = QMS_ROOT / ".meta" / "sdlc_namespaces.json"


def load_namespaces() -> dict:
    """Load namespaces from persistent config, merged with defaults."""
    from qms_config import SDLC_NAMESPACES

    # Start with built-in defaults
    namespaces = dict(SDLC_NAMESPACES)

    # Merge with any persisted namespaces
    if NAMESPACE_CONFIG_PATH.exists():
        try:
            with open(NAMESPACE_CONFIG_PATH, "r", encoding="utf-8") as f:
                persisted = json.load(f)
                namespaces.update(persisted)
        except (json.JSONDecodeError, IOError):
            pass  # Use defaults if config is corrupted

    return namespaces


def save_namespaces(namespaces: dict) -> None:
    """Save namespaces to persistent config (excluding built-in defaults)."""
    from qms_config import SDLC_NAMESPACES

    # Only save namespaces that aren't built-in
    custom = {k: v for k, v in namespaces.items() if k not in SDLC_NAMESPACES}

    NAMESPACE_CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(NAMESPACE_CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(custom, f, indent=2)


@CommandRegistry.register(
    name="namespace",
    help="Manage SDLC namespaces",
    arguments=[
        {"flags": ["action"], "help": "Action: list, add", "nargs": "?", "default": "list"},
        {"flags": ["name"], "help": "Namespace name (for add)", "nargs": "?"},
    ],
)
def cmd_namespace(args) -> int:
    """Manage SDLC namespaces."""
    user = get_current_user(args)

    if not verify_user_identity(user):
        return 1

    action = args.action.lower() if args.action else "list"

    if action == "list":
        return cmd_namespace_list(user)
    elif action == "add":
        return cmd_namespace_add(user, args.name)
    else:
        print(f"Error: Unknown action '{action}'")
        print("Valid actions: list, add")
        return 1


def cmd_namespace_list(user: str) -> int:
    """List registered SDLC namespaces."""
    namespaces = load_namespaces()

    print("Registered SDLC Namespaces:")
    print("=" * 60)

    for name, config in sorted(namespaces.items()):
        path = config.get("path", f"SDLC-{name}")
        print(f"  {name}:")
        print(f"    Path: {path}")
        print(f"    Types: {name}-RS, {name}-RTM")
        print()

    return 0


def cmd_namespace_add(user: str, name: str) -> int:
    """Add a new SDLC namespace."""
    # Permission check - only administrators can add namespaces
    user_group = get_user_group(user)
    if user_group != "administrator":
        print(f"""
Permission Denied: 'namespace add' command

Your role: {user_group} ({user})
Required role: administrator

Only administrators can add new SDLC namespaces.
""")
        return 1

    if not name:
        print("""
Error: Must specify namespace name.

Usage: qms --user lead namespace add NAME

Example:
  qms --user lead namespace add FLOW    # Creates SDLC-FLOW/ with FLOW-RS, FLOW-RTM types
  qms --user lead namespace add ACME    # Creates SDLC-ACME/ with ACME-RS, ACME-RTM types
""")
        return 1

    name = name.upper()
    namespaces = load_namespaces()

    if name in namespaces:
        print(f"Error: Namespace '{name}' already exists.")
        return 1

    # Create namespace directory
    namespace_path = QMS_ROOT / f"SDLC-{name}"
    if not namespace_path.exists():
        namespace_path.mkdir(parents=True)
        print(f"Created: {namespace_path.relative_to(PROJECT_ROOT)}")

    # Add to registry
    namespaces[name] = {"path": f"SDLC-{name}"}
    save_namespaces(namespaces)

    print(f"Registered namespace: {name}")
    print(f"  Document types: {name}-RS, {name}-RTM")
    print(f"  Path: SDLC-{name}/")

    return 0
