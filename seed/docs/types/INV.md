# Document Type: INV (Investigation)

## Overview

INVs are **executable** documents for investigating deviations and implementing corrective/preventive actions (CAPAs). Like [CRs](CR.md), they follow a two-phase workflow (pre-approval for the investigation plan, post-approval for CAPA execution results). INVs analyze root causes and define CAPAs; the CAPAs themselves may spawn child CRs. See [Deviation Management](../05-Deviation-Management.md) for when to investigate and the root cause analysis approach.

---

## Template Structure

Source: `QMS/TEMPLATE/TEMPLATE-INV.md`

### Frontmatter

```yaml
---
title: '{{TITLE}}'
revision_summary: 'Initial draft'
---
```

| Field | Description | Managed By |
|-------|-------------|------------|
| `title` | Document title | Author (in frontmatter) |
| `revision_summary` | Description of changes in this revision | Author (in frontmatter) |

All other metadata lives in `.meta/INV/{INV-NNN}.json` sidecar files.

### Sections

The template defines a structure per SOP-003 Section 5.

#### Pre-Approved Content (Sections 1-6) -- Locked after pre-approval

| # | Heading | Content |
|---|---------|---------|
| 1 | **Purpose** | Why this investigation exists; what deviation or quality event triggered it |
| 2 | **Scope** | Three subsections: |
| 2.1 | Context | How the deviation was discovered. Includes `Triggering Event:` and `Related Document:` fields |
| 2.2 | Deviation Type | Procedural or Product (per SOP-003 Section 2) |
| 2.3 | Systems/Documents Affected | List of impacted systems, files, or documents |
| 3 | **Background** | Four subsections: |
| 3.1 | Expected Behavior | What was expected to happen |
| 3.2 | Actual Behavior | What actually happened |
| 3.3 | Discovery | When and how the deviation was discovered |
| 3.4 | Timeline | Table: Date / Event |
| 4 | **Description of Deviation(s)** | Two subsections: |
| 4.1 | Facts and Observations | Objective observations about the deviation |
| 4.2 | Evidence | Documents reviewed, system states observed, evidence collected |
| 5 | **Impact Assessment** | Three subsections: |
| 5.1 | Systems Affected | Table: System / Impact (High/Medium/Low) / Description |
| 5.2 | Documents Affected | Table: Document / Impact (High/Medium/Low) / Description |
| 5.3 | Other Impacts | Users, workflows, external systems, or "None" |
| 6 | **Root Cause Analysis** | Two subsections: |
| 6.1 | Contributing Factors | What factors contributed to the deviation |
| 6.2 | Root Cause(s) | The fundamental reason(s) for the deviation |

#### Execution Content (Sections 7-10) -- Editable during execution

| # | Heading | Content |
|---|---------|---------|
| 7 | **Remediation Plan (CAPAs)** | CAPA table (see below) |
| 8 | **Execution Comments** | Observations table |
| 9 | **Execution Summary** | Overall outcome, completed after all CAPAs executed |
| 10 | **References** | Related documents (may be updated during execution) |

#### CAPA Table Columns (Section 7)

| Column | Static/Editable | Description |
|--------|----------------|-------------|
| CAPA | Static | CAPA identifier: `INV-NNN-CAPA-NNN` |
| Type | Static | `Corrective` or `Preventive` |
| Description | Static | What the CAPA accomplishes |
| Implementation | Editable | How it will be implemented, child CR references |
| Outcome | Editable | Pass or Fail |
| Verified By - Date | Editable | Signature |

**CAPA Types (per SOP-003 Section 6):**
- **Corrective Action:** Eliminate cause of existing deviation and/or remediate consequences
- **Preventive Action:** Eliminate cause of potential future deviation; continuous improvement

#### Execution Comments Table (Section 8)

| Column | Description |
|--------|-------------|
| Comment | Observation, decision, or issue |
| Performed By - Date | Signature |

### Placeholder Convention

| Syntax | Meaning | When to Replace |
|--------|---------|-----------------|
| `{{DOUBLE_CURLY}}` | Author-time placeholder | Before routing for pre-review (sections 1-6) |
| `[SQUARE_BRACKETS]` | Execution-time placeholder | During execution (sections 7-10) |

After authoring: no `{{...}}` should remain. All `[...]` should remain until execution.

### Static vs Editable

| Sections | Phase | Editability |
|----------|-------|-------------|
| 1-6 | Pre-approval content | **Locked** after pre-approval |
| 7-10 | Execution content | **Editable** during execution |
| 10 (References) | Hybrid | May be updated to add references discovered during execution |

---

## CLI Creation

### Command

```bash
qms --user claude create INV --title "Investigation of Deviation"
```

### Flags

| Flag | Required | Description |
|------|----------|-------------|
| `type` | Yes (positional) | Must be `INV` |
| `--title` | Yes | Document title. Defaults to `"INV - [Title]"` if omitted |
| `--parent` | No | Not applicable for standalone INVs |
| `--name` | No | Not applicable |

### What Happens on Create

1. **ID assignment:** `get_next_number("INV")` scans `QMS/INV/` for directories/files matching `INV-(\d+)`, finds max, returns `max + 1`
2. **Duplicate check:** Verifies neither draft nor effective path exists
3. **Directory creation:** Creates `QMS/INV/INV-NNN/` (folder-per-doc)
4. **Template loading:** Loads `QMS/TEMPLATE/TEMPLATE-INV.md`, extracts example frontmatter and body, strips template notice
5. **Placeholder substitution:** `{{TITLE}}` -> actual title, `INV-XXX` -> assigned ID
6. **Draft creation:** Writes to `QMS/INV/INV-NNN/INV-NNN-draft.md`
7. **Metadata creation:** `.meta/INV/INV-NNN.json` with `executable: true`, `execution_phase: "pre_release"`
8. **Audit logging:** `CREATE` event to `.audit/INV/INV-NNN.jsonl`
9. **Workspace copy:** `.claude/users/{user}/workspace/INV-NNN.md`

---

## CLI Enforcement by Operation

INVs follow the **same executable workflow enforcement as [CRs](CR.md)** in every command. All checks documented in the [CR reference](CR.md) apply identically to INVs. The key differences are noted below.

### Checkout (`checkout.py`)

Identical to CR behavior:

| Check | Detail |
|-------|--------|
| PRE_APPROVED checkout | PRE_APPROVED -> DRAFT (scope revision) |
| POST_REVIEWED checkout | POST_REVIEWED -> IN_EXECUTION |
| IN_EXECUTION checkout | Minor version increment |
| Terminal state guard | CLOSED and RETIRED cannot be checked out |

### Checkin (`checkin.py`)

Identical to CR behavior:

| Check | Detail |
|-------|--------|
| IN_EXECUTION archival | Archives previous version |
| PRE_REVIEWED revert | Reverts to DRAFT |

### Route (`route.py`)

Identical to CR behavior. Same WorkflowEngine transitions, same approval gate checks.

### Review, Approve, Reject, Release, Revert, Close

All identical to CR behavior. The workflow engine makes no distinction between CR and INV -- both are executable documents processed through the same state machine.

### Cancel (`cancel.py`)

Same as CR. Note: for INV documents, the cancel command does not have INV-specific directory cleanup (unlike CRs which check for empty CR directories). INV directories remain if they contain other files.

### Close (`close.py`) -- INV-Specific Note

The close command checks if the document type is an executable document. INVs qualify. The cascade-close logic for attachment documents also applies if INVs have VR children. However, per `create.py`, VR documents can only have CR, VAR, or ADD parents -- **not INV parents**. So cascade close for VR attachments does not apply to INVs.

---

## Lifecycle

### Status Progression (Happy Path)

```
DRAFT -> IN_PRE_REVIEW -> PRE_REVIEWED -> IN_PRE_APPROVAL -> PRE_APPROVED
      -> IN_EXECUTION
      -> IN_POST_REVIEW -> POST_REVIEWED -> IN_POST_APPROVAL -> POST_APPROVED
      -> CLOSED
```

This is identical to the CR lifecycle. The workflow engine uses the same `WORKFLOW_TRANSITIONS` list for both.

### Full State Diagram

The state diagram is identical to the CR state diagram. See `CR.md` for the full diagram. All transitions, withdrawals, and revision paths apply equally.

### Terminal States

| State | How Reached | Recoverable? |
|-------|-------------|--------------|
| CLOSED | `close` from POST_APPROVED | No |
| RETIRED | `--retire` on approval routing | No |

### Withdraw Transitions

| From | To |
|------|----|
| IN_PRE_REVIEW | DRAFT |
| IN_PRE_APPROVAL | PRE_REVIEWED |
| IN_POST_REVIEW | IN_EXECUTION |
| IN_POST_APPROVAL | POST_REVIEWED |

### Version Numbering

Identical to CR:

| Event | Version Change | Example |
|-------|---------------|---------|
| Create | `0.1` | Initial draft |
| Checkout from IN_EXECUTION | `{major}.{minor+1}` | `1.0` -> `1.1` |
| Pre-approval | `{major+1}.0` | `0.1` -> `1.0` |
| Post-approval | `{major+1}.0` | `1.2` -> `2.0` |

### Execution Phase Tracking

Identical to CR. `execution_phase` starts as `"pre_release"` and changes to `"post_release"` on release. Never reset.

---

## Parent/Child Relationships

### INVs as Parents

| Child Type | ID Format | Parent Status Required | Relationship |
|------------|-----------|----------------------|--------------|
| [VAR](VAR.md) | `INV-NNN-VAR-NNN` | Any (no status check on VAR creation) | Variance from INV plan |

### INVs Cannot Be Parents Of

| Child Type | Reason |
|------------|--------|
| TP | TP requires CR parent (`create.py`: "TP documents must have a CR parent") |
| ER | ER requires TP parent |
| VR | VR requires CR, VAR, or ADD parent |
| ADD | ADD requires CR, INV, VAR, or ADD parent **and** parent must be CLOSED |

Note: ADD documents **can** be created against closed INVs. The `create.py` code allows ADD parents of type CR, INV, VAR, or ADD.

### INVs as Children

INVs are never children of other documents in the CLI hierarchy. They are always top-level documents.

### CAPAs and Child CRs

CAPAs are not separate QMS documents -- they are rows in the INV's Section 7 CAPA table. CAPAs may spawn child CRs that implement the corrective/preventive action. These CRs are referenced in the CAPA table's Implementation column but are created as independent top-level CRs (not as children of the INV in the CLI hierarchy).

---

## Naming Convention

| Component | Format | Example |
|-----------|--------|---------|
| Prefix | `INV` | -- |
| Number | 3-digit zero-padded | `001`, `014` |
| Full ID | `INV-NNN` | `INV-001`, `INV-014` |
| CAPA ID | `INV-NNN-CAPA-NNN` | `INV-001-CAPA-001` (table identifiers, not QMS doc IDs) |
| Draft filename | `INV-NNN-draft.md` | `INV-014-draft.md` |
| Effective filename | `INV-NNN.md` | `INV-014.md` |
| Storage path | `QMS/INV/INV-NNN/` | Folder-per-doc |
| Meta path | `QMS/.meta/INV/INV-NNN.json` | |
| Audit path | `QMS/.audit/INV/INV-NNN.jsonl` | |
| Archive path | `QMS/.archive/INV/INV-NNN/INV-NNN-v{version}.md` | |

Child documents (VARs) are stored in the parent INV's folder:
- `QMS/INV/INV-001/INV-001-VAR-001-draft.md`

---

## Configuration

From `qms_config.py`:

```python
"INV": {"path": "INV", "executable": True, "prefix": "INV", "folder_per_doc": True}
```

| Key | Value | Meaning |
|-----|-------|---------|
| `path` | `"INV"` | Stored under `QMS/INV/` |
| `executable` | `True` | Executable workflow (pre/post approval, execution phase) |
| `prefix` | `"INV"` | ID prefix for numbering |
| `folder_per_doc` | `True` | Each INV gets its own directory: `QMS/INV/INV-NNN/` |

---

## Initial Metadata

Created by `create_initial_meta()`:

```json
{
  "doc_id": "INV-014",
  "doc_type": "INV",
  "version": "0.1",
  "status": "DRAFT",
  "executable": true,
  "execution_phase": "pre_release",
  "responsible_user": "claude",
  "checked_out": true,
  "checked_out_date": "2026-02-22",
  "effective_version": null,
  "pending_assignees": []
}
```

---

## Key Differences from CR

While INVs share the same executable workflow as CRs, the template structure differs significantly:

| Aspect | CR | INV |
|--------|-----|-----|
| Pre-approved sections | 1-9 (plan, justification, impact, implementation) | 1-6 (investigation, root cause analysis) |
| Execution content | EI table (Section 10) | CAPA table (Section 7) |
| Execution unit | Execution Items (EI-1, EI-2, ...) | CAPAs (INV-NNN-CAPA-001, ...) |
| Purpose | Authorize and track implementation of a change | Investigate deviation and implement corrective/preventive actions |
| Child CRs | CRs don't typically spawn child CRs | CAPAs frequently spawn child CRs for implementation |
| VR support | Yes (VR can have CR parent) | No (VR cannot have INV parent per `create.py`) |
| ADD support | Yes (ADD against CLOSED CR) | Yes (ADD against CLOSED INV) |
| Section locked after pre-approval | Sections 1-9 | Sections 1-6 |
| References section | Section 12 | Section 10 |

### Structural Mapping

| CR Section | INV Equivalent | Notes |
|------------|----------------|-------|
| 2.1 Context / Parent Document | 2.1 Context / Triggering Event, Related Document | INV uses "Triggering Event" instead of "Parent Document" |
| 2.2 Changes Summary | 2.2 Deviation Type | INV classifies as Procedural or Product |
| 2.3 Files Affected | 2.3 Systems/Documents Affected | Similar scope definition |
| 3 Current State | 3 Background (3.1-3.4) | INV has more structured background with expected/actual/discovery/timeline |
| 4 Proposed State | 4 Description of Deviation(s) | INV has facts/observations and evidence |
| 5 Change Description | 5 Impact Assessment | Similar but different focus |
| 6 Justification | 6 Root Cause Analysis | INV's unique contribution -- contributing factors + root causes |
| 7 Impact Assessment | (covered in Section 5) | |
| 8 Testing Summary | (not applicable) | |
| 9 Implementation Plan | (CAPAs define the remediation plan) | |
| 10 Execution (EI table) | 7 Remediation Plan (CAPA table) | Different table structure |
| 10 Execution Comments | 8 Execution Comments | Same format |
| 11 Execution Summary | 9 Execution Summary | Same purpose |
| 12 References | 10 References | Same purpose |

---

## See Also

- [Deviation Management](../05-Deviation-Management.md) -- When to investigate, root cause analysis, CAPA concepts
- [CR Reference](CR.md) -- Full state diagram (shared with INV) and CLI enforcement details
- [Execution](../06-Execution.md) -- Executable block structure and evidence requirements
- [Child Documents](../07-Child-Documents.md) -- VAR and ADD child documents for INVs
- [QMS Glossary](../QMS-Glossary.md) -- Term definitions
