# Failure Decision Guide

Something went wrong during execution. This guide helps you decide what to do, what document to create, and what to record in the parent.

---

## Decision Flowchart

Start here when an execution item does not go as planned.

```
Something went wrong during execution.
    |
    |-- Is the parent document already CLOSED?
    |       |
    |       YES --> Is this a correction or supplement to the closed work?
    |       |           |
    |       |           YES --> Create an ADD (Addendum Report)
    |       |           |       See: "ADD Path" below
    |       |           |
    |       |           NO --> Is this a systemic or process issue?
    |       |                       |
    |       |                       YES --> Create an INV (Investigation)
    |       |                       |       See: "INV Path" below
    |       |                       |
    |       |                       NO --> Not a child document situation.
    |       |                               Consider a new CR instead.
    |
    |-- Is this a TEST step failure (in a TP or TC)?
    |       |
    |       YES --> Create an ER (Exception Report)
    |               See: "ER Path" below
    |
    |-- Is this a non-test execution failure?
    |       |
    |       YES --> Is the cause clear and localized?
    |       |           |
    |       |           YES --> Create a VAR (Variance Report)
    |       |           |       See: "VAR Path" below
    |       |           |
    |       |           NO --> Is this systemic or does it suggest a process failure?
    |       |                       |
    |       |                       YES --> Create an INV (Investigation)
    |       |                       |       See: "INV Path" below
    |       |                       |
    |       |                       NO --> Create a VAR. If root cause analysis
    |       |                               reveals systemic issues during VAR
    |       |                               execution, escalate to INV then.
    |
    |-- Is this not really a failure, but a scope issue?
            |
            See: Scope Change Guide
```

---

## The Four Paths

### ER Path (Test Failures)

**When:** A test step in a TP or TC produces a result that does not match the expected outcome.

**Parent document type:** TP (Test Protocol)

**What to do:**

1. Stop test execution at the failed step
2. Mark subsequent steps as N/A with a note: "Blocked by Step N failure"
3. Create the ER:
   ```bash
   qms create ER --parent CR-001-TP-001 --title "TC-001 Step 003 Failure: Widget not rendered"
   ```
4. In the ER, document:
   - Which step failed and what was expected vs. observed
   - Root cause analysis
   - Proposed corrective action
   - Re-test plan (full re-execution of the test case, not just the failed step)
5. Route ER through pre-review and pre-approval
6. Execute the re-test
7. If re-test passes: close the ER, resume TP execution
8. If re-test fails: create a new ER under the same TP parent

**In the parent TP's record:**
- Mark the original test step as Fail
- Reference the ER ID in the comments: "See CR-001-TP-001-ER-001"

**Key rule:** The re-test is a *full re-execution* of the test case, not just the failed step. See [ER Reference](../types/ER.md) for template structure.

---

### VAR Path (Non-Test Execution Failures)

**When:** An execution item in a CR or INV cannot be completed as planned, and the cause is understood.

**Parent document types:** CR, INV (or any non-test executable)

**What to do:**

1. Mark the EI as Fail in the parent's EI table
2. Record the failure observation in the Actual Outcome column
3. Create the VAR:
   ```bash
   qms create VAR --parent CR-045 --title "EI-3 test regression requires alternative approach"
   ```
4. Decide Type 1 or Type 2 (see decision criteria below)
5. In the VAR, document:
   - What deviated from the plan
   - Impact assessment
   - Resolution plan with its own EI table
   - Scope handoff from parent
6. Route VAR through pre-review and pre-approval
7. Execute VAR resolution
8. Close the VAR (Type 1) or proceed with parent once VAR is pre-approved (Type 2)

**In the parent's EI table:**

```markdown
| EI-3 | Implement API fix | Response completes in <200ms | Request times out after 30s+ due to interaction with existing connection pool limits | See CR-045-VAR-001 | Fail | claude | 2026-02-15 |
```

**Key rule:** The parent EI gets a Fail outcome and a reference to the VAR. Do not leave the EI blank or try to resolve the failure inline.

---

### ADD Path (Post-Closure Corrections)

**When:** A defect or omission is discovered in work completed under a closed document.

**Parent document state:** Must be CLOSED

**What to do:**

1. Verify the parent is actually CLOSED:
   ```bash
   qms status CR-045
   ```
2. Create the ADD:
   ```bash
   qms create ADD --parent CR-045 --title "Add missing configuration step from original implementation"
   ```
3. In the ADD, document:
   - What was omitted or needs correction
   - How it was discovered
   - Impact assessment
   - Correction plan with EI table
   - Scope handoff (what parent accomplished, what ADD corrects, confirmation nothing was lost)
4. Route ADD through full lifecycle (pre-review, approval, execution, post-review, closure)

**In the parent:** Nothing changes. The parent is CLOSED and immutable. The ADD is a separate child document that references the parent.

**Key rule:** The parent document stays closed. ADDs are "corrections alongside," not "corrections to." See [ADD Reference](../types/ADD.md).

---

### INV Path (Systemic/Process Failures)

**When:** The failure suggests a deeper problem -- a process gap, a systemic defect, a pattern of recurring issues, or an unclear root cause that needs formal investigation.

**What to do:**

1. Create the INV:
   ```bash
   qms create INV --title "Investigation: Recurring timeout failures across multiple CRs"
   ```
2. In the INV, document:
   - Description of the deviation
   - Impact assessment
   - Root cause analysis (5 Whys or similar)
   - CAPAs (corrective and preventive actions)
3. CAPAs may spawn child CRs for implementation:
   ```
   INV-005
     EI-1: Root cause analysis (done in INV)
     EI-2: Corrective action -- create CR-060 to fix the defect
     EI-3: Preventive action -- create CR-061 to add regression tests
   ```
4. Route INV through full lifecycle

**In the original parent document:** If an EI failure triggered the INV, mark the EI as Fail and reference the INV in the evidence column: "See INV-005 for root cause analysis."

**Key rule:** INVs are always top-level documents, not children. They reference their triggering context but live independently. See [INV Reference](../types/INV.md) and [Deviation Management](../05-Deviation-Management.md).

---

## VAR Type 1 vs Type 2

This is the most common decision point. Get it right to avoid blocking the parent unnecessarily or closing the parent prematurely.

### Decision Criteria

| Question | Type 1 | Type 2 |
|----------|--------|--------|
| Is the VAR resolution a prerequisite for the parent's remaining work? | Yes | No |
| Can the parent meaningfully close without the VAR being fully resolved? | No | Yes |
| Does the VAR affect the parent's merge gate or code state? | Yes | No |
| Is the VAR resolution work independent of the parent's objectives? | No | Yes |
| Could the VAR resolution happen days or weeks after the parent closes? | No | Yes |

### Examples

| Scenario | Type | Rationale |
|----------|------|-----------|
| Code fix needed before the CR's execution branch can merge | **Type 1** | Parent cannot close until the code is correct and verified |
| Solver regression that blocks subsequent EIs | **Type 1** | Remaining parent EIs depend on the fix |
| Documentation update that can follow the code change | **Type 2** | Parent's code work is complete; docs can catch up |
| RTM update needed but does not affect functional delivery | **Type 2** | RTM is important but not a gate for the implementation |
| Config value discovered to be suboptimal but functional | **Type 2** | System works; optimization can follow |
| Missing test coverage discovered during execution | **Type 1** if tests are required for the merge gate; **Type 2** if tests are additive |

### When in Doubt

Default to **Type 1**. It is always safe to require full closure before the parent proceeds. Type 2 is an efficiency optimization -- use it when you are confident the parent can close without the VAR work being proven complete.

---

## Scope Handoff Checklist

When creating any child document (VAR, ADD, ER), verify these items to ensure no scope is lost:

- [ ] **Parent EI marked:** The failing EI in the parent has outcome = Fail and references the child document ID
- [ ] **Scope transfer explicit:** The child document states exactly what work it absorbs from the parent
- [ ] **No silent drops:** Every pre-approved parent EI has either a Pass outcome or a Fail outcome with an attached child document
- [ ] **Dependencies identified:** If the child document's resolution affects other parent EIs, those EIs are noted
- [ ] **Handoff documented:** The child document's scope handoff section (VAR or ADD) explicitly confirms no scope was lost

### What to Record in the Parent's EI Table

When an EI fails and a child document is created:

| Column | What to Write |
|--------|--------------|
| **Actual Outcome** | Brief description of what happened (the failure, not the resolution) |
| **Evidence** | Child document reference: "See CR-045-VAR-001" |
| **Task Outcome** | Fail |
| **Performed By** | Your identity |
| **Date** | Date the failure was observed |

**Do not:**
- Leave the EI row blank
- Write the resolution in the parent's EI (that goes in the child document)
- Mark the EI as Pass if it did not achieve its Expected Outcome
- Create the child document without recording the failure in the parent first

---

## Escalation Guide

### Handle Autonomously

You can create and manage these without Lead involvement:

- **VAR (Type 2)** for non-blocking execution deviations with clear cause
- **ER** for test step failures with straightforward root cause
- **VR** flagged items (these are planned, not failures)

### Consult the Lead Before Proceeding

Escalate when:

| Situation | Why Escalate |
|-----------|-------------|
| **VAR Type 1** that will significantly delay the parent | Lead should confirm the blocking assessment |
| **Multiple VARs** on the same parent | Pattern suggests the plan was flawed; Lead may want to reassess |
| **INV creation** | Investigations have broader impact; Lead should be aware |
| **ADD on a recently-closed document** | Lead should confirm the defect assessment before opening correction work |
| **Unclear whether VAR or INV** | If you cannot determine whether the issue is local or systemic, ask |
| **Scope reduction** | Any situation where pre-approved scope might not be completed |
| **Cross-document impact** | Failure affects documents outside the current execution |

### Emergency: Execution Cannot Continue

If you discover a situation where execution absolutely cannot proceed and no existing process seems to apply:

1. Stop execution
2. Document what you observed in the Execution Comments table
3. Check in any open documents to preserve state
4. Report to the Lead with:
   - What you were doing
   - What happened
   - What you think the options are
   - Your recommendation

**Do not improvise a workaround that bypasses the QMS.** If the process does not cover your situation, that is itself a finding that should be investigated.

---

## Quick Reference: Child Document Creation

| Type | Command | Parent State | Key Requirement |
|------|---------|-------------|-----------------|
| ER | `qms create ER --parent {TP_ID} --title "..."` | Any | Parent must be a TP |
| VAR | `qms create VAR --parent {DOC_ID} --title "..."` | Any | Parent must be executable |
| ADD | `qms create ADD --parent {DOC_ID} --title "..."` | CLOSED | Parent must be CLOSED |
| INV | `qms create INV --title "..."` | N/A | Top-level document (no parent) |

---

**See also:**
- [Execution Policy](../06-Execution.md) -- Scope integrity, evidence requirements, task outcomes
- [Child Documents](../07-Child-Documents.md) -- Full lifecycle details for ER, VAR, ADD, VR
- [Deviation Management](../05-Deviation-Management.md) -- INV structure and root cause analysis
- [Scope Change Guide](scope-change-guide.md) -- When the issue is scope, not failure
- [VAR Reference](../types/VAR.md) -- VAR template structure and Type 1/Type 2 details
- [ADD Reference](../types/ADD.md) -- ADD template structure and parent state requirements
- [ER Reference](../types/ER.md) -- ER template structure and re-test mechanics
- [INV Reference](../types/INV.md) -- INV template structure and CAPA table
- [QMS-Glossary](../QMS-Glossary.md) -- Term definitions
