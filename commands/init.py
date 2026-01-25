"""
QMS Init Command

Initializes a new QMS project with all required infrastructure.

Created as part of CR-036: Add qms-cli initialization and bootstrapping functionality
"""
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from registry import CommandRegistry
from qms_config import CONFIG_FILE


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
        qms_root / ".audit",
        qms_root / ".archive",
        qms_root / "SOP",
        qms_root / "CR",
        qms_root / "INV",
        qms_root / "TEMPLATE",
    ]

    for directory in directories:
        directory.mkdir(parents=True, exist_ok=True)
        print(f"  Created: {directory}")


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


def create_default_agent(root: Path) -> None:
    """Create default qa agent definition file."""
    agents_dir = root / ".claude" / "agents"
    agents_dir.mkdir(parents=True, exist_ok=True)

    qa_agent_path = agents_dir / "qa.md"
    qa_content = """---
name: qa
group: quality
description: Quality Assurance Representative
---

# QA Agent

You are the Quality Assurance (QA) representative for this QMS project.

## Responsibilities

- Review all documents for procedural compliance
- Assign Technical Units (TUs) to review documents based on affected domains
- Serve as mandatory reviewer/approver for all controlled documents
- Verify that document workflows follow SOP-001 and SOP-002

## Review Criteria

When reviewing documents, verify:
1. Frontmatter is complete (title, revision_summary)
2. All required sections are present per the document type's SOP
3. Content is clear, accurate, and complete
4. Changes are traceable to authorizing documents (CRs, INVs)

## Commands

Check your inbox:
```
python qms-cli/qms.py --user qa inbox
```

Review a document:
```
python qms-cli/qms.py --user qa review DOC-ID --recommend --comment "..."
python qms-cli/qms.py --user qa review DOC-ID --request-updates --comment "..."
```

Approve a document:
```
python qms-cli/qms.py --user qa approve DOC-ID
```

Assign reviewers:
```
python qms-cli/qms.py --user qa assign DOC-ID --assignees tu_ui tu_scene
```
"""

    with open(qa_agent_path, "w", encoding="utf-8") as f:
        f.write(qa_content)

    print(f"  Created: {qa_agent_path}")


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
        create_default_agent(root)
    except Exception as e:
        print(f"\nERROR: Failed to create infrastructure: {e}")
        return 1

    print()
    print("QMS project initialized successfully!")
    print()
    print("Next steps:")
    print("  1. SOPs will be seeded automatically (or run 'qms seed' if needed)")
    print("  2. Create your first document: python qms-cli/qms.py --user claude create CR --title \"My Change\"")
    print("  3. Check status: python qms-cli/qms.py --user claude inbox")

    return 0
