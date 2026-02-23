# Document Type: SOP (Standard Operating Procedure)

## Overview

SOPs are **non-executable** documents. They define procedures but do not authorize implementation activities. SOPs become EFFECTIVE after approval and remain in force until superseded by a new revision or retired. See [Document Control](../02-Document-Control.md) for the document category definitions and [Workflows](../03-Workflows.md) for the non-executable lifecycle.

---

## Template Structure

Source: `QMS/TEMPLATE/TEMPLATE-SOP.md`

### Frontmatter

```yaml
---
title: '{{TITLE}}'
revision_summary: 'Initial creation'
---
```

| Field | Description | Managed By |
|-------|-------------|------------|
| `title` | Document title | Author (in frontmatter) |
| `revision_summary` | Description of changes in this revision | Author (in frontmatter) |

All other metadata (version, status, responsible_user, dates) lives in `.meta/SOP/{SOP-NNN}.json` sidecar files, managed exclusively by the CLI.

### Sections

| # | Heading | Content |
|---|---------|---------|
| 1 | **Purpose** | Why this procedure exists; what problem it solves |
| 2 | **Scope** | What it covers, who is governed. Includes bullet list and explicit **Out of Scope** sub-list |
| 3 | **Definitions** | Table: Term / Definition |
| 4+ | **(Content sections)** | The actual procedure. Section titles and count are author-defined. Numbered sequentially from 4 |
| N | **References** | Table: Document / Relationship. Last section, numbered to match |

### Placeholder Convention

SOPs use only one placeholder type:

| Syntax | Meaning | When to Replace |
|--------|---------|-----------------|
| `{{DOUBLE_CURLY}}` | Author-time placeholder | Before routing for review |

After drafting, no `{{...}}` placeholders should remain.

### Static vs Editable

SOPs are non-executable -- **all sections are static** once approved. There is no execution phase. To modify an effective SOP, check it out (creating a new draft revision) and go through the full review/approval cycle again.

---

## CLI Creation

### Command

```bash
qms --user claude create SOP --title "Document Title Here"
```

### Flags

| Flag | Required | Description |
|------|----------|-------------|
| `type` | Yes (positional) | Must be `SOP` |
| `--title` | Yes | Document title. Defaults to `"SOP - [Title]"` if omitted |
| `--parent` | No | Not applicable for SOPs |
| `--name` | No | Not applicable for SOPs |

### What Happens on Create

1. **ID assignment:** `get_next_number("SOP")` scans `QMS/SOP/` for files/directories matching `SOP-(\d+)`, finds the max, returns `max + 1`
2. **Duplicate check:** Verifies neither `SOP-NNN-draft.md` nor `SOP-NNN.md` exists
3. **Template loading:** Loads `QMS/TEMPLATE/TEMPLATE-SOP.md`, extracts the example frontmatter and body. Strips the `TEMPLATE DOCUMENT NOTICE` comment block (preserves the `TEMPLATE USAGE GUIDE` comment)
4. **Placeholder substitution:** Replaces `{{TITLE}}` with actual title and `SOP-XXX` with the assigned ID
5. **Draft creation:** Writes to `QMS/SOP/SOP-NNN-draft.md` with minimal frontmatter (title + revision_summary only)
6. **Metadata creation:** Creates `.meta/SOP/SOP-NNN.json` with initial state (see below)
7. **Audit logging:** Logs `CREATE` event to `.audit/SOP/SOP-NNN.jsonl`
8. **Workspace copy:** Copies draft to `.claude/users/{user}/workspace/SOP-NNN.md`
9. Document is immediately checked out and ready for editing

---

## CLI Enforcement by Operation

### Checkout (`checkout.py`)

| Check | Detail |
|-------|--------|
| Permission | `initiator` group required |
| Identity | User must exist in `VALID_USERS` |
| Terminal state guard | CLOSED and RETIRED cannot be checked out |
| Already checked out (same user) | Error: "You already have it checked out" |
| Already checked out (different user) | Error with owner name |
| Auto-withdraw | If document is in IN_REVIEW or IN_APPROVAL, checkout by the owner implicitly withdraws. Clears assignees, deletes inbox tasks |
| Effective checkout | Creates draft version `{major}.1` from the effective copy. Effective version stays in force (REQ-WF-020) |
| Meta update | Sets `checked_out: true`, `responsible_user`, `checked_out_date` |

### Checkin (`checkin.py`)

| Check | Detail |
|-------|--------|
| Permission | `initiator` group, owner-only |
| Ownership | Only the `responsible_user` in `.meta` can check in |
| Workspace required | Document must exist in user's workspace |
| Reviewed state revert | If status is REVIEWED, checkin reverts to DRAFT (new content needs re-review) |
| Meta update | `checked_out: false`, clears `checked_out_date`. Preserves `responsible_user` |

### Route (`route.py`)

| Check | Detail |
|-------|--------|
| Permission | `initiator` group, owner-only (REQ-SEC-003) |
| Auto-checkin | If checked out when routing, performs implicit checkin (owner must match) |
| Flags | Must specify `--review` or `--approval` |
| Approval gate | Before `--approval`, verifies: (1) all reviews are RECOMMEND, (2) at least one quality-group reviewer |
| Assignee default | If no `--assign`, defaults to `["qa"]` |
| Task creation | Creates task files in assignees' inboxes |
| Audit | Logs `STATUS_CHANGE` and `ROUTE_REVIEW`/`ROUTE_APPROVAL` events |

### Review (`review.py`)

| Check | Detail |
|-------|--------|
| Permission | `initiator`, `quality`, or `reviewer` group; must be in `pending_assignees` |
| Required flags | `--comment` (always), plus `--recommend` or `--request-updates` |
| Status check | Must be IN_REVIEW |
| All-complete | When last reviewer completes, transitions to REVIEWED |
| Inbox cleanup | Removes task file from reviewer's inbox |

### Approve (`approve.py`)

| Check | Detail |
|-------|--------|
| Permission | `quality` or `reviewer` group; must be in `pending_assignees` |
| Status check | Must be IN_APPROVAL |
| Version bump | Next major: `{major+1}.0` |
| Archival | Current draft archived to `.archive/SOP/SOP-NNN-v{old_version}.md` |
| APPROVED -> EFFECTIVE | Automatic. Draft moved to effective path, draft deleted, ownership cleared |
| Previous effective | If revising, previous effective version archived before replacement (REQ-WF-020) |
| Retirement | If `--retire` was set during routing, transitions to RETIRED instead. Both draft and effective deleted; document archived |

### Reject (`approve.py` -- reject command)

| Check | Detail |
|-------|--------|
| Permission | `quality` or `reviewer` group; must be in `pending_assignees` |
| Status check | Must be IN_APPROVAL |
| Transition | IN_APPROVAL -> REVIEWED |
| Comment | Required |

### Cancel (`cancel.py`)

| Check | Detail |
|-------|--------|
| Permission | `initiator` group |
| Version guard | Only version < 1.0 (never effective) |
| Checkout guard | Must not be checked out |
| Confirmation | Requires `--confirm` flag |
| Effect | Permanently deletes document file, `.meta`, `.audit`, workspace copies, inbox tasks |

### Fix (`fix.py`)

| Check | Detail |
|-------|--------|
| Permission | `administrator` group only |
| Status guard | EFFECTIVE or CLOSED only |
| Operations | Clears stale `checked_out` flags, syncs body version headers, updates TBD effective dates |

---

## Lifecycle

### Status Progression (Happy Path)

```
DRAFT -> IN_REVIEW -> REVIEWED -> IN_APPROVAL -> APPROVED -> EFFECTIVE
```

### Full State Diagram

```
                    +-----------+
                    |   DRAFT   |<-----------+
                    +-----------+            |
                         |                   |
                   route --review            | checkout (auto-withdraw)
                         |                   | checkin from REVIEWED
                         v                   |
                   +-----------+             |
                   | IN_REVIEW |-------------+
                   +-----------+        withdraw
                         |
                   review (all complete)
                         |
                         v
                   +-----------+
                   | REVIEWED  |<-------+
                   +-----------+        |
                         |              | reject
                   route --approval     |
                         |              |
                         v              |
                   +-------------+      |
                   | IN_APPROVAL |------+
                   +-------------+      |
                         |              | withdraw -> REVIEWED
                         |
                   approve (all complete)
                         |
                         v
                   +-----------+
                   |  APPROVED |
                   +-----------+
                         |
                   (automatic transition)
                         |
                         v
                   +-----------+
                   | EFFECTIVE |
                   +-----------+
                         |
                   checkout (creates {major}.1 draft)
                         |
                         v
                     DRAFT (new revision cycle)
```

### Terminal States

| State | How Reached | Recoverable? |
|-------|-------------|--------------|
| EFFECTIVE | Automatic after APPROVED | Yes -- checkout creates new revision |
| RETIRED | `--retire` flag on approval routing | No -- cannot be checked out |

### Withdraw Transitions

| From | To |
|------|----|
| IN_REVIEW | DRAFT |
| IN_APPROVAL | REVIEWED |

### Version Numbering

| Event | Version Change | Example |
|-------|---------------|---------|
| Create | `0.1` | Initial draft |
| Checkin (while DRAFT) | No change | Stays `0.1` |
| Checkout from EFFECTIVE | `{major}.1` | `1.0` -> `1.1` |
| Approval | `{major+1}.0` | `0.1` -> `1.0`, `1.1` -> `2.0` |

---

## Parent/Child Relationships

SOPs have **no parent/child relationships**. They are top-level standalone documents.

TEMPLATE documents can be parents of SOPs in a conceptual sense (SOPs are created from `TEMPLATE-SOP`), but there is no formal QMS linkage enforced by the CLI.

---

## Naming Convention

| Component | Format | Example |
|-----------|--------|---------|
| Prefix | `SOP` | -- |
| Number | 3-digit zero-padded | `001`, `006` |
| Full ID | `SOP-NNN` | `SOP-001`, `SOP-006` |
| Draft filename | `SOP-NNN-draft.md` | `SOP-001-draft.md` |
| Effective filename | `SOP-NNN.md` | `SOP-001.md` |
| Storage path | `QMS/SOP/` | Flat -- no folder-per-doc |
| Meta path | `QMS/.meta/SOP/SOP-NNN.json` | |
| Audit path | `QMS/.audit/SOP/SOP-NNN.jsonl` | |
| Archive path | `QMS/.archive/SOP/SOP-NNN-v{version}.md` | `QMS/.archive/SOP/SOP-001-v0.1.md` |

---

## Configuration

From `qms_config.py`:

```python
"SOP": {"path": "SOP", "executable": False, "prefix": "SOP"}
```

| Key | Value | Meaning |
|-----|-------|---------|
| `path` | `"SOP"` | Stored under `QMS/SOP/` |
| `executable` | `False` | Non-executable workflow (no execution phase) |
| `prefix` | `"SOP"` | ID prefix for numbering |
| `folder_per_doc` | (absent) | Flat file storage, not per-document folders |

---

## Initial Metadata

Created by `create_initial_meta()` on document creation:

```json
{
  "doc_id": "SOP-001",
  "doc_type": "SOP",
  "version": "0.1",
  "status": "DRAFT",
  "executable": false,
  "execution_phase": null,
  "responsible_user": "claude",
  "checked_out": true,
  "checked_out_date": "2026-02-22",
  "effective_version": null,
  "pending_assignees": []
}
```

---

## See Also

- [Workflows](../03-Workflows.md) -- Non-executable document lifecycle state machine
- [Agent Orchestration](../11-Agent-Orchestration.md) -- Who can create and approve SOPs
- [CLI Reference](../12-CLI-Reference.md) -- Full command reference and permission matrix
- [TEMPLATE Reference](TEMPLATE.md) -- How SOP templates are governed
- [QMS Glossary](../QMS-Glossary.md) -- Term definitions
