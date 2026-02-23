# 1. Overview

## What Is the QMS?

The Quality Management System (QMS) is a GMP-inspired document control and workflow engine that governs how code gets written, reviewed, approved, and deployed. It is implemented as a CLI tool (`qms-cli`) backed by flat-file storage (Markdown documents, JSON metadata, JSONL audit trails).

Every meaningful change -- whether to application code, to a procedure, or to the QMS itself -- flows through a controlled document with defined review, approval, and execution stages. Nothing ships without a paper trail.

## Why GMP?

This is not a pharmaceutical company. The QMS exists for three reasons:

1. **AI agent orchestration.** The primary developers are AI agents (Claude as orchestrator, specialized Technical Units for domain review, a Quality agent for approval). Agents need explicit, machine-readable workflows with clear stage gates. Informal processes ("just review it") break down when the participants are LLMs that lose context between sessions. See [Agent Orchestration](11-Agent-Orchestration.md) for the full agent model.

2. **Traceable provenance.** Every decision, review comment, and approval is recorded in an append-only audit trail. When something goes wrong six months from now, the audit trail answers "who approved this, what did they review, and what was the rationale?"

3. **Recursive self-improvement.** The QMS governs its own evolution. When the process itself fails, the same [Investigation and CAPA](05-Deviation-Management.md) mechanisms that handle code defects are used to diagnose and fix the process. This creates a system that learns from its own mistakes.

## The Two-Layer Structure

The QMS operates on two governance layers simultaneously:

### Layer 1: Code Governance

Controls how application code gets developed.

| Mechanism | Purpose |
|-----------|---------|
| [Change Records (CRs)](04-Change-Control.md) | Authorize specific code modifications |
| Technical Unit review | Domain experts verify correctness |
| Quality approval | Independent sign-off before merge |
| [Merge gates](09-Code-Governance.md) | CI-verified commit + approved documents required |

A developer (human or AI) cannot merge code to `main` without an approved CR, an effective [Requirements Specification](types/RS.md), and a verified [Requirements Traceability Matrix](types/RTM.md).

### Layer 2: Process Governance

Controls how the QMS itself evolves.

| Mechanism | Purpose |
|-----------|---------|
| [SOPs](types/SOP.md) as controlled documents | Procedures are versioned and approved like code |
| [Investigations (INVs)](05-Deviation-Management.md) | Analyze process failures with root cause analysis |
| CAPAs | Corrective/Preventive Actions fix the procedures |
| CRs against the QMS | Same change control for process changes |

When a procedure fails -- an agent skips a step, a review misses a defect, a workflow produces friction -- the failure is investigated using the same document control mechanisms. The resulting CAPA may modify the SOP that governs the workflow, creating a feedback loop.

## The Recursive Governance Loop

```
    Code Change ──► CR ──► Review ──► Approval ──► Execution ──► Close
                                                        │
                                                  [Deviation?]
                                                        │
                                                        ▼
                                                  Investigation
                                                        │
                                                    Root Cause
                                                        │
                                                      CAPA
                                                        │
                                              ┌─────────┴─────────┐
                                              │                   │
                                         Code Fix           Process Fix
                                         (new CR)           (SOP revision)
                                              │                   │
                                              └─────────┬─────────┘
                                                        │
                                              Uses same workflow ──►
```

The key insight: the system that discovers a process failure and the system that fixes it are the same system. The QMS is not a static rulebook imposed from above -- it is a living framework that evolves empirically based on what works and what does not.

Every process failure becomes an input to process improvement. Over the life of the project, this produces:
- Working, tested code (the obvious output)
- A reusable methodology for AI-governed development
- A traceable provenance of how that methodology emerged

## Design Philosophy

### Documents as the Unit of Work

All work is authorized by, tracked through, and evidenced in controlled documents. There is no "just do it" path. This sounds heavy, but the documents are lightweight Markdown files with YAML frontmatter, not Word documents with signature blocks. See [Document Control](02-Document-Control.md) for the full metadata architecture.

### Separation of Concerns

The QMS enforces role separation even when all roles are played by AI agents:

| Role | Responsibility | Cannot |
|------|---------------|--------|
| **Initiator** (Claude) | Create, edit, route documents | Approve own work |
| **Quality** (QA agent) | Assign reviewers, approve/reject | Create documents |
| **Technical Units** (TU agents) | Domain-specific review | Approve outside domain |

This prevents the failure mode where a single agent writes code, reviews it, and approves it. Independence is structural, not aspirational.

### Append-Only Audit

Every lifecycle event is recorded in `.audit/` JSONL files. These are append-only -- events are never modified or deleted. The audit trail is the ground truth for what happened, when, and by whom. See the [CLI Reference](12-CLI-Reference.md) for the `history` and `comments` commands that read these trails.

### The CLI as Gatekeeper

All QMS operations flow through the `qms-cli` tool. Direct manipulation of metadata, audit trails, or controlled documents is prohibited. The CLI enforces state machine transitions, permission checks, and audit logging.

## Project Structure

```
my-project/                          # QMS project root
├── qms-cli/                         # CLI tool (git submodule)
├── qms.config.json                  # Project root marker
├── CLAUDE.md                        # Orchestrator instructions
├── QMS/                             # Controlled documents
│   ├── CR/                          # Change Records
│   ├── INV/                         # Investigations
│   ├── TEMPLATE/                    # Document templates
│   ├── .meta/                       # Document metadata (CLI-managed)
│   ├── .audit/                      # Audit trails (CLI-managed)
│   └── .archive/                    # Version archive (CLI-managed)
├── QMS-Docs/                        # Educational documentation
├── .claude/
│   ├── users/                       # Per-user workspaces and inboxes
│   ├── agents/                      # Agent definitions
│   └── hooks/                       # Hook scripts
└── my-app/                          # Example: a governed codebase
```

See [02-Document-Control.md](02-Document-Control.md) for the full directory structure and metadata architecture.

## Further Reading

- [02-Document-Control.md](02-Document-Control.md) -- Document types, naming, versioning, metadata
- [03-Workflows.md](03-Workflows.md) -- Lifecycle state machines and transitions
- [04-Change-Control.md](04-Change-Control.md) -- Change Records in detail
- [05-Deviation-Management.md](05-Deviation-Management.md) -- Investigations and CAPAs
- [09-Code-Governance.md](09-Code-Governance.md) -- Execution branches, merge gate, qualified commits
- [11-Agent-Orchestration.md](11-Agent-Orchestration.md) -- Agent roles and review independence
- [QMS-Glossary.md](QMS-Glossary.md) -- Term definitions
- [QMS-Policy.md](QMS-Policy.md) -- Policy decisions and judgment criteria
