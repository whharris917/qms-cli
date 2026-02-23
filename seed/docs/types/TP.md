# TP -- Test Protocol

## Document Type Summary

| Property | Value |
|----------|-------|
| **Type code** | `TP` |
| **Executable** | Yes |
| **Parent required** | Yes -- must be a [`CR`](CR.md) |
| **Children** | [`TC`](TC.md) (fragment, embedded), [`ER`](ER.md) (standalone executable) |
| **Folder-per-doc** | No -- lives inside parent CR folder |
| **Template** | `QMS/TEMPLATE/TEMPLATE-TP.md` |

---

## 1. Naming Convention

| Pattern | Example |
|---------|---------|
| `{CR_ID}-TP-{NNN}` | `CR-001-TP-001` |

The sequential number `NNN` is zero-padded to 3 digits. Numbering is scoped to the parent CR: the CLI scans the parent CR folder for existing `{parent_id}-TP-NNN` files and increments from the highest found.

**File paths:**

| Variant | Path |
|---------|------|
| Draft | `QMS/CR/{CR_ID}/{CR_ID}-TP-{NNN}-draft.md` |
| Effective | `QMS/CR/{CR_ID}/{CR_ID}-TP-{NNN}.md` |
| Archive | `QMS/.archive/CR/{CR_ID}/{CR_ID}-TP-{NNN}-v{version}.md` |

---

## 2. Template Structure

### Frontmatter

```yaml
---
title: '{{TITLE}}'
revision_summary: 'Initial draft'
---
```

Only two author-maintained fields. All other metadata (version, status, responsible_user, dates) is managed in sidecar `.meta/TP/{doc_id}.json` files by the CLI.

### Sections

| # | Heading | Content | Static/Editable |
|---|---------|---------|-----------------|
| 1 | **Purpose** | What the test protocol verifies; the system/feature under test. | **Locked** after pre-approval |
| 2 | **Scope** | Table: System, Version, Commit hash identifying the build under test. | **Locked** after pre-approval |
| 3 | **Test Cases** | Container for TC subsections (TC-001, TC-002, ...). Each TC follows `TEMPLATE-TC` structure. | **Editable** during execution |
| 4 | **Protocol Summary** | 4.1 Overall Result (Pass/Fail/Pass with Exceptions) and 4.2 Execution Summary (narrative). | **Editable** during execution |
| 5 | **References** | Links to SOP-004, SOP-006, TC-TEMPLATE, and any additional references. | Locked after pre-approval |

### Placeholder Convention

| Syntax | Phase | Meaning |
|--------|-------|---------|
| `{{DOUBLE_CURLY}}` | Authoring (design time) | Replace before routing for review. None should remain after authoring. |
| `[SQUARE_BRACKETS]` | Execution (run time) | Replace during protocol execution. All should remain until execution begins. |

### ID Hierarchy (within a TP)

```
TP-NNN                              # Protocol
  TC-NNN                            # Test Case (embedded fragment)
    TC-NNN-NNN                      # Step within TC
    TC-NNN-ER-NNN                   # Exception Report for TC
      TC-NNN-ER-NNN-ER-NNN          # Nested ER
```

Full qualified IDs prefix with the TP ID:

```
CR-001-TP-001
  CR-001-TP-001-TC-001
    CR-001-TP-001-TC-001-001        # Step
    CR-001-TP-001-TC-001-ER-001     # Exception Report
```

---

## 3. Scope Table (Section 2)

The Scope section pins the test to a specific software version:

```markdown
| System | Version | Commit |
|--------|---------|--------|
| My App | 1.0.0 | a1b2c3d |
```

This is filled during authoring and locked after pre-approval. It establishes the qualified baseline for the test.

---

## 4. CLI Creation

### Command

```bash
qms --user claude create TP --parent CR-001 --title "Verification of Feature X"
```

### Required flags

| Flag | Required | Description |
|------|----------|-------------|
| `--parent` | **Yes** | Parent CR document ID. CLI validates: (1) parent exists (draft or effective), (2) parent type is `CR`. |
| `--title` | No | Document title. Defaults to `"TP - [Title]"` if omitted. |

### What `create.py` enforces

1. **Parent type validation:** `doc_type == "TP" and parent_type != "CR"` triggers error `"TP documents must have a CR parent"`.
2. **Parent existence:** Checks both `get_doc_path(parent_id)` (effective) and `get_doc_path(parent_id, draft=True)` (draft).
3. **No parent status restriction:** Unlike ADD (requires CLOSED parent) or VR (requires IN_EXECUTION parent), TP has no restriction on the parent CR's status.
4. **ID generation:** Calls `get_next_nested_number(parent_id, "TP")` to find the next sequential TP number under the parent CR folder.
5. **Template loading:** Calls `load_template_for_type("TP", doc_id, title)` which reads `QMS/TEMPLATE/TEMPLATE-TP.md`, extracts the example frontmatter and body, strips the TEMPLATE DOCUMENT NOTICE comment, and substitutes `{{TITLE}}`.
6. **Initial meta:** Creates `.meta/TP/{doc_id}.json` with `version: "0.1"`, `status: "DRAFT"`, `executable: True`.
7. **Workspace copy:** Copies draft to user workspace for immediate editing. Document is checked out on creation.

---

## 5. CLI Enforcement by Operation

### Checkout (`checkout.py`)

- Standard executable document checkout rules apply.
- **Terminal state guard:** CLOSED/RETIRED documents cannot be checked out.
- **Auto-withdraw:** If the TP is in an active workflow state (IN_PRE_REVIEW, IN_PRE_APPROVAL, etc.) and the owner checks it out, an implicit withdraw is performed first.
- **PRE_APPROVED checkout:** Transitions to DRAFT (scope revision -- clears workflow tracking).
- **POST_REVIEWED checkout:** Transitions to IN_EXECUTION (continued execution).
- **IN_EXECUTION checkout:** Increments minor version (e.g., 1.0 -> 1.1).

### Checkin (`checkin.py`)

- Verifies document is in user's workspace.
- **Ownership check:** Only the responsible_user can check in.
- **IN_EXECUTION archival:** If status is IN_EXECUTION and the draft already exists, archives the previous version before overwriting.
- Writes workspace content to QMS draft path; removes workspace copy.

### Route (`route.py`)

- **Owner-only:** Only `responsible_user` can route.
- **Auto-checkin:** If checked out when routing, performs implicit checkin first.
- **`--review` flag:** Routes DRAFT -> IN_PRE_REVIEW (pre-release phase) or IN_EXECUTION -> IN_POST_REVIEW (post-release phase).
- **`--approval` flag:** Routes PRE_REVIEWED -> IN_PRE_APPROVAL (pre-release) or POST_REVIEWED -> IN_POST_APPROVAL (post-release).
- **Approval gate:** `check_approval_gate(meta)` must pass before approval routing.
- **Assignee auto-default:** If no `--assign` flag, defaults to `["qa"]`.
- Creates inbox tasks for all assignees.

### Release (`release.py`)

- **Status guard:** Must be PRE_APPROVED.
- **Executable guard:** Must be an executable document.
- **Ownership check:** Only owner can release.
- Transitions PRE_APPROVED -> IN_EXECUTION, sets `execution_phase: "post_release"`.

### Revert (`revert.py`)

- **Deprecated** -- preferred alternative is checkout from POST_REVIEWED.
- **Status guard:** Must be POST_REVIEWED.
- Requires `--reason` flag.
- Transitions POST_REVIEWED -> IN_EXECUTION.

### Close (`close.py`)

- **Status guard:** Must be POST_APPROVED.
- **Ownership check:** Only owner can close.
- Moves draft to effective location; deletes draft.
- Clears `responsible_user`, sets status to CLOSED.

---

## 6. Lifecycle

TP follows the full **executable document workflow** with pre-approval (design) and post-approval (execution) phases.

```
DRAFT
  |-- route --review --> IN_PRE_REVIEW
                           |-- review --> PRE_REVIEWED
                                           |-- route --approval --> IN_PRE_APPROVAL
                                                                      |-- approve --> PRE_APPROVED
                                                                      |-- reject --> PRE_REVIEWED
                                           |-- checkout --> DRAFT (revision)
                           |-- withdraw --> DRAFT

PRE_APPROVED
  |-- release --> IN_EXECUTION
  |-- checkout --> DRAFT (scope revision, clears workflow)

IN_EXECUTION
  |-- checkout (minor version bump) --> IN_EXECUTION
  |-- route --review --> IN_POST_REVIEW
                           |-- review --> POST_REVIEWED
                                           |-- route --approval --> IN_POST_APPROVAL
                                                                      |-- approve --> POST_APPROVED
                                                                      |-- reject --> POST_REVIEWED
                                           |-- checkout --> IN_EXECUTION
                                           |-- revert --> IN_EXECUTION (deprecated)
                           |-- withdraw --> IN_EXECUTION

POST_APPROVED
  |-- close --> CLOSED (terminal)
```

### Status Reference

| Status | Phase | Description |
|--------|-------|-------------|
| DRAFT | Pre-release | Being authored or revised |
| IN_PRE_REVIEW | Pre-release | Design review in progress |
| PRE_REVIEWED | Pre-release | Review complete, awaiting approval routing |
| IN_PRE_APPROVAL | Pre-release | Approval decision pending |
| PRE_APPROVED | Pre-release | Approved; ready for release to execution |
| IN_EXECUTION | Post-release | Test protocol is being executed |
| IN_POST_REVIEW | Post-release | Execution results under review |
| POST_REVIEWED | Post-release | Post-review complete, awaiting approval routing |
| IN_POST_APPROVAL | Post-release | Final approval decision pending |
| POST_APPROVED | Post-release | Approved; ready for closure |
| CLOSED | Terminal | Permanently closed |

---

## 7. Parent/Child Relationships

| Relationship | Details |
|-------------|---------|
| **Parent** | [CR](CR.md) (required). TP cannot exist without a parent CR. |
| **Children** | [ER](ER.md) -- Exception Reports are created with `--parent {TP_ID}`. ERs must have a TP parent. |
| **Embedded fragments** | [TC](TC.md) (Test Cases) are not standalone QMS documents. They are sections within the TP body following `TEMPLATE-TC` structure. |

### Filesystem hierarchy example

```
QMS/CR/CR-001/
  CR-001-draft.md                    # Parent CR
  CR-001-TP-001-draft.md             # Test Protocol
  CR-001-TP-001-ER-001-draft.md      # Exception Report (child of TP)
```

---

## 8. Validation Patterns

From `qms_schema.py`, the doc_id regex for TP is:

```python
"TP": re.compile(r"^TP-\d{3}$")
```

Note: This is the legacy standalone pattern. In practice, TPs are identified by containing `-TP-` in the ID string (see `get_doc_type()` in `qms_paths.py`), so IDs like `CR-001-TP-001` are resolved correctly despite not matching the standalone pattern.

From `qms_paths.py`, type resolution logic:

```python
if "-TP-" in doc_id:
    return "TP"
```

The `-TP-ER-` pattern is checked first to avoid misidentifying ERs as TPs.

---

## See Also

- [Change Control](../04-Change-Control.md) -- Test Protocols as CR children
- [Child Documents](../07-Child-Documents.md) -- Decision guide for ER vs VAR vs ADD
- [Execution](../06-Execution.md) -- Executable block structure and evidence requirements
- [ER Reference](ER.md) -- Exception Reports for test failures
- [TC Reference](TC.md) -- Test Case fragment structure
