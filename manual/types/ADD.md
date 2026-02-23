# Document Type: ADD (Addendum Report)

## Overview

An Addendum Report (ADD) is an **executable** document that encapsulates post-closure corrections or supplements to a parent document. ADDs provide a lightweight, formal mechanism for addressing omissions or corrections discovered *after* the parent has closed, without requiring a full [INV/CAPA](INV.md) cycle. See [Child Documents](../07-Child-Documents.md) for the conceptual overview and decision guide.

### ADD vs VAR vs INV

| Type | Timing | Purpose |
|------|--------|---------|
| [VAR](VAR.md) | *During* active execution (parent is IN_EXECUTION) | Handles execution failures |
| ADD | *After* closure (parent is CLOSED) | Handles post-closure corrections |
| [INV](INV.md) | Any timing | Formal investigation of quality events |

---

## Template Structure

Source: `QMS/TEMPLATE/TEMPLATE-ADD.md`

### Frontmatter

```yaml
---
title: '{{TITLE}}'
revision_summary: 'Initial draft'
---
```

Only two fields are author-maintained. All other metadata lives in `.meta/` sidecar files.

### Sections

| # | Section | Purpose | Locked After Pre-Approval? |
|---|---------|---------|---------------------------|
| 1 | Addendum Identification | Table: Parent Document, Discovery Context, ADD Scope | Yes |
| 2 | Description of Omission | What was omitted or needs correction | Yes |
| 3 | Impact Assessment | Effect on parent objectives and downstream | Yes |
| 4 | Correction Plan | How the omission will be addressed, with EI table | Yes |
| 5 | Execution | EI execution table (filled during execution) | **No** (editable during execution) |
| 6 | Scope Handoff | Confirm nothing lost between parent and ADD | **No** (editable during execution) |
| 7 | Execution Summary | Overall outcome narrative | **No** (editable during execution) |
| 8 | References | SOPs, parent doc, additional refs | Yes |

### Section Detail

**Section 1: Addendum Identification**

```markdown
| Parent Document | Discovery Context | ADD Scope |
|-----------------|-------------------|-----------|
| {{PARENT_DOC_ID}} | {{HOW_DISCOVERED}} | {{BRIEF_SCOPE}} |
```

Discovery context examples (from template guidance): "Post-closure review", "Downstream dependency identified gap", "User reported missing configuration", "Audit finding".

**Section 4: Correction Plan**

Contains two parts:
1. Narrative description of the correction plan
2. Planning EI table (static, defines what will be done):

```markdown
| EI | Task Description |
|----|------------------|
| EI-1 | {{TASK}} |
| EI-2 | {{TASK}} |
```

**Section 5: Execution**

Full EI execution table with VR column:

```markdown
| EI | Task Description | VR | Execution Summary | Task Outcome | Performed By -- Date |
|----|------------------|----|-------------------|--------------|---------------------|
| EI-1 | {{DESCRIPTION}} | | [SUMMARY] | [Pass/Fail] | [PERFORMER] -- [DATE] |
```

Includes an Execution Comments sub-table for observations and decisions.

**Section 6: Scope Handoff**

Unique to ADD -- confirms completeness between parent and addendum:

```markdown
| Item | Status |
|------|--------|
| What the parent accomplished | [SUMMARY] |
| What this ADD corrects or supplements | [SUMMARY] |
| Confirmation no scope items were lost | [Yes/No -- if No, explain] |
```

### Placeholder Convention

| Syntax | When Replaced |
|--------|---------------|
| `{{DOUBLE_CURLY}}` | During **authoring** (design time, pre-approval) |
| `[SQUARE_BRACKETS]` | During **execution** (run time, post-release) |

---

## Naming Convention

```
{PARENT_DOC_ID}-ADD-NNN
```

The CLI auto-assigns the next sequential number by scanning existing documents nested under the parent.

| Example | Meaning |
|---------|---------|
| `CR-005-ADD-001` | First addendum to CR-005 |
| `INV-003-ADD-001` | Addendum to an investigation |
| `CR-005-VAR-001-ADD-001` | Addendum to a VAR |
| `CR-005-ADD-001-ADD-001` | Nested ADD (correction of a correction) |

**ID pattern regex** (from `qms_schema.py`):
```python
re.compile(r"^(?:CR|INV)-\d{3}(?:-(?:VAR|ADD)-\d{3})*-ADD-\d{3}$")
```

---

## Parent/Child Relationships

| Relationship | Details |
|--------------|---------|
| Valid parent types | [CR](CR.md), [INV](INV.md), [VAR](VAR.md), ADD |
| Invalid parent types | TP, ER (test corrections use ER/nested ER instead) |
| Required parent state | **CLOSED** (enforced at creation time) |
| Children | ADDs can have child ADDs or VARs |
| Nesting | Unlimited depth |

The parent state requirement is the defining characteristic of ADD: it can *only* be created against a CLOSED parent. This distinguishes it from VAR (which operates during execution).

---

## CLI Creation

```bash
qms --user claude create ADD --parent CR-005 --title "Add missing config step"
```

**Required flags:**

| Flag | Required | Purpose |
|------|----------|---------|
| `--parent` | Yes | Parent document ID (must be CLOSED) |
| `--title` | Yes | Document title |

**CLI enforcement at creation** (`commands/create.py`):

1. `--parent` flag is required; error if missing
2. Parent type must be CR, INV, VAR, or ADD:
   ```python
   if doc_type == "ADD" and parent_type not in ("CR", "INV", "VAR", "ADD"):
       print("Error: ADD documents must have a CR, INV, VAR, or ADD parent")
       return 1
   ```
3. Parent must exist (checks both effective and draft paths)
4. **Parent must be CLOSED** -- this is the critical gate:
   ```python
   if doc_type == "ADD":
       parent_meta = read_meta(parent_id, parent_type)
       if not parent_meta or parent_meta.get("status") != "CLOSED":
           print(f"Error: ADD documents can only be created against CLOSED parents.")
           print(f"Parent {parent_id} is currently {parent_meta.get('status', 'UNKNOWN')}.")
           return 1
   ```
5. Next sequential number is computed via `get_next_nested_number(parent_id, "ADD")`
6. Document is created in DRAFT status at version 0.1
7. Document is automatically checked out to the creating user's workspace
8. Initial `.meta` file is created with `execution_phase: "pre_release"`

---

## Lifecycle

ADD follows the standard executable document lifecycle:

```
DRAFT
  -> IN_PRE_REVIEW -> PRE_REVIEWED
  -> IN_PRE_APPROVAL -> PRE_APPROVED
  -> IN_EXECUTION
  -> IN_POST_REVIEW -> POST_REVIEWED
  -> IN_POST_APPROVAL -> POST_APPROVED
  -> CLOSED
```

### Status Transitions

| From | Action | To |
|------|--------|----|
| DRAFT | route --review | IN_PRE_REVIEW |
| IN_PRE_REVIEW | review (recommend) | PRE_REVIEWED |
| PRE_REVIEWED | route --approval | IN_PRE_APPROVAL |
| IN_PRE_APPROVAL | approve | PRE_APPROVED |
| PRE_APPROVED | release | IN_EXECUTION |
| IN_EXECUTION | route --review | IN_POST_REVIEW |
| IN_POST_REVIEW | review (recommend) | POST_REVIEWED |
| POST_REVIEWED | route --approval | IN_POST_APPROVAL |
| IN_POST_APPROVAL | approve | POST_APPROVED |
| POST_APPROVED | close | CLOSED |

**Additional transitions:**

| From | Action | To | Notes |
|------|--------|----|-------|
| IN_PRE_REVIEW | withdraw | DRAFT | |
| IN_PRE_APPROVAL | withdraw | PRE_REVIEWED | |
| IN_POST_REVIEW | withdraw | IN_EXECUTION | |
| IN_POST_APPROVAL | withdraw | POST_REVIEWED | |
| IN_PRE_APPROVAL | reject | PRE_REVIEWED | |
| IN_POST_APPROVAL | reject | POST_REVIEWED | |
| PRE_APPROVED | checkout | DRAFT | Scope revision |
| POST_REVIEWED | checkout | IN_EXECUTION | Continued execution |

---

## CLI Enforcement Summary

### Checkout (`commands/checkout.py`)

- Terminal states (CLOSED, RETIRED) blocked
- Auto-withdraws from active workflow states if owner checks out
- IN_EXECUTION checkout increments minor version
- PRE_APPROVED checkout transitions to DRAFT (scope revision)
- POST_REVIEWED checkout transitions to IN_EXECUTION

### Checkin (`commands/checkin.py`)

- Standard checkin: ownership verified, content written to draft path
- Archives previous version for IN_EXECUTION documents
- REVIEWED/PRE_REVIEWED revert to DRAFT on checkin

### Route (`commands/route.py`)

- Owner-only routing
- Auto-checkin if checked out
- Approval routing requires approval gate (all RECOMMEND, quality review present)
- WorkflowEngine resolves transition using status + executable flag + execution_phase

### Close (`commands/close.py`)

- Must be POST_APPROVED to close
- Moves document from draft to effective location
- Clears ownership fields
- **Cascade close**: when an ADD closes, the `_cascade_close_attachments` function scans for child "attachment" type documents (currently only VR). Any VR children that are not already in a terminal state will be auto-closed, including auto-compilation of interactive VRs that are still checked out.

---

## Cascade Close Logic

The close command in `commands/close.py` includes cascade close behavior (`_cascade_close_attachments`):

1. When a parent closes, the CLI scans `.meta/{type}/` for children matching `{parent_id}-{prefix}-NNN`
2. Only "attachment" type children are cascade-closed (currently only VR has `"attachment": True` in config)
3. For checked-out interactive attachments (VRs), the CLI auto-compiles from source data before closing
4. Each cascade-closed child gets:
   - Draft promoted to effective location
   - Audit trail entries (CLOSE + STATUS_CHANGE)
   - Meta updated to CLOSED with ownership cleared
   - Workspace files cleaned up across all users

This ensures VR documents attached to an ADD are properly finalized when the ADD closes, even if the VR was still being authored interactively.

---

## Scope Handoff (Section 6)

The Scope Handoff section is unique to ADD and serves as a critical verification checkpoint. It requires the executor to explicitly confirm:

1. What the parent document accomplished
2. What this ADD corrects or supplements
3. That no scope items were lost in the transition

This prevents the common failure mode where a post-closure correction inadvertently drops items that the parent had already addressed.

---

## See Also

- [Child Documents](../07-Child-Documents.md) -- ADD lifecycle, scope handoff, decision guide
- [Execution](../06-Execution.md) -- Scope integrity principle
- [VAR Reference](VAR.md) -- Variance Reports for during-execution deviations
- [VR Reference](VR.md) -- Verification Records as ADD children
- [QMS Glossary](../QMS-Glossary.md) -- Term definitions
