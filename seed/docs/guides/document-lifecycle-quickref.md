# Document Lifecycle Quick Reference

One-page reference for all document types, their lifecycles, and key characteristics.

---

## Document Types at a Glance

| Type | Full Name | Category | Lifecycle | Parent | Key Characteristic |
|------|-----------|----------|-----------|--------|--------------------|
| **SOP** | Standard Operating Procedure | Non-executable | Non-executable | None | Standalone procedure; becomes EFFECTIVE |
| **RS** | Requirements Specification | Non-executable | Non-executable | None | SDLC singleton; defines "shall" statements |
| **RTM** | Requirements Traceability Matrix | Non-executable | Non-executable | None | SDLC singleton; proves requirements are met |
| **CR** | Change Record | Executable | Executable | None | Primary change authorization; may have TP, VAR, VR, ADD children |
| **INV** | Investigation | Executable | Executable | None | Deviation analysis; contains CAPAs as EIs |
| **TP** | Test Protocol | Executable | Executable | CR | Singleton child of CR; structured test procedures |
| **ER** | Exception Report | Executable | Executable | TP | Test step failure; requires re-execution |
| **VAR** | Variance Report | Executable | Executable | CR, INV | Execution deviation; Type 1 (blocking) or Type 2 (non-blocking) |
| **ADD** | Addendum Report | Executable | Executable | Any closed executable | Post-closure correction; parent must be CLOSED |
| **VR** | Verification Record | Executable | VR (truncated) | CR, VAR, ADD | Born IN_EXECUTION at v1.0; interactive authoring; cascade-closed |

---

## Non-Executable Lifecycle

Applies to: **SOP**, **RS**, **RTM**

```
DRAFT ──> IN_REVIEW ──> REVIEWED ──> IN_APPROVAL ──> EFFECTIVE
  ^          |              |              |
  |       withdraw          |           reject
  |          |              |              |
  +----------+              +--------------+
  |                                        |
  +----------------------------------------+

EFFECTIVE ──> RETIRED (via retirement approval)
```

### State Descriptions

| State | Meaning | What Can Happen |
|-------|---------|-----------------|
| **DRAFT** | Under development | Edit (checkout/checkin), route for review |
| **IN_REVIEW** | Reviewers evaluating | Reviewers submit outcomes, owner can withdraw |
| **REVIEWED** | All reviewers responded | Route for approval (if all recommend) |
| **IN_APPROVAL** | Awaiting approver | Approve (-> EFFECTIVE) or reject (-> REVIEWED) |
| **EFFECTIVE** | Approved and in force | Checkout starts a revision cycle; route for retirement |
| **RETIRED** | Permanently archived | Terminal state -- no further action |

### Version Progression

```
0.1 (created) -> 0.2 (checkin) -> 0.3 (checkin) -> 1.0 (approved/EFFECTIVE)
                                                    1.1 (revision checkin) -> 2.0 (re-approved)
```

---

## Executable Lifecycle

Applies to: **CR**, **INV**, **TP**, **ER**, **VAR**, **ADD**

```
PRE-EXECUTION PHASE
  DRAFT ──> IN_REVIEW ──> REVIEWED ──> IN_APPROVAL ──> PRE_APPROVED
    ^          |              |              |              |
    |       withdraw          |           reject          release
    +----------+              +--------------+              |
    +-------------------------+                             |
    +-----------------------[checkout from PRE_APPROVED]----+
                                                            |
                                                            v
POST-EXECUTION PHASE
  IN_EXECUTION ──> POST_REVIEW ──> POST_REVIEWED ──> POST_APPROVAL ──> POST_APPROVED
       ^               |               |                  |                  |
       |            withdraw            |               reject              close
       +---------------+               +-----------------+                   |
       +[revert]--------+                                                    v
       +[checkout]------+                                                 CLOSED
```

### State Descriptions

| State | Phase | Meaning | What Can Happen |
|-------|-------|---------|-----------------|
| **DRAFT** | Pre | Under development | Edit, route for review |
| **IN_REVIEW** | Pre | Pre-execution review | Reviewers evaluate the plan |
| **REVIEWED** | Pre | Plan reviewed | Route for approval (if gate met) |
| **IN_APPROVAL** | Pre | Awaiting plan approval | Approve or reject |
| **PRE_APPROVED** | Pre | Plan approved | Release to begin execution, or checkout for scope revision |
| **IN_EXECUTION** | Exec | Active work phase | Execute EIs, record evidence, create child docs, route for post-review |
| **POST_REVIEW** | Post | Post-execution review | Reviewers verify execution |
| **POST_REVIEWED** | Post | Execution reviewed | Route for approval, revert to execution, or checkout |
| **POST_APPROVAL** | Post | Awaiting execution approval | Approve or reject |
| **POST_APPROVED** | Post | Execution approved | Close |
| **CLOSED** | Terminal | Complete | No further action (ADD can be created against CLOSED parents) |

---

## VR Lifecycle (Truncated)

Applies to: **VR** (Verification Record)

VRs skip the entire pre-execution phase. They are born directly in IN_EXECUTION at version 1.0.

```
CREATE ──> IN_EXECUTION ──> POST_REVIEW ──> POST_REVIEWED ──> POST_APPROVAL ──> POST_APPROVED
                ^               |               |                  |                  |
                |            withdraw            |               reject              close
                +---------------+               +-----------------+                   |
                +[revert]--------+                                                    v
                                                                                   CLOSED
```

### Key Differences from Standard Executable

| Aspect | Standard Executable | VR |
|--------|--------------------|----|
| Born at version | 0.1 (DRAFT) | 1.0 (IN_EXECUTION) |
| Pre-review phase | Full review/approval cycle | Skipped entirely |
| First editable state | DRAFT | IN_EXECUTION |
| Authoring method | Freehand Markdown | Interactive only (`qms interact`) |
| Closure | Owner closes explicitly | Cascade-closed with parent |

---

## What Makes Each Type Unique

### SOP (Standard Operating Procedure)

- **Standalone.** Not a child of any other document.
- **Defines process.** SOPs are the rules that govern how other documents are created, reviewed, and executed.
- **EFFECTIVE state.** SOPs become EFFECTIVE (not CLOSED) because they remain in force indefinitely.
- **Revision cycle.** Checking out an EFFECTIVE SOP starts a new revision (version N.1) that goes through the full review/approval cycle again.

### CR (Change Record)

- **Primary change authorization.** Every code or process change requires a CR.
- **Rich parent.** Can spawn TP, VAR, VR, and ADD children.
- **Code CRs** have additional SDLC requirements: RS/RTM must be EFFECTIVE, execution branch must be merged, qualified commit must be recorded.
- **12-section structure.** The most structured document type in the QMS.

### INV (Investigation)

- **Deviation analysis.** Created when something goes wrong (process failure, code defect, workflow issue).
- **CAPAs as EIs.** Corrective/Preventive Actions are defined as execution items within the investigation.
- **Can spawn CRs.** CAPA execution may require creating new CRs for code or process fixes.

### TP (Test Protocol)

- **Singleton child of CR.** Each CR can have at most one TP (though the TP can contain multiple test cases).
- **Contains TC sections.** Test Cases are structured sections within the TP, not separate documents.
- **Failure handling.** Test step failures generate ER children.

### ER (Exception Report)

- **Test failure resolution.** Created when a TP test step fails.
- **Re-execution required.** After resolution, the failed test step must be re-executed and the passing result recorded.
- **Can nest.** If re-execution fails, a new ER is created as a child of the original ER.

### VAR (Variance Report)

- **Two types with different blocking behavior:**
  - **Type 1:** Parent cannot close until VAR is fully CLOSED.
  - **Type 2:** Parent can proceed once VAR reaches PRE_APPROVED.
- **Scope handoff.** Must explicitly document what scope moves from parent to child.
- **Not for test failures.** Test failures use ERs, not VARs.

### ADD (Addendum Report)

- **Post-closure correction.** Parent must be CLOSED before an ADD can be created.
- **Independent lifecycle.** The ADD goes through its own full review/approval/execution cycle.
- **Scope handoff.** Documents what the parent delivered and what the ADD corrects or supplements.

### VR (Verification Record)

- **Pre-approved evidence form.** Born at v1.0 in IN_EXECUTION -- no pre-review needed.
- **Interactive authoring only.** Authored via `qms interact`, not freehand Markdown.
- **Cascade close.** Closes automatically when parent closes (attachment semantics).
- **Engine-managed commits.** Evidence capture triggers automatic git commits, pinning project state at observation time.

### RS (Requirements Specification)

- **SDLC singleton.** One RS per governed system (each governed system gets its own RS).
- **Requirements only.** No implementation details -- just "the system shall..." statements.
- **Paired with RTM.** RS defines requirements; RTM proves they are met.

### RTM (Requirements Traceability Matrix)

- **SDLC singleton.** One RTM per governed system, paired with the RS.
- **Proof artifact.** Maps each requirement to implementation code and verification evidence.
- **Qualified baseline.** Contains the CI-verified commit hash -- the anchor for the qualified state of the system.

---

## Terminal States

| State | Applies To | How Reached | Reversible? |
|-------|-----------|-------------|-------------|
| **CLOSED** | Executable documents | `close` from POST_APPROVED | No. Use ADD for post-closure corrections. |
| **RETIRED** | All document types | `approve` on retirement routing | No. Document is permanently archived. |
| **CANCELLED** | Never-effective documents (v < 1.0) | `cancel --confirm` | No. Document is permanently removed. |

### Terminal State Decision Tree

```
Is this an executable document that completed its lifecycle?
  YES --> CLOSED (via close from POST_APPROVED)

Is this any document that is no longer needed?
  YES --> Was it ever approved (version >= 1.0)?
            YES --> RETIRED (via retirement approval workflow)
            NO  --> CANCELLED (via cancel --confirm)
```

---

## See Also

- [Routing Quick Reference](routing-quickref.md) -- Action-by-action routing cheat sheet
- [Review Guide](review-guide.md) -- How to prepare for and conduct reviews
- [Post-Review Checklist](post-review-checklist.md) -- Post-execution review preparation
- [Workflows](../03-Workflows.md) -- Full state machine diagrams with transition tables
- [Document Control](../02-Document-Control.md) -- Naming conventions, versioning, metadata architecture
- [Execution](../06-Execution.md) -- Executable block structure and EI documentation
- [Child Documents](../07-Child-Documents.md) -- ER, VAR, ADD, VR details
- [CR Reference](../types/CR.md) -- CR-specific template, enforcement, and lifecycle
- [VAR Reference](../types/VAR.md) -- VAR-specific template and Type 1/Type 2 details
- [VR Reference](../types/VR.md) -- VR-specific template and interactive authoring
- [QMS-Glossary](../QMS-Glossary.md) -- Term definitions
