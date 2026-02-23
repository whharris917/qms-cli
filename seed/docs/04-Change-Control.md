# 4. Change Control

Change Records (CRs) are the primary mechanism for authorizing changes to the product or the QMS itself. Every modification -- code, configuration, procedure -- flows through a CR. This document covers how CRs are structured, reviewed, executed, and closed.

> **Related docs:** [03-Workflows.md](03-Workflows.md) for the state machine mechanics, [06-Execution.md](06-Execution.md) for the executable block details, [07-Child-Documents.md](07-Child-Documents.md) for Test Protocols, VARs, and other children.

---

## CR Lifecycle at a Glance

```
Create (DRAFT) --> Author content --> Check in --> Route for Review
    --> Review team evaluates --> Route for Approval --> QA approves
    --> PRE_APPROVED --> Release --> IN_EXECUTION --> Execute EIs
    --> Route for Post-Review --> Post-Approval --> CLOSED
```

CRs are **executable documents**, meaning they pass through the full execution lifecycle after initial approval. See [06-Execution.md](06-Execution.md) for execution mechanics.

---

## CR Content Requirements

A CR contains 12 sections. All must be populated before routing for review.

| # | Section | Purpose | When Written |
|---|---------|---------|--------------|
| 1 | **Purpose** | One-sentence statement of what this CR accomplishes | Authoring |
| 2 | **Scope** | What systems, documents, or components are affected | Authoring |
| 3 | **Current State** | Description of the system as it exists before this change | Authoring |
| 4 | **Proposed State** | Description of the system as it will exist after this change | Authoring |
| 5 | **Change Description** | Technical details of what will be modified | Authoring |
| 6 | **Justification** | Why this change is needed -- the business or technical rationale | Authoring |
| 7 | **Impact Assessment** | What other systems, documents, or workflows are affected; risk analysis | Authoring |
| 8 | **Testing Summary** | How the change will be verified; references to Test Protocols if applicable | Authoring |
| 9 | **Implementation Plan** | Ordered steps for carrying out the change | Authoring |
| 10 | **Execution** | The executable block -- EI table where work is recorded | Execution phase |
| 11 | **Execution Summary** | Post-execution narrative: what was done, deviations encountered, final state | Post-execution |
| 12 | **References** | Links to parent/child documents, related CRs, external resources | Authoring + updated during execution |

### Section Guidance

**Purpose vs. Justification:** Purpose states *what*; Justification states *why*. "Add a dropdown widget to the toolbar" is purpose. "Users currently cannot switch tools without keyboard shortcuts, reducing accessibility" is justification.

**Current State vs. Proposed State:** These form a diff pair. A reviewer should be able to compare them and understand exactly what changes. Be specific -- reference file paths, function names, or configuration values.

**Impact Assessment:** Think broadly. Does this change affect:
- Other code modules that import the modified files?
- Existing [SOPs](types/SOP.md) or procedures?
- The [RTM](types/RTM.md) or [Requirements Specification](types/RS.md)?
- Other open CRs that might conflict?

**Implementation Plan vs. Execution:** The Implementation Plan is the *approved plan* written before review. The Execution section is the *actual record* of what happened during implementation. They may diverge -- that is what [VARs](07-Child-Documents.md) are for.

---

## The `revision_summary` Field

Every CR carries a `revision_summary` field in its frontmatter. This field provides document-level traceability:

```yaml
---
title: "Add particle emitter configuration panel"
revision_summary: "Initial draft"
---
```

The `revision_summary` is updated at each check-in to describe what changed in that revision. It serves as a human-readable changelog for the document itself (distinct from the change the document *authorizes*).

**Examples:**
- `"Initial draft"` -- first version
- `"Addressed reviewer feedback: clarified impact on simulation module"` -- after review round
- `"Updated execution summary with final commit hashes"` -- post-execution

---

## Review Team Composition

Every CR requires a review team before it can be approved. The team is assembled by QA.

### Roles

| Role | Who | Responsibility |
|------|-----|----------------|
| **QA** | Quality Assurance representative | Mandatory on every CR. Assigns TUs, verifies process compliance, approves. |
| **TU** | Technical Unit (domain expert) | Assigned by QA based on the CR's scope. Reviews technical correctness. |

### Assignment Process

1. The initiator creates the CR and routes it for review.
2. QA receives the review routing notification.
3. QA evaluates the CR scope and assigns appropriate TUs (e.g., `tu_ui` for UI changes, `tu_scene` for scene logic).
4. All assigned reviewers evaluate the CR independently.

### Review Independence

Reviewers derive their evaluation criteria from the SOPs and their domain expertise -- not from the orchestrator's instructions. A TU reviewing a UI change checks against UI architecture principles, not against whatever the CR author says is important. See [11-Agent-Orchestration.md](11-Agent-Orchestration.md) for the full independence model.

### Review Outcomes

Each reviewer submits one of two outcomes:

| Outcome | Meaning | Effect |
|---------|---------|--------|
| **Recommend** | The CR is technically sound and ready for approval | Clears this reviewer's gate |
| **Request-Updates** | The CR has issues that must be addressed | Blocks approval routing (see Approval Gate below) |

### The Approval Gate

If *any* reviewer submits `request-updates`, the CR cannot be routed for approval. The initiator must:

1. Check out the document
2. Address the feedback
3. Check it back in
4. Re-route for review

This cycle repeats until all reviewers recommend. The gate is enforced by the system -- there is no override.

---

## The Execution Phase

Once approved, the CR enters the executable document lifecycle. See [06-Execution.md](06-Execution.md) for full details on:

- The executable block structure
- EI table format
- Evidence requirements
- Pre/post execution commits

### High-Level Execution Flow

1. **PRE_APPROVED** -- CR is approved but execution has not started.
2. **Release** -- The owner releases the CR, transitioning it to IN_EXECUTION.
3. **Execute EIs** -- Each execution item is performed and documented with evidence.
4. **Route for post-review** -- After all EIs are complete, the CR is routed for post-execution review.
5. **POST_REVIEWED** -- Reviewers verify execution matches approved scope.
6. **Approve** -- QA gives final approval.
7. **CLOSED** -- Terminal state. No further modifications possible.

### What Happens During Execution

During the IN_EXECUTION phase, the initiator:

- Works through each EI in the approved plan
- Records actual outcomes, evidence (commit hashes, screenshots, test results), and any deviations
- Creates [child documents](07-Child-Documents.md) as needed:
  - **[Test Protocols (TPs)](types/TP.md)** for structured test execution
  - **[VARs](types/VAR.md)** when execution deviates from the approved plan
  - **[Verification Records (VRs)](types/VR.md)** for structured behavioral verification
- Commits code changes to the execution branch (see [09-Code-Governance.md](09-Code-Governance.md))

---

## Post-Review Gates

After execution, QA and the review team verify the CR before closure. Post-review checks include:

| Check | What QA Verifies |
|-------|-----------------|
| **Scope integrity** | All approved EIs were executed; none were silently dropped |
| **Evidence completeness** | Every EI has documented evidence of completion |
| **Deviation handling** | Any deviations were captured in VARs with proper resolution |
| **Child document status** | All child TPs, VARs, ERs, ADDs are in appropriate terminal or pre-approved states |
| **Code governance** | Execution branch merged, commit hashes recorded |
| **Document consistency** | Execution summary accurately reflects what happened |

If post-review reveals issues, QA can reject the CR back to a reviewed state for correction.

---

## Test Protocols as Children

A CR may optionally include one or more **Test Protocols (TPs)** as child documents. TPs are themselves executable documents with their own lifecycle.

### When to Use a TP

- The CR involves behavioral changes that require structured verification steps
- Testing is complex enough to warrant its own review/approval cycle
- The test procedure needs to be reusable or auditable independently

### TP Lifecycle Relationship

```
CR (parent)
 └── TP-001 (child) -- has its own review, approval, execution, closure
```

- TPs are created with the parent CR's ID (e.g., `CR-045-TP-001`)
- TPs go through their own review and approval cycle
- TP execution generates evidence that feeds back into the parent CR
- The parent CR cannot close until its child TPs reach appropriate states

See [07-Child-Documents.md](07-Child-Documents.md) for TP naming conventions, content requirements, and the scope handoff mechanism.

---

## Quick Reference: CR Workflow Commands

```bash
# Create a CR
qms create CR --title "Add particle emitter panel"

# Check out for editing
qms checkout CR-045

# Check in after editing
qms checkin CR-045

# Route for review
qms route CR-045 --review

# Route for approval (after all reviewers recommend)
qms route CR-045 --approval

# Release for execution (after approval)
qms release CR-045

# Route for post-review (after execution complete)
qms route CR-045 --review

# Route for post-approval
qms route CR-045 --approval

# Close (after post-approval)
qms close CR-045
```

See [12-CLI-Reference.md](12-CLI-Reference.md) for the full command reference.

---

## See Also

- [CR Reference](types/CR.md) -- Detailed CR template structure, CLI enforcement, and lifecycle
- [06-Execution.md](06-Execution.md) -- Executable block structure, EI tables, evidence requirements
- [09-Code-Governance.md](09-Code-Governance.md) -- Execution branches, merge gate, qualified commits
- [10-SDLC.md](10-SDLC.md) -- RS/RTM framework and CR closure prerequisites
- [QMS-Policy.md](QMS-Policy.md) -- Review team assignment policy and judgment criteria

---

## Glossary References

Key terms used in this document: [CR](QMS-Glossary.md), [Review Team](QMS-Glossary.md), [QA](QMS-Glossary.md), [TU](QMS-Glossary.md), [Approval Gate](QMS-Glossary.md), [Executable Document](QMS-Glossary.md), [TP](QMS-Glossary.md), [Frontmatter](QMS-Glossary.md), [Review Independence](QMS-Glossary.md).
