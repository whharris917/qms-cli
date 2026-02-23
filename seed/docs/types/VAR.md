# Document Type: VAR (Variance Report)

## Overview

A Variance Report (VAR) is an **executable** document that encapsulates resolution work for variances encountered during the execution of a parent document. VARs are blocking child containers -- the parent cannot proceed until the VAR clears its block condition. See [Child Documents](../07-Child-Documents.md) for the conceptual overview and decision guide.

VARs can be attached to any executable document type: [CR](CR.md), [INV](INV.md), TC, TP.

---

## Template Structure

Source: `QMS/TEMPLATE/TEMPLATE-VAR.md`

### Frontmatter

```yaml
---
title: '{{TITLE}}'
revision_summary: 'Initial draft'
---
```

Only two fields are author-maintained. All other metadata (version, status, responsible_user, dates) lives in the `.meta/` sidecar managed by the CLI.

### Sections

| # | Section | Purpose | Locked After Pre-Approval? |
|---|---------|---------|---------------------------|
| 1 | Variance Identification | Table: Parent Document, Failed Item, VAR Type | Yes |
| 2 | Detailed Description | What happened? Expected vs. actual? | Yes |
| 3 | Root Cause | Why did this happen? | Yes |
| 4 | Variance Type | Classification of the variance | Yes |
| 5 | Impact Assessment | Effect on parent document's objectives | Yes |
| 6 | Proposed Resolution | What will be done to address root cause | Yes |
| 7 | Resolution Work | Actual work performed during execution | **No** (editable during execution) |
| 8 | VAR Closure | Resolution details, outcome, performer | **No** (editable during execution) |
| 9 | References | SOPs, parent doc, additional refs | Yes |

### Section Detail

**Section 1: Variance Identification**

```markdown
| Parent Document | Failed Item | VAR Type |
|-----------------|-------------|----------|
| {{PARENT_DOC_ID}} | {{ITEM_ID}} | {{TYPE_1_or_TYPE_2}} |
```

Includes a persistent HTML comment explaining Type 1 vs Type 2 (retained during execution).

**Section 4: Variance Type**

Select one from the embedded guidance:
- Execution Error
- Scope Error
- System Error
- Documentation Error
- External Factor
- Other

**Section 7: Resolution Work**

The template provides guidance for three structural options depending on the parent type:

| Parent Type | Structure |
|-------------|-----------|
| TC or TP | TC structure: Prerequisite Section, Test Script, Comments |
| CR or INV | EI table: `EI / Task Description / VR / Execution Summary / Task Outcome / Performed By -- Date` |
| Simple resolution | Narrative + evidence format |

The VR column in the EI table is set to "Yes" for items requiring behavioral verification (per SOP-004 Section 9C).

**Section 8: VAR Closure**

```markdown
| Details of Resolution | Outcome | Performed By -- Date |
|-----------------------|---------|---------------------|
| [RESOLUTION_DETAILS] | [OUTCOME] | [PERFORMER] -- [DATE] |
```

### Placeholder Convention

| Syntax | When Replaced |
|--------|---------------|
| `{{DOUBLE_CURLY}}` | During **authoring** (design time, pre-approval) |
| `[SQUARE_BRACKETS]` | During **execution** (run time, post-release) |

---

## VAR Types: Type 1 vs Type 2

| Property | Type 1 | Type 2 |
|----------|--------|--------|
| Block condition | Full closure of VAR required | Pre-approval sufficient |
| Use when | Resolution is critical; parent cannot close until fix is proven | Variance does not affect conceptual closure; impacts are understood and contained |
| Parent can close when | VAR is CLOSED | VAR is PRE_APPROVED (or later) |
| Rationale | Ensures fix is verified end-to-end | Prevents issues from "falling off the radar" while keeping parent from waiting inefficiently |

---

## Naming Convention

```
{PARENT_DOC_ID}-VAR-NNN
```

The CLI auto-assigns the next sequential number by scanning existing documents nested under the parent.

| Example | Meaning |
|---------|---------|
| `CR-005-VAR-001` | First variance from CR-005 |
| `TP-001-TC-002-VAR-001` | Variance from a TC within a TP |
| `INV-003-VAR-001` | Variance from an investigation |
| `CR-005-VAR-001-VAR-001` | Nested VAR (resolution work encountered its own issue) |

**ID pattern regex** (from `qms_schema.py`):
```python
re.compile(r"^(?:CR|INV)-\d{3}-VAR-\d{3}$")
```

---

## Parent/Child Relationships

| Relationship | Details |
|--------------|---------|
| Valid parents | Any executable document (CR, INV, TC, TP, VAR) -- validated by parent existence check, not by type restriction in CLI |
| Required parent state | No state restriction at creation (unlike ADD which requires CLOSED, or VR which requires IN_EXECUTION) |
| Children | VARs can have child VARs (nesting), [VRs](VR.md), or [ADDs](ADD.md) |
| Nesting | Unlimited depth: `CR-005-VAR-001-VAR-001` |

---

## CLI Creation

```bash
qms --user claude create VAR --parent CR-005 --title "Fix broken validation logic"
```

**Required flags:**

| Flag | Required | Purpose |
|------|----------|---------|
| `--parent` | Yes | Parent document ID |
| `--title` | Yes | Document title |

**CLI enforcement at creation** (`commands/create.py`):

1. `--parent` flag is required; error if missing
2. Parent document must exist (checks both effective and draft paths)
3. No parent status restriction (unlike ADD or VR)
4. Next sequential number is computed via `get_next_nested_number(parent_id, "VAR")`
5. Document is created in DRAFT status at version 0.1
6. Document is automatically checked out to the creating user's workspace
7. Initial `.meta` file is created with `execution_phase: "pre_release"`

---

## Lifecycle

VAR follows the standard executable document lifecycle:

```
DRAFT
  -> IN_PRE_REVIEW -> PRE_REVIEWED
  -> IN_PRE_APPROVAL -> PRE_APPROVED
  -> IN_EXECUTION
  -> IN_POST_REVIEW -> POST_REVIEWED
  -> IN_POST_APPROVAL -> POST_APPROVED
  -> CLOSED
```

### Status Transitions (from `workflow.py`)

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
| IN_PRE_REVIEW | withdraw | DRAFT | Owner can withdraw from workflow |
| IN_PRE_APPROVAL | withdraw | PRE_REVIEWED | |
| IN_POST_REVIEW | withdraw | IN_EXECUTION | |
| IN_POST_APPROVAL | withdraw | POST_REVIEWED | |
| IN_PRE_APPROVAL | reject | PRE_REVIEWED | Approver rejects |
| IN_POST_APPROVAL | reject | POST_REVIEWED | |
| PRE_APPROVED | checkout | DRAFT | Scope revision |
| POST_REVIEWED | checkout | IN_EXECUTION | Continued execution |
| POST_REVIEWED | revert | IN_EXECUTION | Revert to execution |

---

## CLI Enforcement Summary

### Checkout (`commands/checkout.py`)

- Terminal states (CLOSED, RETIRED) are blocked
- Auto-withdraws from active workflow states (IN_PRE_REVIEW, etc.) if owner checks out
- IN_EXECUTION checkout increments minor version (creates N.X+1 in workspace)
- PRE_APPROVED checkout transitions to DRAFT (scope revision)
- POST_REVIEWED checkout transitions to IN_EXECUTION

### Checkin (`commands/checkin.py`)

- User must have document checked out (ownership verified via `.meta`)
- Archives previous version for IN_EXECUTION documents before writing new version
- REVIEWED/PRE_REVIEWED states revert to DRAFT on checkin (new version needs review)

### Route (`commands/route.py`)

- Owner-only: only `responsible_user` can route
- Auto-checkin if document is checked out when routing
- Approval routing requires passing the approval gate (`check_approval_gate`):
  - All reviews must have RECOMMEND outcome
  - At least one review by a quality group member
- WorkflowEngine determines valid transitions based on current status, executable flag, and execution_phase

### Close (`commands/close.py`)

- Must be POST_APPROVED to close (standard executable rule)
- Moves document from draft to effective location
- Clears ownership fields
- No cascade close logic for VAR (VAR is not an "attachment" type in config)

---

## Scope Handoff

VARs serve as a containment boundary. The parent document does not track variance resolution details -- it only knows that a VAR was created and whether it has cleared. This separation ensures:

1. The parent's execution log stays clean
2. Resolution work gets its own review/approval cycle
3. Nested variances are possible without polluting the parent

The parent document's EI table should reference the VAR ID in the relevant row but does not duplicate the resolution content.

---

## See Also

- [Child Documents](../07-Child-Documents.md) -- Type 1 vs Type 2 VARs, scope handoff, decision guide
- [Execution](../06-Execution.md) -- Scope integrity principle and task outcome handling
- [ADD Reference](ADD.md) -- Post-closure corrections (vs VAR during execution)
- [VR Reference](VR.md) -- Verification Records as VAR children
- [QMS Glossary](../QMS-Glossary.md) -- Term definitions
