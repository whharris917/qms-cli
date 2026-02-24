# 12. CLI Reference

All QMS operations are performed through the CLI tool. Direct manipulation of QMS files (metadata, audit trails, controlled documents) is prohibited. See [Document Control](02-Document-Control.md) for the metadata architecture and [Agent Orchestration](11-Agent-Orchestration.md) for who can run which commands.

## Command Format

```bash
python qms-cli/qms.py --user {USER} <command> [options]
```

The `--user` flag is required on every command. It identifies the agent performing the operation and determines which permissions apply.

## MCP Tool Equivalents

When the QMS MCP server is running, many commands are also available as native MCP tools. MCP tools return structured responses and are preferred when available.

| CLI Command | MCP Tool | Notes |
|-------------|----------|-------|
| `inbox` | `qms_inbox(user)` | |
| `workspace` | `qms_workspace(user)` | |
| `status {DOC_ID}` | `qms_status(doc_id, user)` | |
| `read {DOC_ID}` | `qms_read(doc_id, user)` | Supports `--version` and `--draft` |
| `create {TYPE} --title "..."` | `qms_create(doc_type, title, user)` | |
| `checkout {DOC_ID}` | `qms_checkout(doc_id, user)` | |
| `checkin {DOC_ID}` | `qms_checkin(doc_id, user)` | |
| `route {DOC_ID} --review` | `qms_route(doc_id, "review", user)` | |
| `route {DOC_ID} --approval` | `qms_route(doc_id, "approval", user)` | |
| `assign {DOC_ID} --assignees [...]` | `qms_assign(doc_id, assignees, user)` | Quality group only |
| `review {DOC_ID} --recommend` | `qms_review(doc_id, "recommend", user)` | |
| `review {DOC_ID} --request-updates` | `qms_review(doc_id, "request-updates", user)` | |
| `approve {DOC_ID}` | `qms_approve(doc_id, user)` | |
| `reject {DOC_ID} --comment "..."` | `qms_reject(doc_id, comment, user)` | |
| `release {DOC_ID}` | `qms_release(doc_id, user)` | |
| `revert {DOC_ID} --reason "..."` | `qms_revert(doc_id, reason, user)` | |
| `close {DOC_ID}` | `qms_close(doc_id, user)` | |
| `cancel {DOC_ID} --confirm` | `qms_cancel(doc_id, user, confirm)` | |
| `history {DOC_ID}` | `qms_history(doc_id, user)` | |
| `comments {DOC_ID}` | `qms_comments(doc_id, user)` | |
| `fix {DOC_ID}` | `qms_fix(doc_id, user)` | Administrator only |

---

## Document Management

### `create` -- Create a new document

Creates a draft document of the specified type.

```bash
python qms-cli/qms.py --user claude create CR --title "Add particle collision detection"
python qms-cli/qms.py --user claude create SOP --title "Code Review Procedures"
python qms-cli/qms.py --user claude create INV --title "Investigation: Solver convergence failure"
```

**Options:**

| Flag | Description | Required |
|------|-------------|----------|
| `--title "..."` | Document title | Yes |
| `--parent {DOC_ID}` | Parent document ID (for child types: VAR, TP, ER, ADD, VR) | For child types |
| `--name {NAME}` | Template name (for TEMPLATE type) | For templates |

**Child document examples:**

```bash
python qms-cli/qms.py --user claude create VAR --title "Variance: scope change" --parent CR-045
python qms-cli/qms.py --user claude create TP --title "Test Protocol: UI regression" --parent CR-045
python qms-cli/qms.py --user claude create VR --title "Verification: particle behavior" --parent CR-045
```

**Output:** Confirmation with the new document ID (e.g., `CR-092`, `CR-045-VAR-001`).

### `read` -- Read document content

Retrieves and displays the content of a document.

```bash
python qms-cli/qms.py --user claude read CR-045
python qms-cli/qms.py --user claude read CR-045 --version 1.0
python qms-cli/qms.py --user claude read CR-045 --draft
```

**Options:**

| Flag | Description |
|------|-------------|
| `--version {X.Y}` | Read a specific version (e.g., `1.0`, `2.1`) |
| `--draft` | Read the current draft version instead of the effective version |

### `checkout` -- Check out a document for editing

Locks the document and copies it to your workspace for editing.

```bash
python qms-cli/qms.py --user claude checkout CR-045
```

**Behavior:**
- Document is locked -- no other user can check it out simultaneously
- A working copy appears in `.claude/users/claude/workspace/`
- Edit the workspace copy, then check in when finished

### `checkin` -- Check in a document after editing

Unlocks the document and applies your workspace changes.

```bash
python qms-cli/qms.py --user claude checkin CR-045
```

**Behavior:**
- Workspace changes are applied to the controlled copy
- Document is unlocked
- Draft version is incremented

### `status` -- Check document status

Displays the current state, version, owner, and workflow status of a document.

```bash
python qms-cli/qms.py --user claude status CR-045
```

**Output includes:** Document state, current version, responsible user, lock status, review team assignments.

---

## Workflow

### `route` -- Route for review or approval

Submits a document to the next workflow stage.

```bash
python qms-cli/qms.py --user claude route CR-045 --review
python qms-cli/qms.py --user claude route CR-045 --approval
python qms-cli/qms.py --user claude route SOP-003 --retire
```

**Options:**

| Flag | Description |
|------|-------------|
| `--review` | Route for review (DRAFT -> IN_REVIEW) |
| `--approval` | Route for approval (IN_REVIEW -> IN_APPROVAL) |
| `--retire` | Route for retirement approval |

**Note:** Routing for approval is blocked if any reviewer submitted `request-updates`. All reviewers must recommend before approval routing is permitted.

### `assign` -- Assign reviewers or approvers

Adds users to a document's review/approval team. **Quality group only.**

```bash
python qms-cli/qms.py --user qa assign CR-045 --assignees tu_ui tu_scene
```

**Options:**

| Flag | Description |
|------|-------------|
| `--assignees {user1} {user2} ...` | List of user IDs to assign |

### `review` -- Submit a review decision

Records a review outcome with an optional comment.

```bash
python qms-cli/qms.py --user tu_ui review CR-045 --recommend --comment "Code changes look correct"
python qms-cli/qms.py --user tu_ui review CR-045 --request-updates --comment "Missing error handling in solver path"
```

**Options:**

| Flag | Description |
|------|-------------|
| `--recommend` | Recommend for approval |
| `--request-updates` | Request changes before approval |
| `--comment "..."` | Review comments (optional but encouraged) |

### `approve` -- Approve a document

Completes the approval workflow and increments the document version.

```bash
python qms-cli/qms.py --user qa approve CR-045
```

**Behavior:** Depends on document type (see [Workflows](03-Workflows.md)):
- Non-executable documents (RS, RTM, SOP) transition to EFFECTIVE
- Executable documents (CR, INV, TP, etc.) transition to PRE_APPROVED

### `reject` -- Reject a document

Returns the document to a revisable state with a mandatory comment explaining why.

```bash
python qms-cli/qms.py --user qa reject CR-045 --comment "RTM references are incomplete"
```

**Options:**

| Flag | Description | Required |
|------|-------------|----------|
| `--comment "..."` | Rejection rationale | Yes |

### `withdraw` -- Withdraw from workflow

Returns a document to its previous state before routing. Only the document owner can withdraw.

```bash
python qms-cli/qms.py --user claude withdraw CR-045
```

### `release` -- Release for execution

Transitions an executable document from PRE_APPROVED to IN_EXECUTION. Owner only.

```bash
python qms-cli/qms.py --user claude release CR-045
```

### `revert` -- Revert to execution

Transitions an executable document from POST_REVIEWED back to IN_EXECUTION. Requires a reason.

```bash
python qms-cli/qms.py --user claude revert CR-045 --reason "Additional execution items needed"
```

**Options:**

| Flag | Description | Required |
|------|-------------|----------|
| `--reason "..."` | Explanation for the revert | Yes |

### `close` -- Close an executable document

Transitions from POST_APPROVED to CLOSED (terminal state). Owner only.

```bash
python qms-cli/qms.py --user claude close CR-045
```

### `cancel` -- Cancel a never-effective document

Permanently deletes a document that has never been approved (version < 1.0). Requires confirmation.

```bash
python qms-cli/qms.py --user claude cancel CR-099 --confirm
```

**Options:**

| Flag | Description | Required |
|------|-------------|----------|
| `--confirm` | Safety confirmation flag | Yes |

**Restriction:** Only documents that have never reached EFFECTIVE or PRE_APPROVED can be cancelled.

---

## Audit and History

### `history` -- View audit trail

Shows all recorded lifecycle events for a document in chronological order.

```bash
python qms-cli/qms.py --user claude history CR-045
```

**Output:** Timestamped list of events (created, checked out, routed, reviewed, approved, etc.).

### `comments` -- View review comments

Extracts comments from REVIEW and REJECT events in the audit trail.

```bash
python qms-cli/qms.py --user claude comments CR-045
python qms-cli/qms.py --user claude comments CR-045 --version 2.0
```

**Options:**

| Flag | Description |
|------|-------------|
| `--version {X.Y}` | Filter comments by version (optional) |

---

## User

### `inbox` -- Check pending tasks

Shows documents awaiting your review, approval, or other action.

```bash
python qms-cli/qms.py --user qa inbox
```

**Output:** List of documents assigned to you with their current workflow state.

### `workspace` -- View checked-out documents

Lists all documents currently checked out to your workspace.

```bash
python qms-cli/qms.py --user claude workspace
```

---

## Interactive

### `interact` -- Interactive document operations

Used for interactive executable documents (documents with interactive templates). These commands manage the response lifecycle within an interactive execution.

```bash
python qms-cli/qms.py --user claude interact CR-045 --respond
python qms-cli/qms.py --user claude interact CR-045 --compile
python qms-cli/qms.py --user claude interact CR-045 --progress
python qms-cli/qms.py --user claude interact CR-045 --goto {STEP}
python qms-cli/qms.py --user claude interact CR-045 --cancel-goto
python qms-cli/qms.py --user claude interact CR-045 --reopen
```

**Options:**

| Flag | Description |
|------|-------------|
| `--respond` | Submit a response to the current interactive step |
| `--compile` | Compile responses into the document |
| `--progress` | Show current progress through the interactive template |
| `--goto {STEP}` | Navigate to a specific step |
| `--cancel-goto` | Cancel a pending goto operation |
| `--reopen` | Reopen a completed interactive step for revision |

See [08-Interactive-Authoring.md](08-Interactive-Authoring.md) for the full interactive authoring model.

---

## Administrative

### `fix` -- Administrative fix

Applies a minor correction to an EFFECTIVE document without a full revision cycle. **Administrator only.**

```bash
python qms-cli/qms.py --user lead fix SOP-001
```

**When to use:** Typo corrections, formatting fixes, or other non-substantive changes that do not alter the meaning or requirements of the document.

**Restriction:** Only works on EFFECTIVE documents. Substantive changes require a full CR.

---

## Permission Matrix

Quick reference for which groups can run which commands:

| Command | Administrator | Initiator | Quality | Reviewer |
|---------|:---:|:---:|:---:|:---:|
| `create` | Y | Y | - | - |
| `read` | Y | Y | Y | Y |
| `checkout` / `checkin` | Y | Y | - | - |
| `route` | Y | Y | - | - |
| `assign` | - | - | Y | - |
| `review` | - | - | Y | Y |
| `approve` / `reject` | - | - | Y | Y |
| `withdraw` | Y | Y | - | - |
| `release` / `close` | Y | Y | - | - |
| `cancel` | Y | Y | - | - |
| `history` / `comments` | Y | Y | Y | Y |
| `inbox` / `workspace` | Y | Y | Y | Y |
| `status` | Y | Y | Y | Y |
| `interact` | Y | Y | - | - |
| `fix` | Y | - | - | - |

## Related Documents

- [02-Document-Control.md](02-Document-Control.md) -- Document types, naming, versioning, metadata architecture
- [03-Workflows.md](03-Workflows.md) -- Document lifecycle state machines and transitions
- [04-Change-Control.md](04-Change-Control.md) -- CR-specific content and workflow
- [06-Execution.md](06-Execution.md) -- Execution items and evidence capture
- [08-Interactive-Authoring.md](08-Interactive-Authoring.md) -- Interactive template system
- [11-Agent-Orchestration.md](11-Agent-Orchestration.md) -- Agent identities and permissions
- [QMS-Glossary.md](QMS-Glossary.md) -- Term definitions
