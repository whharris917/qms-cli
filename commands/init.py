"""
QMS Init Command

Initializes a new QMS project with all required infrastructure.

Created as part of CR-036: Add qms-cli initialization and bootstrapping functionality
"""
import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from registry import CommandRegistry
from qms_config import CONFIG_FILE


# =============================================================================
# Seed Directory Location
# =============================================================================

def get_seed_dir() -> Path:
    """Get the seed directory path (relative to qms-cli installation)."""
    # seed/ is in the same directory as this file's parent (qms-cli/)
    return Path(__file__).parent.parent / "seed"


# =============================================================================
# Safety Checks
# =============================================================================

def check_clean_runway(root: Path) -> list[str]:
    """
    Check that the target directory is clean for initialization.

    All checks must pass before any changes are made.

    Args:
        root: Target project root directory

    Returns:
        List of blocking items (empty if all checks pass)
    """
    blockers = []

    # Check for existing QMS infrastructure
    if (root / "QMS").exists():
        blockers.append(f"QMS/ directory already exists at {root / 'QMS'}")

    if (root / ".claude" / "users").exists():
        blockers.append(f".claude/users/ directory already exists at {root / '.claude' / 'users'}")

    if (root / ".claude" / "agents" / "qa.md").exists():
        blockers.append(f".claude/agents/qa.md already exists at {root / '.claude' / 'agents' / 'qa.md'}")

    if (root / CONFIG_FILE).exists():
        blockers.append(f"{CONFIG_FILE} already exists at {root / CONFIG_FILE}")

    return blockers


# =============================================================================
# Directory Creation
# =============================================================================

def create_config_file(root: Path) -> None:
    """Create qms.config.json at project root."""
    config = {
        "version": "1.0",
        "created": datetime.now(timezone.utc).isoformat(),
        "sdlc_namespaces": []
    }

    config_path = root / CONFIG_FILE
    with open(config_path, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2)

    print(f"  Created: {config_path}")


def create_qms_structure(root: Path) -> None:
    """Create QMS/ directory structure."""
    qms_root = root / "QMS"

    # Create main directories
    directories = [
        qms_root / ".meta",
        qms_root / ".meta" / "SOP",
        qms_root / ".meta" / "TEMPLATE",
        qms_root / ".audit",
        qms_root / ".audit" / "SOP",
        qms_root / ".audit" / "TEMPLATE",
        qms_root / ".archive",
        qms_root / "SOP",
        qms_root / "CR",
        qms_root / "INV",
        qms_root / "TEMPLATE",
    ]

    for directory in directories:
        directory.mkdir(parents=True, exist_ok=True)

    print(f"  Created: {qms_root} (with subdirectories)")


def create_user_workspaces(root: Path) -> None:
    """Create user workspace and inbox directories."""
    users_root = root / ".claude" / "users"

    # Default users: lead, claude, qa
    default_users = ["lead", "claude", "qa"]

    for user in default_users:
        workspace = users_root / user / "workspace"
        inbox = users_root / user / "inbox"

        workspace.mkdir(parents=True, exist_ok=True)
        inbox.mkdir(parents=True, exist_ok=True)

        print(f"  Created: {workspace}")
        print(f"  Created: {inbox}")


# =============================================================================
# Seeding Functions
# =============================================================================

def create_meta_file(meta_dir: Path, doc_id: str, doc_type: str, executable: bool = False) -> None:
    """Create a .meta JSON file for a seeded document."""
    meta = {
        "doc_id": doc_id,
        "doc_type": doc_type,
        "version": "1.0",
        "status": "EFFECTIVE",
        "executable": executable,
        "responsible_user": None,
        "checked_out": False,
        "checked_out_date": None,
        "effective_version": "1.0",
        "supersedes": None,
        "pending_assignees": [],
        "pending_reviewers": [],
        "completed_reviewers": [],
        "review_outcomes": {},
        "approval_date": datetime.now(timezone.utc).strftime("%Y-%m-%d")
    }

    meta_path = meta_dir / f"{doc_id}.json"
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(meta, f, indent=2)


def create_audit_file(audit_dir: Path, doc_id: str) -> None:
    """Create an initial audit trail for a seeded document."""
    audit_path = audit_dir / f"{doc_id}.jsonl"

    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "action": "seed",
        "user": "system",
        "details": {
            "message": "Document seeded during QMS initialization",
            "version": "1.0",
            "status": "EFFECTIVE"
        }
    }

    with open(audit_path, "w", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")


def seed_sops(root: Path) -> int:
    """Copy seed SOPs to QMS/SOP/ with metadata."""
    seed_dir = get_seed_dir()
    sops_src = seed_dir / "sops"
    sops_dst = root / "QMS" / "SOP"
    meta_dir = root / "QMS" / ".meta" / "SOP"
    audit_dir = root / "QMS" / ".audit" / "SOP"

    if not sops_src.exists():
        print(f"  Warning: Seed SOPs not found at {sops_src}")
        return 0

    count = 0
    for sop_file in sorted(sops_src.glob("SOP-*.md")):
        # Copy document
        dst_path = sops_dst / sop_file.name
        shutil.copy2(sop_file, dst_path)

        # Extract doc_id from filename (e.g., SOP-001.md -> SOP-001)
        doc_id = sop_file.stem

        # Create metadata
        create_meta_file(meta_dir, doc_id, "SOP", executable=False)
        create_audit_file(audit_dir, doc_id)

        count += 1

    print(f"  Seeded: {count} SOPs")
    return count


def seed_templates(root: Path) -> int:
    """Copy seed templates to QMS/TEMPLATE/ with metadata."""
    seed_dir = get_seed_dir()
    templates_src = seed_dir / "templates"
    templates_dst = root / "QMS" / "TEMPLATE"
    meta_dir = root / "QMS" / ".meta" / "TEMPLATE"
    audit_dir = root / "QMS" / ".audit" / "TEMPLATE"

    if not templates_src.exists():
        print(f"  Warning: Seed templates not found at {templates_src}")
        return 0

    count = 0
    for template_file in sorted(templates_src.glob("TEMPLATE-*.md")):
        # Copy document
        dst_path = templates_dst / template_file.name
        shutil.copy2(template_file, dst_path)

        # Extract doc_id from filename (e.g., TEMPLATE-CR.md -> TEMPLATE-CR)
        doc_id = template_file.stem

        # Create metadata
        create_meta_file(meta_dir, doc_id, "TEMPLATE", executable=False)
        create_audit_file(audit_dir, doc_id)

        count += 1

    print(f"  Seeded: {count} templates")
    return count


def seed_agents(root: Path) -> int:
    """Copy seed agent definitions to .claude/agents/."""
    seed_dir = get_seed_dir()
    agents_src = seed_dir / "agents"
    agents_dst = root / ".claude" / "agents"

    if not agents_src.exists():
        print(f"  Warning: Seed agents not found at {agents_src}")
        return 0

    agents_dst.mkdir(parents=True, exist_ok=True)

    count = 0
    for agent_file in sorted(agents_src.glob("*.md")):
        dst_path = agents_dst / agent_file.name
        shutil.copy2(agent_file, dst_path)
        count += 1

    print(f"  Seeded: {count} agent definition(s)")
    return count


# =============================================================================
# Init Command
# =============================================================================

@CommandRegistry.register(
    name="init",
    help="Initialize a new QMS project",
    arguments=[
        {"flags": ["--root"], "help": "Project root directory (default: current directory)"},
    ],
)
def cmd_init(args) -> int:
    """
    Initialize a new QMS project with all required infrastructure.

    This command creates:
    - qms.config.json (project root marker)
    - QMS/ directory structure
    - User workspaces and inboxes
    - Default agent definitions

    Safety: All checks must pass before any changes are made.
    """
    # Determine target root
    if hasattr(args, 'root') and args.root:
        root = Path(args.root).resolve()
    else:
        root = Path.cwd().resolve()

    print(f"Initializing QMS project at: {root}")
    print()

    # Safety checks
    print("Running safety checks...")
    blockers = check_clean_runway(root)

    if blockers:
        print()
        print("ERROR: Cannot initialize - existing infrastructure detected:")
        for blocker in blockers:
            print(f"  - {blocker}")
        print()
        print("To initialize a new project, choose a clean directory or remove existing files.")
        return 1

    print("  All checks passed")
    print()

    # Create infrastructure
    print("Creating QMS infrastructure...")

    try:
        create_config_file(root)
        create_qms_structure(root)
        create_user_workspaces(root)
    except Exception as e:
        print(f"\nERROR: Failed to create infrastructure: {e}")
        return 1

    # Seed documents
    print()
    print("Seeding documents...")

    try:
        seed_sops(root)
        seed_templates(root)
        seed_agents(root)
    except Exception as e:
        print(f"\nERROR: Failed to seed documents: {e}")
        return 1

    print()
    print("QMS project initialized successfully!")
    print()
    print("Next steps:")
    print("  1. Review seeded SOPs in QMS/SOP/")
    print("  2. Create your first document: python qms-cli/qms.py --user claude create CR --title \"My Change\"")
    print("  3. Check your inbox: python qms-cli/qms.py --user claude inbox")

    return 0
