# ER -- Exception Report

## Document Type Summary

| Property | Value |
|----------|-------|
| **Type code** | `ER` |
| **Executable** | Yes |
| **Parent required** | Yes -- must be a [`TP`](TP.md) |
| **Children** | Nested ERs (ER under same parent TP) |
| **Folder-per-doc** | Listed as `True` in `qms_config.py` but files resolve into the parent CR folder |
| **Template** | `QMS/TEMPLATE/TEMPLATE-ER.md` |

---

## 1. Naming Convention

| Pattern | Example |
|---------|---------|
| `{TP_ID}-ER-{NNN}` | `CR-001-TP-001-ER-001` |
| Nested ER (in template ID scheme) | `TP-001-TC-001-ER-001-ER-001` |

The sequential number `NNN` is zero-padded to 3 digits. Numbering is scoped to the parent TP: the CLI calls `get_next_nested_number(parent_id, "ER")` which scans the parent CR folder for existing `{parent_id}-ER-NNN` files and increments from the highest found.

**Type resolution** (`qms_paths.py`):

```python
if "-TP-ER-" in doc_id:
    return "ER"
```

The `-TP-ER-` pattern is checked **before** the `-TP-` check to avoid misidentifying ERs as TPs.

**File paths:**

| Variant | Path |
|---------|------|
| Draft | `QMS/CR/{CR_ID}/{TP_ID}-ER-{NNN}-draft.md` |
| Effective | `QMS/CR/{CR_ID}/{TP_ID}-ER-{NNN}.md` |
| Archive | `QMS/.archive/CR/{CR_ID}/{TP_ID}-ER-{NNN}-v{version}.md` |

All ER files live in the top-level CR folder alongside their parent TP, resolved via the `CR-NNN` prefix extracted from the doc_id (`qms_paths.py` lines 136-141).

---

## 2. Template Structure

### Frontmatter

```yaml
---
title: '{{TITLE}}'
revision_summary: 'Initial draft'
---
```

Two author-maintained fields only. All metadata is in `.meta/ER/{doc_id}.json`.

### Sections

| # | Heading | Content | Static/Editable |
|---|---------|---------|-----------------|
| 1 | **Exception Identification** | Table: Parent Test Case ID, Failed Step ID. | **Locked** after pre-approval |
| 2 | **Detailed Description** | Narrative: what happened, expected vs actual. | **Locked** after pre-approval |
| 3 | **Root Cause** | Analysis of why the failure occurred. | **Locked** after pre-approval |
| 4 | **Proposed Corrective Action** | What will be done to fix the root cause before re-testing. | **Locked** after pre-approval |
| 5 | **Exception Type** | Classification of the failure (see below). | **Locked** after pre-approval |
| 6 | **Re-test** | Full re-execution of the test case following TC-TEMPLATE structure. | **Editable** during execution |
| 7 | **ER Closure** | Resolution details, outcome, performer signature. | **Editable** during execution |
| 8 | **References** | Links to SOP-004, TC-TEMPLATE, parent TC, additional refs. | Locked after pre-approval |

### Section 1: Exception Identification

```markdown
## 1. Exception Identification

| Parent Test Case | Failed Step |
|------------------|-------------|
| {{TC_ID}} | {{STEP_ID}} |
```

Links the ER to the specific test case and step that triggered it.

### Section 5: Exception Type Values

The template includes a preserved comment listing the valid classifications:

| Value | Meaning |
|-------|---------|
| Test Script Error | The test itself was written or designed incorrectly |
| Test Execution Error | The tester made a mistake by not following instructions as written |
| System Error | The system under test behaved unexpectedly |
| Documentation Error | Error in a document other than the test script itself |
| Other | See Detailed Description for explanation |

### Section 6: Re-test

The re-test section contains a **full re-execution of the test case** (not just the failed step). It follows the complete `TEMPLATE-TC` structure:

```markdown
## 6. Re-test

### Re-test: {{TC_ID}}

#### Prerequisite Section
| Test Case ID | Objectives | Prerequisites | Performed By -- Date |
|--------------|------------|---------------|---------------------|
| {{TC_ID}} | {{OBJECTIVES}} | {{PREREQUISITES}} | [PERFORMER] -- [DATE] |

The signature above indicates that all listed test prerequisites have been
satisfied and that the test script below is ready for execution.

---

#### Test Script

**Instructions:** Test execution must be performed in accordance with SOP-004 ...

**Acceptance Criteria:** A test case is accepted when either: (1) all test steps
pass ... or (2) a step failed, subsequent steps are marked N/A with nested ER
reference, and the nested ER contains a successful full re-execution and is closed.

| Step | REQ ID | Instruction | Expected Result | Actual Result | Pass/Fail | Performed By -- Date |
|------|--------|-------------|-----------------|---------------|-----------|---------------------|
| {{STEP_ID}}-001 | {{REQ_ID}} | {{INSTRUCTION}} | {{EXPECTED}} | [ACTUAL] | [Pass/Fail] | [PERFORMER] -- [DATE] |
| {{STEP_ID}}-002 | {{REQ_ID}} | {{INSTRUCTION}} | {{EXPECTED}} | [ACTUAL] | [Pass/Fail] | [PERFORMER] -- [DATE] |
| {{STEP_ID}}-003 | {{REQ_ID}} | {{INSTRUCTION}} | {{EXPECTED}} | [ACTUAL] | [Pass/Fail] | [PERFORMER] -- [DATE] |

---

#### Test Execution Comments
| Comment | Performed By -- Date |
|---------|---------------------|
| [COMMENT] | [PERFORMER] -- [DATE] |
```

Key differences from the standard TC template in an ER context:
- The instructions text says "create a **nested ER**" on failure (vs "follow the ER workflow" in original TC)
- Step IDs use `{{STEP_ID}}-NNN` format (where STEP_ID is the failed step from Section 1)
- The comments section notes that nested ERs applying to the re-test as a whole go here

### Section 7: ER Closure

```markdown
## 7. ER Closure

| Details of Resolution | Outcome | Performed By -- Date |
|-----------------------|---------|---------------------|
| [RESOLUTION_DETAILS] | [OUTCOME] | [PERFORMER] -- [DATE] |
```

Filled during execution after re-test completes.

---

## 3. Placeholder Convention

| Syntax | Phase | Example |
|--------|-------|---------|
| `{{DOUBLE_CURLY}}` | Authoring | `{{ER_ID}}`, `{{TC_ID}}`, `{{STEP_ID}}`, `{{ROOT_CAUSE}}`, `{{EXCEPTION_TYPE}}`, `{{OBJECTIVES}}`, `{{PREREQUISITES}}`, `{{REQ_ID}}`, `{{INSTRUCTION}}`, `{{EXPECTED}}` |
| `[SQUARE_BRACKETS]` | Execution | `[ACTUAL]`, `[Pass/Fail]`, `[PERFORMER]`, `[DATE]`, `[RESOLUTION_DETAILS]`, `[OUTCOME]`, `[COMMENT]` |

After authoring: zero `{{...}}` remain; all `[...]` remain until execution.

---

## 4. CLI Creation

### Command

```bash
qms --user claude create ER --parent CR-001-TP-001 --title "TC-001 Step 003 Failure: Widget not rendered"
```

### Required flags

| Flag | Required | Description |
|------|----------|-------------|
| `--parent` | **Yes** | Parent TP document ID. CLI validates: (1) parent exists, (2) parent type is `TP`. |
| `--title` | No | Document title. Defaults to `"ER - [Title]"` if omitted. |

### Error message on missing parent

```
Error: ER documents require --parent flag
Usage: qms create ER --parent CR-001-TP-001 --title "..."
```

### What `create.py` enforces

1. **Parent type validation:** `doc_type == "ER" and parent_type != "TP"` triggers error `"ER documents must have a TP parent"`. The parent type is determined by `get_doc_type(parent_id)` which checks for `-TP-` in the ID.
2. **Parent existence:** Checks both `get_doc_path(parent_id)` (effective) and `get_doc_path(parent_id, draft=True)` (draft). If neither exists: `"Error: Parent document {parent_id} does not exist"`.
3. **No parent status restriction:** Unlike ADD (requires CLOSED parent) or VR (requires IN_EXECUTION parent), ER has no restriction on the parent TP's status.
4. **ID generation:** Calls `get_next_nested_number(parent_id, "ER")` -- scans the parent CR folder for `{parent_id}-ER-NNN` files.
5. **Template loading:** Reads `QMS/TEMPLATE/TEMPLATE-ER.md`, strips TEMPLATE DOCUMENT NOTICE, substitutes `{{TITLE}}`.
6. **Initial meta:** Creates `.meta/ER/{doc_id}.json` with `version: "0.1"`, `status: "DRAFT"`, `executable: True`.
7. **Workspace copy:** Copies draft to user workspace; document is checked out on creation.

---

## 5. CLI Enforcement by Operation

### Checkout (`checkout.py`)

Standard executable document rules:
- **Terminal state guard:** CLOSED/RETIRED cannot be checked out.
- **Auto-withdraw:** If in an active workflow state and owner checks out, implicit withdraw first.
- **PRE_APPROVED checkout:** Transitions to DRAFT (scope revision -- clears workflow tracking).
- **POST_REVIEWED checkout:** Transitions to IN_EXECUTION (continued execution).
- **IN_EXECUTION checkout:** Increments minor version (e.g., 1.0 -> 1.1).

### Checkin (`checkin.py`)

Standard executable document rules:
- Ownership verification.
- IN_EXECUTION archival of previous version before overwriting.
- Writes workspace to QMS draft; removes workspace copy.

### Route (`route.py`)

Standard executable document routing:
- Owner-only routing.
- Auto-checkin if checked out.
- `--review`: DRAFT -> IN_PRE_REVIEW (pre-release) or IN_EXECUTION -> IN_POST_REVIEW (post-release).
- `--approval`: PRE_REVIEWED -> IN_PRE_APPROVAL (pre-release) or POST_REVIEWED -> IN_POST_APPROVAL (post-release).
- Approval gate check before approval routing.
- Auto-defaults assignees to `["qa"]`.

### Release (`release.py`)

- Must be PRE_APPROVED.
- Transitions to IN_EXECUTION, sets `execution_phase: "post_release"`.

### Revert (`revert.py`)

- **Deprecated** -- preferred alternative is checkout from POST_REVIEWED.
- Must be POST_REVIEWED -> IN_EXECUTION.
- Requires `--reason` flag.

### Close (`close.py`)

- Must be POST_APPROVED.
- Moves draft to effective; clears ownership; status -> CLOSED.

---

## 6. Lifecycle

ER follows the same full executable document workflow as TP.

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
  |-- checkout --> DRAFT (scope revision)

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
| DRAFT | Pre-release | ER being authored (exception analysis, corrective action, re-test design) |
| IN_PRE_REVIEW | Pre-release | Pre-review of ER plan and re-test design |
| PRE_REVIEWED | Pre-release | Review complete |
| IN_PRE_APPROVAL | Pre-release | Pre-approval pending |
| PRE_APPROVED | Pre-release | Approved to execute re-test |
| IN_EXECUTION | Post-release | Re-test being executed |
| IN_POST_REVIEW | Post-release | Re-test results under review |
| POST_REVIEWED | Post-release | Post-review complete |
| IN_POST_APPROVAL | Post-release | Final approval pending |
| POST_APPROVED | Post-release | Approved for closure |
| CLOSED | Terminal | ER resolved and closed |

---

## 7. Parent/Child Relationships

| Relationship | Details |
|-------------|---------|
| **Parent** | [TP](TP.md) (required). ER cannot exist without a parent TP. |
| **Grandparent** | [CR](CR.md) (via TP). The ER's filesystem location is derived from the CR ancestor. |
| **Children** | Nested ERs. If the re-test fails, a new ER is created under the same parent TP. |

### What cannot be an ER parent

From `create.py`:
```python
if doc_type == "ER" and parent_type != "TP":
    print("Error: ER documents must have a TP parent")
    return 1
```

Only `TP` is accepted. Attempting `--parent CR-001` or `--parent CR-001-TP-001-ER-001` will fail.

### Document hierarchy example

```
CR-001                                    # Change Record
  CR-001-TP-001                           # Test Protocol
    CR-001-TP-001-ER-001                  # Exception Report (re-test of a TC)
    CR-001-TP-001-ER-002                  # Another ER (or for nested failure)
```

---

## 8. Re-Execution Mechanics

The ER's defining characteristic is the **re-test cycle**. Understanding the two-phase structure is essential.

### Pre-release phase (Sections 1-5: "What went wrong and what we'll do about it")

1. **Identify** the failed step and parent TC (Section 1)
2. **Describe** what happened vs what was expected (Section 2)
3. **Analyze** root cause (Section 3)
4. **Plan** corrective action (Section 4)
5. **Classify** the exception type (Section 5)
6. **Design** the re-test in Section 6 -- the test script for re-execution, potentially revised from the original

This phase goes through pre-review and pre-approval. Reviewers verify that:
- Root cause analysis is sound
- Corrective action addresses the root cause
- Re-test design is adequate
- If the test script is modified, it still meets the original objectives

### Post-release phase (Section 6 execution + Section 7: "Re-run and close")

1. **Release** the ER to enter IN_EXECUTION
2. **Execute** the full re-test -- the entire test case, not just the failed step
3. Fill Section 6 execution columns (Actual Result, Pass/Fail, Performed By)
4. If re-test **passes**: Fill Section 7 closure table, route for post-review/approval, close
5. If re-test **fails**: Create a nested ER under the same parent TP

### Nested ER pattern

```
CR-001-TP-001-TC-001           # Original test case fails at step 003
  CR-001-TP-001-ER-001         # ER created; re-test also fails
    CR-001-TP-001-ER-002       # New ER for the re-test failure (same TP parent)
```

Each ER goes through its own full lifecycle (DRAFT -> ... -> CLOSED).

### Re-test design flexibility

The re-test in Section 6 may differ from the original test case:

| Exception Type | Likely Re-test Change |
|----------------|----------------------|
| Test Script Error | Different or corrected steps |
| Test Execution Error | Same steps (tester re-executes correctly) |
| System Error | Same steps (system is fixed) |
| Documentation Error | Steps may reference corrected documentation |

Reviewers must verify that any test design changes still meet the intent of the original objectives. If the TC objectives themselves are modified, this must be justified in the ER.

---

## 9. Validation Patterns

From `qms_schema.py`:

```python
"ER": re.compile(r"^ER-\d{3}$")
```

This is the legacy standalone pattern. In practice, ERs are identified by the `-TP-ER-` substring in `get_doc_type()`:

```python
if "-TP-ER-" in doc_id:
    return "ER"
```

ERs are in `EXECUTABLE_TYPES` and `FOLDER_DOC_TYPES` per `qms_schema.py`:

```python
EXECUTABLE_TYPES = {"CR", "INV", "CAPA", "TP", "ER", "VAR", "VR", "ADD"}
FOLDER_DOC_TYPES = {"CR", "INV", "CAPA", "TP", "ER", "VAR", "ADD"}
```

---

## See Also

- [Child Documents](../07-Child-Documents.md) -- Decision guide for ER vs VAR vs ADD
- [TP Reference](TP.md) -- Test Protocols (ER parent type)
- [TC Reference](TC.md) -- Test Case fragment structure used in re-test sections
- [Execution](../06-Execution.md) -- Evidence requirements and scope integrity
- [QMS Glossary](../QMS-Glossary.md) -- Term definitions
