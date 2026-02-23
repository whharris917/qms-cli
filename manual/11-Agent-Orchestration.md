# 11. Agent Orchestration

The QMS is designed for AI agent development. The primary developers, reviewers, and approvers are all AI agents operating within a structured permission system. This section describes how agents are organized, what they can do, and the boundaries that keep their work independent and trustworthy.

## The Agent Model

Agent orchestration follows a hub-and-spoke pattern:

```
                    ┌─────────┐
                    │  Lead   │  (Human)
                    │ (admin) │
                    └────┬────┘
                         │ directs
                         ▼
                  ┌──────────────┐
                  │ Orchestrator │  (Claude)
                  │ (initiator)  │
                  └──────┬───────┘
                         │ spawns
            ┌────────────┼────────────┐
            ▼            ▼            ▼
        ┌──────┐    ┌────────┐   ┌────────┐
        │  QA  │    │ TU-UI  │   │ TU-SIM │  ...
        │(qual)│    │ (revw) │   │ (revw) │
        └──────┘    └────────┘   └────────┘
```

### Orchestrator

The **orchestrator** (Claude) is the primary agent. It:

- Creates and manages documents through the QMS workflow
- Implements code changes on execution branches
- Spawns subagents when review, approval, or domain expertise is needed
- Coordinates the overall development process

The orchestrator operates as an **Initiator** in the QMS permission system.

### Subagents

**Subagents** are spawned by the orchestrator for specific roles. Each subagent receives a role identity, a task prompt, and limited context. Subagents include:

| Subagent | Role | QMS Group | Primary Function |
|----------|------|-----------|------------------|
| **QA** | Quality Assurance Representative | Quality | Assign reviewers, review documents, approve/reject |
| **TU-UI** | Technical Unit -- UI Domain | Reviewer | Review UI/interaction code changes |
| **TU-SCENE** | Technical Unit -- Scene Domain | Reviewer | Review scene/orchestration code changes |
| **TU-SKETCH** | Technical Unit -- Sketch/Solver Domain | Reviewer | Review CAD/solver code changes |
| **TU-SIM** | Technical Unit -- Simulation Domain | Reviewer | Review physics/simulation code changes |
| **BU** | Business Unit | Reviewer | Review non-technical changes (process, documentation) |

## User Groups and Permissions

The QMS enforces four permission groups. Every agent is assigned to exactly one group. See the [CLI Reference](12-CLI-Reference.md) permission matrix for the full command-to-group mapping.

### Administrator

| Permission | Description |
|------------|-------------|
| All Initiator permissions | Everything below, plus... |
| `fix` | Apply administrative corrections to EFFECTIVE documents |

Administrators are typically the human Lead. This role exists for corrections that do not warrant a full revision cycle.

### Initiator

| Permission | Description |
|------------|-------------|
| `create` | Create new documents of any type |
| `checkout` / `checkin` | Lock documents for editing and release them |
| `route --review` | Submit documents for review |
| `route --approval` | Submit reviewed documents for approval |
| `release` | Transition executable documents from PRE_APPROVED to IN_EXECUTION |
| `close` | Close executable documents after post-approval |
| `cancel` | Cancel never-effective documents |

The orchestrator (Claude) operates at this level.

### Quality

| Permission | Description |
|------------|-------------|
| `assign` | Add reviewers and approvers to a document's review team |
| `review` | Submit review decisions (recommend or request-updates) |
| `approve` | Approve a document, advancing it to the next state |
| `reject` | Reject a document, returning it for revision |

The QA agent is the sole member of this group. QA is a mandatory reviewer and approver on all documents.

### Reviewer

| Permission | Description |
|------------|-------------|
| `review` | Submit review decisions (recommend or request-updates) |
| `approve` | Approve documents assigned for approval |
| `reject` | Reject documents assigned for approval |

Technical Units and Business Units operate at this level. They are assigned to specific documents by QA.

## Communication Boundaries

The integrity of the review process depends on what information the orchestrator provides -- and does not provide -- when spawning subagents.

### What the Orchestrator Provides

When spawning a subagent, the orchestrator provides:

| Context | Example |
|---------|---------|
| **Role identity** | "You are the QA agent" |
| **Task description** | "Review CR-045 for approval" |
| **Document reference** | "The document is CR-045" |
| **System prompt / SOP references** | Which SOPs govern the subagent's role |

### What the Orchestrator Does NOT Provide

| Excluded Context | Reason |
|-----------------|--------|
| **Review criteria** | Reviewers derive criteria from SOPs and domain expertise, not from the orchestrator |
| **Expected outcome** | The orchestrator must not suggest "approve this" or "this looks good" |
| **Justifications for the change** | The document itself contains the rationale; the reviewer reads it independently |
| **Other reviewers' opinions** | Each reviewer forms their own judgment |

### Review Independence

**Review independence** is the principle that reviewers derive their criteria from SOPs and their domain expertise, not from orchestrator instructions. This is a structural safeguard:

- The orchestrator wrote the code and authored the document. It has an inherent bias toward approval.
- If the orchestrator told the reviewer what to look for, the review would only verify what the orchestrator already checked.
- Independent review catches what the author missed.

The orchestrator may provide factual context (e.g., "this CR modifies the solver module") but must not provide evaluative context (e.g., "the changes are straightforward and low-risk").

## Agent Reuse Within Sessions

Spawning a new agent is expensive (15-60 seconds). When the orchestrator needs a subagent multiple times in a session, it should **reuse** the existing agent rather than spawning a new one.

```
# First interaction -- spawns new agent, returns agentId
Task(subagent_type="qa", prompt="Check inbox") -> agentId: abc123

# Subsequent interactions -- resume existing agent (faster, preserves context)
Task(resume="abc123", prompt="Review CR-045")
Task(resume="abc123", prompt="Approve CR-045")
```

**Benefits of reuse:**
- Faster response (no cold start)
- Preserved context from earlier interactions
- Consistent review perspective within a session

## Identity and Integrity

### Agent Identity

Each agent has a fixed QMS identity (lowercase string) that is used for all QMS operations:

| Agent | Identity | Group |
|-------|----------|-------|
| Orchestrator | `claude` | Initiator |
| QA | `qa` | Quality |
| TU-UI | `tu_ui` | Reviewer |
| TU-SCENE | `tu_scene` | Reviewer |
| TU-SKETCH | `tu_sketch` | Reviewer |
| TU-SIM | `tu_sim` | Reviewer |
| BU | `bu` | Reviewer |
| Lead (human) | `lead` | Administrator |

### Integrity Requirements

- Agents must not impersonate other agents or use another agent's identity
- Agents must not directly manipulate QMS metadata, audit trails, or controlled documents (all operations flow through the CLI)
- Agents must not circumvent permission checks by any means
- If an agent discovers a way to bypass the system, it reports the vulnerability rather than exploiting it

## Conflict Resolution and Escalation

### Review Disagreements

When a reviewer requests updates, the orchestrator must address the feedback before re-routing for review. The orchestrator cannot override a reviewer's decision.

### Approval Gate

If any reviewer submitted `request-updates`, the document **cannot** be routed for approval until:

1. The orchestrator addresses the reviewer's concerns
2. The document is re-routed for review
3. All reviewers recommend approval (or the requesting reviewer withdraws their objection)

This is enforced by the CLI -- the system blocks approval routing if any outstanding `request-updates` exists.

### Rejection

If an approver rejects a document, the document returns to a revisable state. The orchestrator must:

1. Read the rejection comment (mandatory on rejection)
2. Address the stated concerns
3. Re-submit through the review/approval cycle

### Escalation to the Lead

Situations that require human escalation:

| Situation | Action |
|-----------|--------|
| Reviewer and orchestrator cannot resolve a disagreement | Escalate to Lead for decision |
| Process ambiguity (SOP does not cover the situation) | Escalate to Lead; may trigger an [Investigation](05-Deviation-Management.md) |
| Permission or access issues | Lead (Administrator) resolves |
| Potential QMS vulnerability discovered | Report to Lead immediately |

## Related Documents

- [01-Overview.md](01-Overview.md) -- QMS design philosophy, role separation
- [03-Workflows.md](03-Workflows.md) -- Document lifecycle state machines
- [04-Change-Control.md](04-Change-Control.md) -- CR review teams and execution
- [12-CLI-Reference.md](12-CLI-Reference.md) -- Commands available to each role
- [QMS-Policy.md](QMS-Policy.md) -- Review team assignment policy and communication boundaries
- [QMS-Glossary.md](QMS-Glossary.md) -- Term definitions
