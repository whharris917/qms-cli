# Document Type: CR (Change Record)

## Overview

CRs are **executable** documents that authorize implementation activities. They follow a two-phase workflow: pre-approval (plan review) and post-approval (execution review). CRs pass through pre-review, pre-approval, execution, post-review, post-approval, and close stages. See [Change Control](../04-Change-Control.md) for the conceptual overview and [Workflows](../03-Workflows.md) for the executable lifecycle state machine.

---

## Template Structure

Source: `QMS/TEMPLATE/TEMPLATE-CR.md`

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

All other metadata lives in `.meta/CR/{CR-NNN}.json` sidecar files.

### Sections

The template defines a strict structure per SOP-002 Section 6.

#### Pre-Approved Content (Sections 1-9) -- Locked after pre-approval

| # | Heading | Content |
|---|---------|---------|
| 1 | **Purpose** | What problem does this CR solve? What improvement does it introduce? |
| 2 | **Scope** | Three subsections: |
| 2.1 | Context | Parent investigation, CAPA, or origin of change. Includes `Parent Document:` field |
| 2.2 | Changes Summary | Brief description of what will change |
| 2.3 | Files Affected | List of files with descriptions of changes |
| 3 | **Current State** | Declarative present-tense statement of what exists now |
| 4 | **Proposed State** | Declarative present-tense statement of what will exist after |
| 5 | **Change Description** | Full technical details, structured with numbered subsections (5.1, 5.2, ...) |
| 6 | **Justification** | Why the change is needed: problem, impact of not changing, how the solution addresses root cause |
| 7 | **Impact Assessment** | Four subsections: |
| 7.1 | Files Affected | Table: File / Change Type / Description |
| 7.2 | Documents Affected | Table: Document / Change Type / Description |
| 7.3 | Other Impacts | External systems, dependencies, or "None" |
| 7.4 | Development Controls | (Code CRs only) Test environment isolation, branch isolation, write protection, CI, PR gate, submodule update |
| 7.5 | Qualified State Continuity | (Code CRs only) Table showing main branch state, RS/RTM status, and qualified release across phases |
| 8 | **Testing Summary** | Two subsections (code CRs) or simple list (document CRs): |
| 8.1 | Automated Verification | Unit tests, CI checks, qualification tests |
| 8.2 | Integration Verification | What will be launched, what functionality exercised, what behavior demonstrates effectiveness |
| 9 | **Implementation Plan** | Phases (see below) |

#### Implementation Plan Phases (Section 9 subsections, for code CRs)

| Phase | Heading | Purpose |
|-------|---------|---------|
| 9.1 | Test Environment Setup | Verify/create dev directory, clone repo, create branch |
| 9.2 | Requirements (RS Update) | Checkout RS, add/modify requirements, route for approval |
| 9.3 | Implementation | Implement changes, test locally, commit |
| 9.4 | Qualification | Add/update tests, run suite, push, verify CI |
| 9.5 | Integration Verification | Launch application, exercise functionality, confirm effectiveness |
| 9.6 | RTM Update and Approval | Checkout RTM, add evidence, route for approval. RTM must be EFFECTIVE before Phase 7 |
| 9.7 | Merge and Submodule Update | Verify RS/RTM EFFECTIVE, create PR, merge (no squash), verify commit reachability, update submodule |
| 9.8 | Documentation | Update project documentation |

#### Execution Content (Sections 10-12) -- Editable during execution

| # | Heading | Content |
|---|---------|---------|
| 10 | **Execution** | EI table + Execution Comments |
| 11 | **Execution Summary** | Overall outcome summary, completed after all EIs |
| 12 | **References** | Related documents (may be updated during execution) |

#### Execution Item (EI) Table Columns

| Column | Static/Editable | Description |
|--------|----------------|-------------|
| EI | Static | Execution item identifier (EI-1, EI-2, ...) |
| Task Description | Static | What to do (from Implementation Plan) |
| VR | Design: "Yes"/blank; Execution: VR ID | Whether integration verification required; replaced with VR document ID during execution |
| Execution Summary | Editable | Narrative of what was done, evidence, observations |
| Task Outcome | Editable | Pass or Fail |
| Performed By - Date | Editable | Signature |

#### Execution Comments Table

| Column | Description |
|--------|-------------|
| Comment | Observation, decision, or issue |
| Performed By - Date | Signature |

### Placeholder Convention

| Syntax | Meaning | When to Replace |
|--------|---------|-----------------|
| `{{DOUBLE_CURLY}}` | Author-time placeholder | Before routing for pre-review (sections 1-9) |
| `[SQUARE_BRACKETS]` | Execution-time placeholder | During execution (sections 10-12) |

After authoring: no `{{...}}` should remain. All `[...]` should remain until execution.

### Static vs Editable

| Sections | Phase | Editability |
|----------|-------|-------------|
| 1-9 | Pre-approval content | **Locked** after pre-approval |
| 10-12 | Execution content | **Editable** during execution |
| 12 (References) | Hybrid | May be updated to add references discovered during execution |

---

## CLI Creation

### Command

```bash
qms --user claude create CR --title "Description of Change"
```

### Flags

| Flag | Required | Description |
|------|----------|-------------|
| `type` | Yes (positional) | Must be `CR` |
| `--title` | Yes | Document title. Defaults to `"CR - [Title]"` if omitted |
| `--parent` | No | Not applicable for standalone CRs |
| `--name` | No | Not applicable |

### What Happens on Create

1. **ID assignment:** `get_next_number("CR")` scans `QMS/CR/` for directories/files matching `CR-(\d+)`, finds max, returns `max + 1`
2. **Duplicate check:** Verifies neither draft nor effective path exists
3. **Directory creation:** Creates `QMS/CR/CR-NNN/` (folder-per-doc)
4. **Template loading:** Loads `QMS/TEMPLATE/TEMPLATE-CR.md`, extracts example frontmatter and body, strips template notice
5. **Placeholder substitution:** `{{TITLE}}` -> actual title, `CR-XXX` -> assigned ID
6. **Draft creation:** Writes to `QMS/CR/CR-NNN/CR-NNN-draft.md`
7. **Metadata creation:** `.meta/CR/CR-NNN.json` with `executable: true`, `execution_phase: "pre_release"`
8. **Audit logging:** `CREATE` event to `.audit/CR/CR-NNN.jsonl`
9. **Workspace copy:** `.claude/users/{user}/workspace/CR-NNN.md`

---

## CLI Enforcement by Operation

### Checkout (`checkout.py`)

| Check | Detail |
|-------|--------|
| Permission | `initiator` group required |
| Terminal state guard | CLOSED and RETIRED cannot be checked out |
| Auto-withdraw | If in IN_PRE_REVIEW, IN_PRE_APPROVAL, IN_POST_REVIEW, or IN_POST_APPROVAL, owner checkout implicitly withdraws |
| PRE_APPROVED checkout | **Status-changing transition** (REQ-WF-016): PRE_APPROVED -> DRAFT. This is a scope revision -- clears workflow tracking |
| POST_REVIEWED checkout | **Status-changing transition** (REQ-WF-017): POST_REVIEWED -> IN_EXECUTION. Continues execution |
| IN_EXECUTION checkout | Increments minor version: `{major}.{minor+1}` (REQ-WF-021). Current version remains in QMS; new version created in workspace |
| Meta update | `checked_out: true`, `responsible_user`, `checked_out_date` |

### Checkin (`checkin.py`)

| Check | Detail |
|-------|--------|
| Permission | `initiator` group, owner-only |
| IN_EXECUTION archival | Archives previous version before writing new one (REQ-WF-021). Copies current draft to `.archive/CR/CR-NNN/CR-NNN-v{prev_version}.md` |
| PRE_REVIEWED revert | Checkin from PRE_REVIEWED reverts to DRAFT |
| Meta update | `checked_out: false`, preserves `responsible_user` and `execution_phase` |

### Route (`route.py`)

| Check | Detail |
|-------|--------|
| Permission | `initiator` group, owner-only |
| Auto-checkin | If checked out, performs implicit checkin (with IN_EXECUTION archival if applicable) |
| `--review` from DRAFT (pre_release) | DRAFT -> IN_PRE_REVIEW |
| `--review` from DRAFT (post_release) | DRAFT -> IN_POST_REVIEW |
| `--review` from IN_EXECUTION | IN_EXECUTION -> IN_POST_REVIEW |
| `--approval` from PRE_REVIEWED | PRE_REVIEWED -> IN_PRE_APPROVAL |
| `--approval` from POST_REVIEWED | POST_REVIEWED -> IN_POST_APPROVAL |
| Approval gate | All reviews must be RECOMMEND; at least one quality-group reviewer |
| `--retire` flag | Only valid on `--approval` routing. Requires version >= 1.0. Sets `retiring: true` in meta |

### Review (`review.py`)

| Check | Detail |
|-------|--------|
| Status check | Must be IN_PRE_REVIEW or IN_POST_REVIEW |
| Required flags | `--comment` + (`--recommend` or `--request-updates`) |
| All-complete | IN_PRE_REVIEW -> PRE_REVIEWED, or IN_POST_REVIEW -> POST_REVIEWED |

### Approve (`approve.py`)

| Check | Detail |
|-------|--------|
| Status check | Must be IN_PRE_APPROVAL or IN_POST_APPROVAL |
| Version bump | `{major+1}.0` |
| Archival | Current draft archived |
| IN_PRE_APPROVAL -> PRE_APPROVED | Executable stays as draft; does NOT become EFFECTIVE |
| IN_POST_APPROVAL -> POST_APPROVED | Ready for close |
| Retirement | If `retiring: true`, transitions to RETIRED instead |

### Reject

| Check | Detail |
|-------|--------|
| IN_PRE_APPROVAL -> PRE_REVIEWED | Returns to pre-reviewed for revision |
| IN_POST_APPROVAL -> POST_REVIEWED | Returns to post-reviewed for revision |

### Release (`release.py`)

| Check | Detail |
|-------|--------|
| Permission | `initiator` group, owner-only |
| Status check | Must be PRE_APPROVED |
| Executable check | Must be an executable document |
| Transition | PRE_APPROVED -> IN_EXECUTION |
| Meta update | Sets `execution_phase: "post_release"` |

### Revert

| Check | Detail |
|-------|--------|
| Transition | POST_REVIEWED -> IN_EXECUTION |
| Purpose | Return to execution after post-review if more work needed |

### Close (`close.py`)

| Check | Detail |
|-------|--------|
| Permission | `initiator` group, owner-only |
| Status check | Must be POST_APPROVED |
| Executable check | Must be an executable document |
| Transition | POST_APPROVED -> CLOSED |
| File operations | Draft moved to effective path, draft deleted |
| Meta update | Clears `responsible_user`, `checked_out`, `pending_assignees` |
| Cascade close | Closes any child attachment documents (VR type) |

### Cancel (`cancel.py`)

| Check | Detail |
|-------|--------|
| Version guard | Only version < 1.0 |
| Checkout guard | Must not be checked out |
| `--confirm` required | Safety check |
| For CRs specifically | Also removes the CR directory if empty after deletion |

---

## Lifecycle

### Status Progression (Happy Path)

```
DRAFT -> IN_PRE_REVIEW -> PRE_REVIEWED -> IN_PRE_APPROVAL -> PRE_APPROVED
      -> IN_EXECUTION
      -> IN_POST_REVIEW -> POST_REVIEWED -> IN_POST_APPROVAL -> POST_APPROVED
      -> CLOSED
```

### Full State Diagram

```
                     +-----------+
                     |   DRAFT   |<-----------+------------------+
                     +-----------+            |                  |
                          |                   |                  |
               route --review (pre_release)   | checkout         | checkout from
                          |                   | (auto-withdraw)  | PRE_APPROVED
                          v                   |                  | (scope revision)
                   +---------------+          |                  |
                   | IN_PRE_REVIEW |---------+                  |
                   +---------------+   withdraw                 |
                          |                                      |
                   review (all complete)                         |
                          |                                      |
                          v                                      |
                   +---------------+                             |
                   | PRE_REVIEWED  |<-------+                    |
                   +---------------+        |                    |
                          |                 | reject             |
                   route --approval         |                    |
                          |                 |                    |
                          v                 |                    |
                   +-----------------+      |                    |
                   | IN_PRE_APPROVAL |------+                    |
                   +-----------------+      |                    |
                          |                 | withdraw           |
                          |                 v                    |
                   approve              PRE_REVIEWED             |
                          |                                      |
                          v                                      |
                   +--------------+                              |
                   | PRE_APPROVED |------------------------------+
                   +--------------+     checkout (scope revision)
                          |
                   release
                          |
                          v
                   +--------------+
                   | IN_EXECUTION |<--------+------------------+
                   +--------------+         |                  |
                          |                 | revert           | checkout from
               route --review (post)        |                  | POST_REVIEWED
                          |                 |                  |
                          v                 |                  |
                   +----------------+       |                  |
                   | IN_POST_REVIEW |-------+                  |
                   +----------------+  withdraw                |
                          |                                    |
                   review (all complete)                       |
                          |                                    |
                          v                                    |
                   +----------------+                          |
                   | POST_REVIEWED  |--------------------------+
                   +----------------+
                          |
                   route --approval
                          |
                          v
                   +------------------+
                   | IN_POST_APPROVAL |------+
                   +------------------+      | reject -> POST_REVIEWED
                          |                  | withdraw -> POST_REVIEWED
                   approve
                          |
                          v
                   +----------------+
                   | POST_APPROVED  |
                   +----------------+
                          |
                   close
                          |
                          v
                   +-----------+
                   |  CLOSED   |
                   +-----------+
```

### Terminal States

| State | How Reached | Recoverable? |
|-------|-------------|--------------|
| CLOSED | `close` from POST_APPROVED | No (but ADD documents can be created against CLOSED parents) |
| RETIRED | `--retire` on approval routing | No |

### Withdraw Transitions

| From | To |
|------|----|
| IN_PRE_REVIEW | DRAFT |
| IN_PRE_APPROVAL | PRE_REVIEWED |
| IN_POST_REVIEW | IN_EXECUTION |
| IN_POST_APPROVAL | POST_REVIEWED |

### Version Numbering

| Event | Version Change | Example |
|-------|---------------|---------|
| Create | `0.1` | Initial draft |
| Checkout from IN_EXECUTION | `{major}.{minor+1}` | `1.0` -> `1.1`, `1.1` -> `1.2` |
| Pre-approval | `{major+1}.0` | `0.1` -> `1.0` |
| Post-approval | `{major+1}.0` | `1.2` -> `2.0` |

### Execution Phase Tracking

The `execution_phase` field in `.meta` determines which workflow path routing uses:

| Phase | Value | Set When |
|-------|-------|----------|
| Pre-release | `"pre_release"` | On create (initial value) |
| Post-release | `"post_release"` | On release (PRE_APPROVED -> IN_EXECUTION) |

This field is **never reset** by checkin or checkout. Once a document enters post_release, it stays post_release. This ensures routing from DRAFT (after a scope revision checkout from PRE_APPROVED) goes to IN_POST_REVIEW if the document has already been released, but goes to IN_PRE_REVIEW if it has not.

**Exception:** Checkout from PRE_APPROVED resets status to DRAFT but does NOT change execution_phase. However, since PRE_APPROVED is a pre_release status and the checkout hasn't happened after release, the phase stays `pre_release`.

---

## Parent/Child Relationships

### CRs as Parents

CRs can be parents of these child document types:

| Child Type | ID Format | Parent Status Required | Relationship |
|------------|-----------|----------------------|--------------|
| [VAR](VAR.md) | `CR-NNN-VAR-NNN` | Any (no status check on VAR creation) | Variance from CR plan |
| [TP](TP.md) | `CR-NNN-TP-NNN` | Any (no status check) | Test Protocol child of CR |
| [VR](VR.md) | `CR-NNN-VR-NNN` | IN_EXECUTION | Verification Record (attachment) |
| [ADD](ADD.md) | `CR-NNN-ADD-NNN` | CLOSED | Addendum to closed CR |

### CRs as Children

CRs are never children of other documents in the CLI hierarchy. However, CRs can reference parent investigations or CAPAs in their Section 2.1 Context field.

---

## Naming Convention

| Component | Format | Example |
|-----------|--------|---------|
| Prefix | `CR` | -- |
| Number | 3-digit zero-padded | `001`, `091` |
| Full ID | `CR-NNN` | `CR-001`, `CR-091` |
| Draft filename | `CR-NNN-draft.md` | `CR-091-draft.md` |
| Effective filename | `CR-NNN.md` | `CR-091.md` |
| Storage path | `QMS/CR/CR-NNN/` | Folder-per-doc |
| Meta path | `QMS/.meta/CR/CR-NNN.json` | |
| Audit path | `QMS/.audit/CR/CR-NNN.jsonl` | |
| Archive path | `QMS/.archive/CR/CR-NNN/CR-NNN-v{version}.md` | |

Child documents are stored in the parent CR's folder:
- `QMS/CR/CR-091/CR-091-VAR-001-draft.md`
- `QMS/CR/CR-091/CR-091-VR-001.md`
- `QMS/CR/CR-091/CR-091-TP-001-draft.md`

---

## Configuration

From `qms_config.py`:

```python
"CR": {"path": "CR", "executable": True, "prefix": "CR", "folder_per_doc": True}
```

| Key | Value | Meaning |
|-----|-------|---------|
| `path` | `"CR"` | Stored under `QMS/CR/` |
| `executable` | `True` | Executable workflow (pre/post approval, execution phase) |
| `prefix` | `"CR"` | ID prefix for numbering |
| `folder_per_doc` | `True` | Each CR gets its own directory: `QMS/CR/CR-NNN/` |

---

## Initial Metadata

Created by `create_initial_meta()`:

```json
{
  "doc_id": "CR-091",
  "doc_type": "CR",
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

## Code CR vs Document-Only CR

The template provides conditional sections for code CRs:

| Sections | Include When | Delete When |
|----------|-------------|-------------|
| 7.4 Development Controls | CR modifies controlled code | Document-only CR |
| 7.5 Qualified State Continuity | CR modifies controlled code | Document-only CR |
| 9.1 Test Environment Setup | Code CR | Document-only CR |
| 9.2 Requirements (RS Update) | Code CR adding/modifying requirements | No requirement changes |
| 9.4 Qualification | Code CR | Document-only CR |
| 9.5 Integration Verification | Code CR | Document-only CR |
| 9.6 RTM Update and Approval | Code CR with requirements | No requirement changes |
| 9.7 Merge and Submodule Update | Code CR | Document-only CR |

### Template CR Pattern

When a CR modifies QMS templates, changes must propagate to both locations:
- `QMS/TEMPLATE/` -- active QMS instance (document control)
- `qms-cli/seed/templates/` -- bootstrap templates (SDLC)

The implementation plan must include an alignment verification EI.

### Code CR Merge Rules

- [RS](RS.md) and [RTM](RTM.md) must be EFFECTIVE before merging to main
- Merge type: regular merge commit (`--no-ff`). Squash merges are prohibited
- The qualified commit is the execution branch commit verified by CI (not the merge commit)
- RTM must reference the execution branch commit hash

---

## See Also

- [Change Control](../04-Change-Control.md) -- CR content requirements, review team, approval gate
- [Execution](../06-Execution.md) -- Executable block structure, EI tables, evidence requirements
- [Code Governance](../09-Code-Governance.md) -- Execution branches, merge gate, qualified commits
- [Child Documents](../07-Child-Documents.md) -- VAR, ER, ADD, VR lifecycle and decision guide
- [QMS Glossary](../QMS-Glossary.md) -- Term definitions
