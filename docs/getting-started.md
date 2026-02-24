# Getting Started

## Installation

qms-cli has no package installer. Clone or add as a submodule:

```bash
# As a submodule (recommended)
git submodule add https://github.com/whharris917/qms-cli.git qms-cli

# Or clone directly
git clone https://github.com/whharris917/qms-cli.git
```

## Initialize a Project

Run `init` from your project root:

```bash
python qms-cli/qms.py init
```

This creates:

| Artifact | Purpose |
|----------|---------|
| `qms.config.json` | Project root marker |
| `QMS/` | Controlled document storage (with `.meta/`, `.audit/`, `.archive/` subdirectories) |
| `QMS/TEMPLATE/` | Document templates (CR, VAR, VR, etc.) |
| `.claude/users/` | Workspaces and inboxes for default users (lead, claude, qa, tu) |
| `.claude/agents/` | Agent definitions (qa.md, tu.md) |
| `.claude/hooks/` | Write guard hook |
| `CLAUDE.md` | Starter orchestrator instructions |

Use `--root` to initialize a different directory:

```bash
python qms-cli/qms.py init --root /path/to/project
```

## Your First Document

### 1. Create a Change Record

```bash
python qms-cli/qms.py --user claude create CR --title "Add user authentication"
```

Output: `Created CR-001 (DRAFT v0.1)`

### 2. Check Out and Edit

```bash
python qms-cli/qms.py --user claude checkout CR-001
```

This copies CR-001 to `.claude/users/claude/workspace/CR-001.md`. Edit that file — fill in the scope, rationale, and execution items.

### 3. Check In

```bash
python qms-cli/qms.py --user claude checkin CR-001
```

Your edits are applied to the controlled copy. The document is unlocked.

### 4. Route for Review

```bash
python qms-cli/qms.py --user claude route CR-001 --review
```

The document moves to `IN_PRE_REVIEW`. QA assigns reviewers, reviewers submit their recommendations.

### 5. Route for Approval

After all reviewers recommend:

```bash
python qms-cli/qms.py --user claude route CR-001 --approval
```

QA (or assigned reviewers) approve or reject.

### 6. Release and Execute

Once approved (`PRE_APPROVED`):

```bash
python qms-cli/qms.py --user claude release CR-001
```

The document moves to `IN_EXECUTION`. Do the work described in the execution items. Check out the document again to record your evidence.

### 7. Post-Review and Close

After execution, route for post-review, get post-approval, then close:

```bash
python qms-cli/qms.py --user claude route CR-001 --review      # post-review
# ... reviewers review execution evidence ...
python qms-cli/qms.py --user claude route CR-001 --approval    # post-approval
# ... QA approves ...
python qms-cli/qms.py --user claude close CR-001
```

## Checking Your Status

```bash
python qms-cli/qms.py --user claude inbox       # Pending tasks assigned to you
python qms-cli/qms.py --user claude workspace    # Documents you have checked out
python qms-cli/qms.py --user claude status CR-001  # Status of a specific document
```

## Next Steps

- [CLI Reference](cli-reference.md) — Full command documentation
- [Users and Permissions](users-and-permissions.md) — Adding users, understanding groups
- Quality Manual (`Quality-Manual/START_HERE.md`) — Understanding when and why to use each document type
