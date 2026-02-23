# QMS Policy

This document contains the judgment layer of the Quality Management System — the decisions, principles, and criteria that cannot be inferred from the CLI code or document templates. It is one of three authoritative strands:

- **Mechanism:** qms-cli code (how the system works)
- **Structure:** QMS/TEMPLATE/ files (what documents look like)
- **Policy:** This document (when, why, and judgment calls)

If a rule is enforced by the CLI, it belongs in the code, not here. If a document structure is defined by a template, it belongs there, not here. This document exists only for what the other two cannot express.

---

## 1. Governance Philosophy

The QMS is recursive. It controls how application code is developed, and it controls its own evolution through the same mechanisms. When a process fails, an Investigation analyzes the failure and Corrective/Preventive Actions improve the procedures — using the same document control infrastructure that governs the application code.

This recursion is intentional. The system learns from its own mistakes. Every process failure is an input to process improvement. The QMS is not a static framework imposed from above; it is a living system that discovers better orchestration patterns empirically.

---

## 2. Agent Governance

### 2.1 Communication Boundaries

The orchestrator (claude) coordinates all work and is the sole point of contact with the Lead. Subagents (qa, tu_*, bu) communicate only through QMS mechanisms: reviews, comments, and inbox tasks.

Subagents shall not receive full conversation context. Each agent reasons independently based on the document under review and the policies in this document. This constraint is not a limitation — it is the mechanism that produces independent technical judgment.

### 2.2 Review Independence

Reviewers form opinions based solely on the document content and applicable policy. The orchestrator shall not coach, pre-empt, or influence reviewer conclusions. If a reviewer's concerns are addressed, the document is revised and re-submitted — the reviewer decides independently whether the revision is adequate.

### 2.3 Conflict Resolution

When reviewers disagree, the orchestrator does not adjudicate. Disagreements are escalated to the Lead. The orchestrator may provide context but shall not advocate for a particular resolution.

### 2.4 Review Team Assignment

QA assigns Technical Unit reviewers based on the domains affected by a change:

| Domain (project-specific) | Reviewer |
|--------------------------|----------|
| *Defined per project based on codebase domains* | tu, or specialized TUs (e.g., tu_backend, tu_frontend) |
| User experience, product value, usability | bu |

QA exercises judgment in assignment. Not every change requires every reviewer. The goal is relevant expertise, not comprehensive coverage.

---

## 3. When to Investigate

An Investigation (INV) shall be created when:

- A procedure was not followed and the deviation had material consequences
- A procedure was followed correctly but produced the wrong outcome (the procedure itself is defective)
- A systemic pattern is discovered that may affect multiple documents or processes
- Root cause analysis is needed beyond what a VAR can provide

An INV is not required for:

- Isolated execution variances handled adequately by a VAR
- Feature requests or enhancements (use a CR)
- Clarifications to procedures that don't stem from a failure (use a CR to revise the SOP)

**The threshold question:** Did something go wrong in a way that could happen again? If yes, investigate. If it was a one-time mechanical error with an obvious fix, a VAR is sufficient.

---

## 4. When to Create Child Documents

### 4.1 VAR vs ADD

- **VAR:** The parent is still in execution and something has gone wrong. The variance blocks further progress until resolution is understood (Type 1) or at least scoped (Type 2).
- **ADD:** The parent has closed and a gap is discovered afterward. The parent's closure was legitimate at the time; the ADD supplements it without invalidating it.

The distinction is temporal: VAR is prospective (fixing a problem in flight), ADD is retrospective (patching after landing).

### 4.2 VAR Type Selection

- **Type 1** (full closure required): The variance directly threatens the parent's objectives. The parent cannot meaningfully close until the fix is proven end-to-end.
- **Type 2** (pre-approval sufficient): The variance is real but contained. Its impact is understood, the resolution plan is sound, and the parent can close without waiting for the full resolution cycle. Type 2 prevents issues from falling off the radar while keeping the parent from waiting inefficiently.

When in doubt, default to Type 1. A Type 2 that should have been Type 1 can allow a parent to close prematurely.

### 4.3 When VR is Required

A VR is required when an EI involves behavioral verification — confirming that a system behaves correctly under specific conditions. The VR flag in the EI table signals this requirement.

VR is not required for:
- Document-only changes (SOP revisions, template updates)
- Configuration changes verifiable by inspection
- Work that produces no observable system behavior

---

## 5. Evidence Standards

### 5.1 Adequacy

Evidence must be sufficient for a reviewer who was not present during execution to independently conclude that the work was completed as described. The question is not "did the executor believe they finished?" but "can a third party verify it?"

### 5.2 Contemporaneity

Evidence must be recorded during execution, not reconstructed afterward. Commit hashes, test output, and VR responses are captured at the time of execution. Post-hoc evidence reconstruction is a deviation.

### 5.3 Traceability

Each EI's evidence should be traceable to a specific artifact: a commit hash, a document version, a test result, or a VR document ID. Narrative-only evidence ("I did this and it worked") is acceptable only when no artifact is possible.

---

## 6. Scope Integrity

The scope of execution must match the scope of the pre-approved plan. Pre-approval authorizes specific work; execution must deliver that work and only that work.

If execution reveals that additional work is needed:
- Work within the approved scope continues normally.
- Work outside the approved scope must be captured in a child document (VAR for in-flight scope expansion, or a new CR for unrelated discoveries).
- Silently expanding scope during execution defeats the purpose of pre-approval review.

The pre/post split exists so that reviewers can verify the plan (pre) and then verify the execution matched the plan (post). If execution routinely diverges from the plan without formal scope changes, the review process provides no assurance.

---

## 7. Code Governance

### 7.1 Execution Branches

Code changes are developed on branches named after the authorizing CR. This is not merely organizational — it creates a traceable link between the authorization (CR) and the implementation (branch). The main branch receives changes only through reviewed pull requests.

### 7.2 Qualified Commit

A qualified commit is the specific commit on an execution branch where CI passes. It represents the moment when the code is verified. The RTM records this commit hash as the evidence that requirements are satisfied.

The qualified commit must be on the execution branch, not on main. The merge to main happens after qualification and after RS/RTM are both EFFECTIVE. The merge commit must contain the qualified commit in its ancestry — this is verified during post-review.

### 7.3 Merge Gate

The merge gate exists to prevent unqualified code from reaching main. All four conditions must be met:

1. RS is EFFECTIVE (requirements have been reviewed and approved)
2. RTM is EFFECTIVE (verification evidence has been reviewed and approved)
3. CI passes at the qualified commit
4. The CR's post-review confirms the merge

Merging before RS/RTM are EFFECTIVE, or merging without a CR, is a deviation requiring investigation.

### 7.4 Genesis Sandbox

Before the QMS is operational, a time-boxed genesis period permits development without full CR governance. Genesis work is adopted into the QMS via an adoption CR that retroactively establishes traceability. The genesis sandbox is a bootstrap mechanism, not a standing exception.

---

## 8. SDLC Coordination

### 8.1 RS and RTM as a Pair

RS defines what must be built. RTM proves it was built and verified. Neither is useful without the other. During a code CR, both are typically revised: RS to add or modify requirements, RTM to record verification evidence.

They are independent documents with independent review cycles, but they are coordinated in practice. Both must reach EFFECTIVE before the execution branch can merge.

### 8.2 Qualification as Event

Qualification is not a status — it is an event that occurs at a specific point in time when RS, RTM, and CI converge. The RTM captures this event. Once captured, the qualification evidence is immutable (the commit hash doesn't change, the RS version doesn't change).

### 8.3 CR Closure Prerequisites

A code CR cannot close until:
- RS is EFFECTIVE with all requirements from this CR
- RTM is EFFECTIVE with verification evidence for those requirements
- The execution branch has been merged to main
- Post-review has verified the merge

These are not arbitrary gates. Each one closes a specific assurance gap: requirements were reviewed (RS), evidence was reviewed (RTM), code was integrated (merge), and integration was verified (post-review).

---

## 9. Post-Review Expectations

Post-execution review is not a rubber stamp. Reviewers must verify:

- Every EI has a recorded outcome with traceable evidence.
- EIs flagged for VR have completed VR documents.
- All child documents (VAR, ADD) have met their block conditions (Type 1: closed, Type 2: pre-approved).
- The execution summary accurately reflects what happened, including any deviations from the plan.
- For code CRs: the merge PR is linked, the merge commit is verified, and the qualified commit is reachable from main.

If post-review reveals gaps, the document is rejected and returned for revision — not approved with caveats.

---

## 10. Retirement and Cancellation

### 10.1 When to Cancel

Cancel is for abandoning work that was never completed. Draft documents that will not be finished (duplicates, false starts, exploratory documents that proved unnecessary) should be canceled rather than left as orphaned drafts.

### 10.2 When to Retire

Retire is for removing documents that were once effective but are no longer needed. Retired documents are archived, not deleted — they may have driven workflows or established traceability that must remain auditable.

A document should be retired when:
- It has been superseded by a newer document
- The process or system it governs no longer exists
- It is obsolete and could cause confusion if followed

Retirement requires approval because removing an effective document from active use is itself a controlled change.
