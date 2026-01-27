# QMS CLI - Quality Management System

A GMP-inspired document control system for software projects. See **SOP-001** for complete procedural documentation.

## Quick Start

### Initialize a New Project

```bash
# Clone qms-cli into your project
cd my-project
git clone https://github.com/whharris917/qms-cli.git

# Initialize QMS infrastructure
python qms-cli/qms.py init
```

This creates:
- `qms.config.json` - Project root marker
- `QMS/` - Document storage (SOPs, CRs, templates)
- `.claude/users/` - User workspaces and inboxes
- `.claude/agents/qa.md` - Default QA agent

### Project Structure

```
my-project/                     # Your project root
├── qms-cli/                    # QMS CLI tool (cloned repo)
├── qms.config.json             # Project marker (created by init)
├── QMS/                        # Controlled documents
│   ├── SOP/                    # Standard Operating Procedures
│   ├── CR/                     # Change Records
│   ├── INV/                    # Investigations
│   ├── TEMPLATE/               # Document templates
│   ├── .meta/                  # Workflow metadata (managed by CLI)
│   ├── .audit/                 # Audit trails (append-only)
│   └── .archive/               # Historical versions
├── .claude/
│   ├── users/                  # User workspaces and inboxes
│   └── agents/                 # Agent definition files
└── src/                        # Your application code
```

**Important:** Keep `qms-cli/` as a separate directory from your QMS documents. Do not run `init` inside the `qms-cli/` directory.

## Usage

Most commands require the `--user` (or `-u`) flag to identify yourself:

```bash
python qms-cli/qms.py --user <username> <command> [options]
```

Or with an alias:

```bash
alias qms='python qms-cli/qms.py'
qms --user claude <command> [options]
```

## User Management

### Built-in Administrators

The users `lead` and `claude` are hardcoded as administrators. They work without agent files.

### Adding Users

Other users are defined via agent files in `.claude/agents/`:

```bash
# Add a new user (requires administrator privileges)
qms --user lead user --add alice --group reviewer

# List all users
qms --user lead user --list
```

This creates `.claude/agents/alice.md` with the specified group and sets up workspace/inbox directories.

### User Groups & Permissions

| Group | Capabilities |
|-------|--------------|
| **administrator** | All capabilities (create, route, assign, review, approve, manage users) |
| **initiator** | Create, checkout, checkin, route, release, close |
| **quality** | Assign reviewers, review, approve, reject |
| **reviewer** | Review, approve, reject (when assigned) |

Note: The `fix` command is restricted to specific users (`qa` and `lead`) rather than being group-based.

## Commands

### Document Creation & Editing

```bash
# Create a new document (auto-generates ID, auto-checkouts)
qms --user claude create SOP --title "My Procedure"
qms --user claude create CR --title "Feature Implementation"

# Check out existing document for editing
qms --user claude checkout SOP-001

# Check in edited document (saves to QMS, clears checkout)
qms --user claude checkin SOP-001

# Read documents (any user can read)
qms --user claude read SOP-001                    # Effective version
qms --user claude read SOP-001 --draft            # Draft version
qms --user claude read SOP-001 --version 1.0      # Archived version
```

### Workflow Routing

**Non-executable documents (SOP, RS, RTM):**

```bash
qms --user claude route SOP-001 --review      # Route for review (QA auto-assigned)
qms --user claude route SOP-001 --approval    # Route for approval (after REVIEWED)
```

**Executable documents (CR, INV, TP, ER, VAR):**

```bash
qms --user claude route CR-001 --review      # Routes to pre-review (from DRAFT)
qms --user claude route CR-001 --approval    # Routes to pre-approval (from PRE_REVIEWED)
qms --user claude release CR-001             # Start execution
qms --user claude route CR-001 --review      # Routes to post-review (from IN_EXECUTION)
qms --user claude route CR-001 --approval    # Routes to post-approval (from POST_REVIEWED)
qms --user claude close CR-001               # Finalize
```

The CLI automatically infers pre/post phase from the document's current status.

### Review & Approval

```bash
# Submit review (must specify outcome)
qms --user qa review SOP-001 --recommend --comment "Approved. No issues."
qms --user alice review SOP-001 --request-updates --comment "Section 3 needs work."

# Approve or reject
qms --user qa approve SOP-001
qms --user qa reject SOP-001 --comment "Does not meet requirements."

# QA: Assign additional reviewers
qms --user qa assign SOP-001 --assignees alice bob
```

### Status & Tasks

```bash
qms --user claude status SOP-001    # Document status and workflow state
qms --user qa inbox                 # Your pending review/approval tasks
qms --user claude workspace         # Your checked-out documents
```

### Administrative

```bash
# Fix metadata on EFFECTIVE documents (QA/lead only)
qms --user qa fix SOP-001
```

## Document Types

| Type | Executable | Description |
|------|------------|-------------|
| SOP | No | Standard Operating Procedure |
| CR | Yes | Change Record |
| INV | Yes | Investigation |
| TP | Yes | Test Protocol (child of CR) |
| ER | Yes | Exception Report (child of TP) |
| VAR | Yes | Variance Report (child of CR or INV) |
| RS, RTM | No | SDLC documents (per registered namespace) |
| TEMPLATE | No | Document templates |

## Workflows

### Non-Executable (SOP, SDLC docs)

```
DRAFT → IN_REVIEW → REVIEWED → IN_APPROVAL → APPROVED → EFFECTIVE
                ↑______________|  (rejection)
```

### Executable (CR, INV, etc.)

```
DRAFT → IN_PRE_REVIEW → PRE_REVIEWED → IN_PRE_APPROVAL → PRE_APPROVED
                    ↑_______________|  (rejection)
                                                              ↓
                                                        IN_EXECUTION
                                                              ↓
        IN_POST_REVIEW → POST_REVIEWED → IN_POST_APPROVAL → POST_APPROVED → CLOSED
                     ↑_______________|  (rejection)
                            ↑_______|  (revert)
```

## Review Outcomes

Reviews require an explicit outcome:

| Flag | Meaning |
|------|---------|
| `--recommend` | Document ready for approval |
| `--request-updates` | Changes required before approval |

**Approval Gate:** Documents cannot be routed for approval unless all reviewers submitted `--recommend`.

## Directory Structure

```
my-project/
├── qms-cli/                    # QMS CLI tool
├── qms.config.json             # Project root marker
├── QMS/
│   ├── SOP/                    # Effective SOPs
│   ├── CR/                     # Change Records (folder per CR)
│   │   └── CR-001/
│   ├── INV/                    # Investigations
│   ├── TEMPLATE/               # Document templates
│   ├── .meta/                  # Workflow state (JSON, managed by CLI)
│   ├── .audit/                 # Audit trails (JSONL, append-only)
│   └── .archive/               # Historical versions
│       └── SOP/
│           └── SOP-001-v1.0.md
└── .claude/
    ├── users/
    │   ├── claude/
    │   │   ├── workspace/      # Checked-out documents
    │   │   └── inbox/          # Pending tasks
    │   └── qa/
    └── agents/                 # User definitions
        ├── qa.md               # group: quality
        └── alice.md            # group: reviewer
```

## Version Numbering

| Version | Meaning |
|---------|---------|
| v0.1 | Initial draft |
| v0.2+ | Revisions during review |
| v1.0 | First approval |
| v1.1+ | Revisions after reopening v1.0 |
| v2.0 | Second approval |

## Common Workflows

### Create and approve a new SOP

```bash
# Initiator creates and routes document
qms --user claude create SOP --title "New Procedure"
# Edit the document in workspace...
qms --user claude checkin SOP-003
qms --user claude route SOP-003 --review

# QA reviews
qms --user qa review SOP-003 --recommend --comment "Looks good."
qms --user qa inbox  # empty now

# Initiator routes for approval
qms --user claude route SOP-003 --approval

# QA approves
qms --user qa approve SOP-003
# Document is now EFFECTIVE
```

### Create and execute a Change Record

```bash
# Initiator creates CR
qms --user claude create CR --title "Add feature X"
qms --user claude checkin CR-001
qms --user claude route CR-001 --review       # -> IN_PRE_REVIEW (from DRAFT)

# QA assigns technical reviewer and reviews
qms --user qa assign CR-001 --assignees alice
qms --user qa review CR-001 --recommend --comment "Approach is sound."

# Technical reviewer reviews
qms --user alice review CR-001 --recommend --comment "Technical changes approved."

# Route for pre-approval
qms --user claude route CR-001 --approval     # -> IN_PRE_APPROVAL (from PRE_REVIEWED)

# Approvals
qms --user qa approve CR-001
qms --user alice approve CR-001

# Execute the change
qms --user claude release CR-001
# ... implement the change ...
qms --user claude route CR-001 --review       # -> IN_POST_REVIEW (from IN_EXECUTION)

# ... post-review and post-approval ...
qms --user claude route CR-001 --approval     # -> IN_POST_APPROVAL (from POST_REVIEWED)
qms --user claude close CR-001
```

## Error Messages

The CLI provides detailed error messages with guidance when permissions are denied or workflow rules are violated. Example:

```
Permission Denied: 'approve' command

Your role: initiators (claude)
Required role(s): qa, reviewers

As an Initiator (lead, claude), you can:
  - Create new documents: qms create SOP --title "Title"
  ...

You cannot:
  - Approve or reject documents
```

## References

- **SOP-001**: Quality Management System - Document Control (complete procedural documentation)
- **SOP-002**: Change Control (CR workflow details)
