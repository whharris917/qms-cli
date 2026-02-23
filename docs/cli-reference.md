# CLI Reference

## Command Format

```bash
python qms-cli/qms.py --user {USER} <command> [options]
```

The `--user` flag is required on every command except `init`. It identifies the agent performing the operation and determines which permissions apply. See [Users and Permissions](users-and-permissions.md) for details.

---

## Document Management

### `create` — Create a new document

Creates a draft document of the specified type.

```bash
qms --user claude create CR --title "Add particle collision detection"
qms --user claude create INV --title "Investigation: Solver convergence failure"
qms --user claude create SOP --title "Code Review Procedures"
```

**Options:**

| Flag | Description | Required |
|------|-------------|----------|
| `--title "..."` | Document title | Yes |
| `--parent {DOC_ID}` | Parent document ID (for child types: VAR, TP, ER, ADD, VR) | For child types |
| `--name {NAME}` | Template name (for TEMPLATE type) | For templates |

**Child document examples:**

```bash
qms --user claude create VAR --title "Variance: scope change" --parent CR-045
qms --user claude create VR --title "Verification: particle behavior" --parent CR-045
qms --user claude create TP --title "Test Protocol: UI regression" --parent CR-045
```

**Output:** Confirmation with the new document ID (e.g., `CR-092`, `CR-045-VAR-001`).

### `read` — Read document content

Retrieves and displays the content of a document.

```bash
qms --user claude read CR-045
qms --user claude read CR-045 --version 1.0
qms --user claude read CR-045 --draft
```

**Options:**

| Flag | Description |
|------|-------------|
| `--version {X.Y}` | Read a specific version (e.g., `1.0`, `2.1`) |
| `--draft` | Read the current draft instead of the effective version |

### `checkout` — Check out for editing

Locks the document and copies it to your workspace.

```bash
qms --user claude checkout CR-045
```

- Document is locked — no other user can check it out simultaneously
- Working copy appears in `.claude/users/{user}/workspace/`
- Edit the workspace copy, then check in when finished

### `checkin` — Check in after editing

Unlocks the document and applies workspace changes.

```bash
qms --user claude checkin CR-045
```

- Workspace changes are applied to the controlled copy
- Document is unlocked
- Draft version is incremented

### `status` — Check document status

Displays current state, version, owner, and workflow status.

```bash
qms --user claude status CR-045
```

---

## Workflow

### `route` — Route for review or approval

Submits a document to the next workflow stage.

```bash
qms --user claude route CR-045 --review
qms --user claude route CR-045 --approval
qms --user claude route SOP-003 --retire
```

**Options:**

| Flag | Description |
|------|-------------|
| `--review` | Route for review (DRAFT → IN_REVIEW, or IN_EXECUTION → IN_POST_REVIEW) |
| `--approval` | Route for approval (REVIEWED → IN_APPROVAL, or POST_REVIEWED → IN_POST_APPROVAL) |
| `--retire` | Route for retirement approval |

Routing for approval is blocked if any reviewer submitted `request-updates`. All reviewers must recommend before approval routing is permitted.

### `assign` — Assign reviewers

Adds users to a document's review team. **Quality group only.**

```bash
qms --user qa assign CR-045 --assignees tu_ui tu_scene
```

| Flag | Description |
|------|-------------|
| `--assignees {user1} {user2} ...` | List of user IDs to assign |

### `review` — Submit a review decision

Records a review outcome with a comment.

```bash
qms --user tu_ui review CR-045 --recommend --comment "Code changes look correct"
qms --user tu_ui review CR-045 --request-updates --comment "Missing error handling"
```

| Flag | Description |
|------|-------------|
| `--recommend` | Recommend for approval |
| `--request-updates` | Request changes before approval |
| `--comment "..."` | Review comments (required) |

### `approve` — Approve a document

Completes the approval workflow.

```bash
qms --user qa approve CR-045
```

- Non-executable documents (SOP, RS, RTM) transition to EFFECTIVE
- Executable documents (CR, INV, etc.) transition to PRE_APPROVED (pre) or POST_APPROVED (post)

### `reject` — Reject a document

Returns the document to a revisable state. Requires a comment.

```bash
qms --user qa reject CR-045 --comment "RTM references are incomplete"
```

| Flag | Description | Required |
|------|-------------|----------|
| `--comment "..."` | Rejection rationale | Yes |

After rejection, the document must go through a full review cycle again (not straight to re-approval).

### `withdraw` — Withdraw from workflow

Returns a document to its state before routing. Owner only.

```bash
qms --user claude withdraw CR-045
```

### `release` — Release for execution

Transitions an executable document from PRE_APPROVED to IN_EXECUTION. Owner only.

```bash
qms --user claude release CR-045
```

### `revert` — Revert to execution

Transitions from POST_REVIEWED back to IN_EXECUTION. Requires a reason. Owner only.

```bash
qms --user claude revert CR-045 --reason "Additional execution items needed"
```

| Flag | Description | Required |
|------|-------------|----------|
| `--reason "..."` | Explanation for the revert | Yes |

### `close` — Close an executable document

Transitions from POST_APPROVED to CLOSED (terminal state). Owner only.

```bash
qms --user claude close CR-045
```

### `cancel` — Cancel a never-effective document

Permanently deletes a document that has never been approved (version < 1.0). Requires confirmation.

```bash
qms --user claude cancel CR-099 --confirm
```

| Flag | Description | Required |
|------|-------------|----------|
| `--confirm` | Safety confirmation flag | Yes |

---

## Audit and History

### `history` — View audit trail

Shows all lifecycle events for a document in chronological order.

```bash
qms --user claude history CR-045
```

### `comments` — View review comments

Extracts comments from REVIEW and REJECT events.

```bash
qms --user claude comments CR-045
qms --user claude comments CR-045 --version 2.0
```

| Flag | Description |
|------|-------------|
| `--version {X.Y}` | Filter comments by version (optional) |

---

## User

### `inbox` — Check pending tasks

Shows documents awaiting your review, approval, or other action.

```bash
qms --user qa inbox
```

### `workspace` — View checked-out documents

Lists documents currently checked out to your workspace.

```bash
qms --user claude workspace
```

### `user --add` — Add a new user

Creates an agent definition and workspace/inbox for a new user. Administrator only.

```bash
qms --user lead user --add reviewer_name --group reviewer
```

| Flag | Description |
|------|-------------|
| `--add {USERNAME}` | Username to create |
| `--group {GROUP}` | Permission group: administrator, initiator, quality, reviewer |
| `--list` | List all known users |

---

## Interactive Authoring

### `interact` — Interactive document operations

For documents with interactive templates (currently VR documents). Manages the prompt-response lifecycle.

```bash
qms --user claude interact CR-045-VR-001 --respond        # Submit response to current prompt
qms --user claude interact CR-045-VR-001 --progress        # Show completion progress
qms --user claude interact CR-045-VR-001 --compile         # Preview compiled output
qms --user claude interact CR-045-VR-001 --goto step_3     # Navigate to a specific step
qms --user claude interact CR-045-VR-001 --cancel-goto     # Cancel pending navigation
qms --user claude interact CR-045-VR-001 --reopen loop_1   # Reopen a completed loop
```

| Flag | Description |
|------|-------------|
| `--respond [VALUE]` | Submit a response (reads from stdin if no value) |
| `--file {PATH}` | Read response from file instead of argument |
| `--reason "..."` | Reason for amendment or loop reopen |
| `--compile` | Preview compiled output |
| `--progress` | Show current progress |
| `--goto {STEP}` | Navigate to a step for amendment |
| `--cancel-goto` | Cancel a pending goto |
| `--reopen {LOOP}` | Reopen a completed loop |

---

## Administrative

### `fix` — Administrative fix

Applies a minor correction to an EFFECTIVE document without a full revision cycle. Administrator only.

```bash
qms --user lead fix SOP-001
```

Use for typos, formatting, or non-substantive changes. Substantive changes require a CR.

### `init` — Initialize a new project

Creates QMS infrastructure in a directory. Does not require `--user`.

```bash
python qms-cli/qms.py init
python qms-cli/qms.py init --root /path/to/project
```

Safety checks prevent initialization if any QMS infrastructure already exists.

### `namespace` — Manage SDLC namespaces

Registers namespaces for RS/RTM document pairs.

```bash
qms --user claude namespace list
qms --user claude namespace add FLOW
```

---

## Permission Matrix

| Command | Administrator | Initiator | Quality | Reviewer |
|---------|:---:|:---:|:---:|:---:|
| `create` | Y | Y | - | - |
| `read` | Y | Y | Y | Y |
| `checkout` / `checkin` | Y | Y | - | - |
| `route` | Y | Y | - | - |
| `assign` | - | - | Y | - |
| `review` | Y | Y | Y | Y |
| `approve` / `reject` | - | - | Y | Y |
| `withdraw` | Y | Y | - | - |
| `release` / `close` | Y | Y | - | - |
| `cancel` | Y | Y | - | - |
| `history` / `comments` | Y | Y | Y | Y |
| `inbox` / `workspace` | Y | Y | Y | Y |
| `interact` | Y | Y | - | - |
| `fix` | Y | - | - | - |
| `user --add` | Y | - | - | - |

Note: Administrators inherit all Initiator permissions. Some commands additionally require ownership (`owner_only`) or workflow assignment (`assigned_only`).

---

## MCP Equivalents

When the QMS MCP server is running, all commands are available as native MCP tools. See [MCP Server](mcp-server.md) for setup.

| CLI Command | MCP Tool |
|-------------|----------|
| `inbox` | `qms_inbox(user)` |
| `workspace` | `qms_workspace(user)` |
| `status {DOC_ID}` | `qms_status(doc_id, user)` |
| `read {DOC_ID}` | `qms_read(doc_id, user)` |
| `create {TYPE} --title "..."` | `qms_create(doc_type, title, user)` |
| `checkout {DOC_ID}` | `qms_checkout(doc_id, user)` |
| `checkin {DOC_ID}` | `qms_checkin(doc_id, user)` |
| `route {DOC_ID} --review` | `qms_route(doc_id, "review", user)` |
| `route {DOC_ID} --approval` | `qms_route(doc_id, "approval", user)` |
| `assign {DOC_ID} --assignees [...]` | `qms_assign(doc_id, assignees, user)` |
| `review {DOC_ID} --recommend` | `qms_review(doc_id, "recommend", user)` |
| `approve {DOC_ID}` | `qms_approve(doc_id, user)` |
| `reject {DOC_ID} --comment "..."` | `qms_reject(doc_id, comment, user)` |
| `release {DOC_ID}` | `qms_release(doc_id, user)` |
| `revert {DOC_ID} --reason "..."` | `qms_revert(doc_id, reason, user)` |
| `close {DOC_ID}` | `qms_close(doc_id, user)` |
| `cancel {DOC_ID} --confirm` | `qms_cancel(doc_id, user, confirm)` |
| `history {DOC_ID}` | `qms_history(doc_id, user)` |
| `comments {DOC_ID}` | `qms_comments(doc_id, user)` |
| `fix {DOC_ID}` | `qms_fix(doc_id, user)` |
