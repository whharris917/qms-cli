# 2. Document Control

This document defines how QMS documents are organized, identified, versioned, and stored. It is the foundational reference for the metadata architecture.

## Document Categories

Every controlled document falls into one of two categories:

| Category | Purpose | Examples |
|----------|---------|----------|
| **Executable** | Authorizes and tracks implementation work | [CR](types/CR.md), [INV](types/INV.md), [TP](types/TP.md), [ER](types/ER.md), [VAR](types/VAR.md), [ADD](types/ADD.md), [VR](types/VR.md) |
| **Non-Executable** | Defines requirements or specifications | [RS](types/RS.md), [RTM](types/RTM.md), [SOP](types/SOP.md) |

The distinction matters because each category follows a different lifecycle state machine. See [03-Workflows.md](03-Workflows.md) for the full state diagrams.

### Executable Documents

Executable documents contain an **executable block** -- a structured section where implementation work is recorded. Each block contains **execution items (EIs)**: discrete tasks with descriptions, outcomes (Pass/Fail), and evidence. See [Execution](06-Execution.md) for the full block structure.

| Type | Full Name | Purpose | Parent |
|------|-----------|---------|--------|
| **CR** | Change Record | Authorizes a code or process change | None |
| **INV** | Investigation | Analyzes a deviation; contains root cause and CAPAs | None |
| **TP** | Test Protocol | Formal test procedures | CR |
| **ER** | Exception Report | Documents test execution failures | TP |
| **VAR** | Variance Report | Resolves execution deviations in non-test documents | CR, INV |
| **ADD** | Addendum Report | Corrects or supplements a CLOSED executable document | Any closed executable |
| **VR** | Verification Record | Pre-approved evidence form for behavioral verification | CR, VAR, ADD |

### Non-Executable Documents

Non-executable documents define what the system should do or how it should be governed. They do not contain executable blocks.

| Type | Full Name | Purpose |
|------|-----------|---------|
| **SOP** | Standard Operating Procedure | Defines a process or policy |
| **RS** | Requirements Specification | Defines what a system shall do |
| **RTM** | Requirements Traceability Matrix | Maps requirements to code and verification evidence |

## Naming Conventions

### Standalone Documents

Format: `{TYPE}-{NNN}`

```
CR-001      # First Change Record
SOP-007     # Seventh SOP
INV-003     # Third Investigation
RS-001      # First Requirements Specification
```

The numeric suffix is zero-padded to three digits and auto-incremented by the CLI.

### Child Documents

Child documents reference their parent using a hyphenated suffix:

Format: `{PARENT_ID}-{CHILD_TYPE}-{NNN}`

```
CR-045-TP-001       # First Test Protocol under CR-045
CR-045-TP-001-ER-001   # First Exception Report under that TP
CR-045-VAR-001      # First Variance Report under CR-045
CR-091-ADD-001      # First Addendum under CR-091
CR-091-ADD-001-VR-001  # Verification Record under that Addendum
```

The nesting follows the parent-child relationship in the document hierarchy. The CLI manages ID assignment automatically.

## Versioning Scheme

All documents use a two-part version number: **N.X**

| Component | Meaning |
|-----------|---------|
| **N** (major) | Increments on each approval. Version `1.0` = first approval. |
| **X** (minor) | Increments on each check-in during draft/revision. Resets to 0 on approval. |

### Version Lifecycle Example

```
0.1  ← Created (first draft)
0.2  ← Checked in after edits
0.3  ← Checked in again
1.0  ← Approved (first effective version)
1.1  ← Checked in for revision
1.2  ← More revision edits
2.0  ← Approved (second effective version)
```

Key rules:
- A document at version `0.X` has **never been approved**
- A document at version `N.0` (where N >= 1) is **currently approved/effective**
- A document at version `N.X` (where X > 0) is **under revision** of an effective document
- The CLI manages version increments automatically on check-in and approval

## Document Statuses

### Non-Executable Document Statuses

| Status | Meaning |
|--------|---------|
| **DRAFT** | Under development, not yet submitted for review |
| **IN_REVIEW** | Submitted for review; reviewers are evaluating |
| **REVIEWED** | All reviewers have completed review |
| **IN_APPROVAL** | Submitted for approval; awaiting approver decision |
| **EFFECTIVE** | Approved and in force |
| **RETIRED** | Permanently archived, no longer in use (terminal) |

### Executable Document Statuses

Executable documents share the base statuses above plus additional states for the execution phase:

| Status | Meaning |
|--------|---------|
| **DRAFT** | Under development |
| **IN_REVIEW** | Submitted for pre-execution review |
| **REVIEWED** | Pre-execution review complete |
| **IN_APPROVAL** | Submitted for pre-execution approval |
| **PRE_APPROVED** | Approved for execution (not yet started) |
| **IN_EXECUTION** | Execution underway; EIs being completed |
| **POST_REVIEW** | Execution complete; submitted for post-execution review |
| **POST_REVIEWED** | Post-execution review complete |
| **POST_APPROVAL** | Submitted for post-execution approval |
| **POST_APPROVED** | Post-execution approved |
| **CLOSED** | Execution complete, all gates passed (terminal) |
| **RETIRED** | Permanently archived (terminal) |

The CLI uses the document's current phase (pre-execution or post-execution) to automatically determine which review/approval stage applies when you route a document. You do not need to specify "post-review" vs "pre-review" -- the CLI infers it.

### Special Case: Verification Records (VR)

VRs skip the entire pre-execution phase. They are born directly in `IN_EXECUTION` because they are pre-approved evidence forms. Their lifecycle begins at execution and proceeds through post-review to closure. See [VR Reference](types/VR.md) and [Interactive Authoring](08-Interactive-Authoring.md) for details.

## Directory Structure

```
QMS/
├── SOP/
│   ├── SOP-001.md                    # Document content
│   ├── SOP-002.md
│   └── ...
├── CR/
│   ├── CR-001.md
│   ├── CR-001-TP-001.md              # Child documents live alongside parents
│   ├── CR-001-VAR-001.md
│   └── ...
├── INV/
│   ├── INV-001.md
│   └── ...
├── RS/
│   ├── RS-001.md
│   └── ...
├── RTM/
│   ├── RTM-001.md
│   └── ...
├── .meta/
│   ├── SOP/
│   │   ├── SOP-001.json              # Sidecar metadata for each document
│   │   └── ...
│   ├── CR/
│   │   ├── CR-001.json
│   │   ├── CR-001-TP-001.json
│   │   └── ...
│   └── ...
├── .audit/
│   ├── SOP/
│   │   ├── SOP-001.jsonl             # Append-only event log
│   │   └── ...
│   ├── CR/
│   │   ├── CR-001.jsonl
│   │   └── ...
│   └── ...
└── .archive/
    ├── SOP/
    │   ├── SOP-001_v1.0.md           # Superseded version snapshot
    │   └── ...
    └── CR/
        └── ...
```

Key points:
- Document content lives in `QMS/{TYPE}/`
- Child documents live in the same directory as their parent type (e.g., `CR-001-VAR-001.md` is in `QMS/CR/`)
- Metadata, audit, and archive directories mirror the type structure

## Three-Tier Metadata Architecture

Document state is tracked across three layers, each with a distinct purpose and access pattern.

### Tier 1: Frontmatter (Author-Maintained)

Minimal YAML header embedded in the document's Markdown file. Contains fields that the author controls:

```yaml
---
title: "Implement Particle Collision Detection"
revision_summary: "Added spatial hashing algorithm"
---
```

The frontmatter is the only part of the metadata that authors edit directly. It travels with the document content.

### Tier 2: Sidecar Metadata (CLI-Managed)

JSON files in `.meta/{TYPE}/` that store workflow state. Managed exclusively by the CLI -- never edited by hand.

```json
{
  "doc_id": "CR-045",
  "doc_type": "CR",
  "status": "IN_EXECUTION",
  "version": "1.0",
  "owner": "claude",
  "created": "2026-01-15T10:30:00Z",
  "checked_out_by": null,
  "reviewers": ["qa", "tu_ui"],
  "children": ["CR-045-TP-001", "CR-045-VAR-001"]
}
```

The sidecar holds everything the CLI needs to enforce state transitions, permission checks, and workflow routing. It is the machine-readable source of truth for "where is this document in its lifecycle?"

### Tier 3: Audit Trail (Append-Only Log)

JSONL files in `.audit/{TYPE}/` that record every lifecycle event. Each line is a timestamped JSON object:

```jsonl
{"event":"CREATE","user":"claude","timestamp":"2026-01-15T10:30:00Z","version":"0.1"}
{"event":"CHECKOUT","user":"claude","timestamp":"2026-01-15T10:31:00Z"}
{"event":"CHECKIN","user":"claude","timestamp":"2026-01-15T11:00:00Z","version":"0.2"}
{"event":"ROUTE_REVIEW","user":"claude","timestamp":"2026-01-15T11:01:00Z"}
{"event":"REVIEW","user":"qa","timestamp":"2026-01-15T11:30:00Z","outcome":"recommend","comment":"Looks good"}
{"event":"ROUTE_APPROVAL","user":"claude","timestamp":"2026-01-15T11:31:00Z"}
{"event":"APPROVE","user":"qa","timestamp":"2026-01-15T12:00:00Z","version":"1.0"}
```

Audit trails are never modified or deleted. They are the forensic record of what happened, when, and by whom. The CLI's `history` command reads these files; the `comments` command extracts review and rejection comments. See [CLI Reference](12-CLI-Reference.md) for full command documentation.

### Why Three Tiers?

| Tier | Who writes | Who reads | Survives document edit? |
|------|-----------|-----------|------------------------|
| Frontmatter | Author | Author, CLI | Yes (embedded in file) |
| Sidecar | CLI only | CLI, agents | Yes (separate file) |
| Audit trail | CLI only | CLI, agents, auditors | Yes (separate file, append-only) |

Separating content from workflow state from audit history means:
- Editing a document cannot corrupt its workflow state
- Workflow transitions cannot alter document content
- Audit history is immutable regardless of what happens to the document

## Workspace and Inbox

### Workspace

Each user has a workspace at `.claude/users/{username}/workspace/`. When a document is checked out, a working copy is placed here. The original document is locked (no other user can check it out).

```
.claude/users/claude/workspace/
└── CR-045.md        # Working copy, editable
```

Check-in copies the workspace version back to `QMS/{TYPE}/` and removes the workspace copy.

### Inbox

Each user has an inbox at `.claude/users/{username}/inbox/`. When a document is routed for review or approval, task files are created in the assigned users' inboxes.

```
.claude/users/qa/inbox/
├── review-CR-045.json    # Review task
└── approve-SOP-002.json  # Approval task
```

Task files are removed when the user completes the review or approval action.

## Further Reading

- [01-Overview.md](01-Overview.md) -- What the QMS is and why it exists
- [03-Workflows.md](03-Workflows.md) -- State machines and lifecycle transitions
- [06-Execution.md](06-Execution.md) -- Executable block structure and evidence
- [07-Child-Documents.md](07-Child-Documents.md) -- ER, VAR, ADD, VR details
- [12-CLI-Reference.md](12-CLI-Reference.md) -- CLI commands for document operations
- [QMS-Glossary.md](QMS-Glossary.md) -- Term definitions
