# 7. Child Documents

Child documents handle situations where the planned execution path of a parent document cannot be followed as written, where corrections are needed after closure, or where structured evidence collection is required. Each type addresses a specific failure mode or need.

Every child document is an [executable document](06-Execution.md) that follows its own review/approval lifecycle while remaining linked to its parent.

---

## 7.1 The Four Types at a Glance

| Type | Full Name | Trigger | Parent Types | Parent State | Resolution |
|------|-----------|---------|--------------|--------------|------------|
| **[ER](types/ER.md)** | Exception Report | Test step fails during TP/TC execution | TP, TC | IN_EXECUTION | Re-execute failed step after resolution |
| **[VAR](types/VAR.md)** | Variance Report | Non-test execution cannot proceed as planned | CR, INV | IN_EXECUTION | Type 1: full closure; Type 2: pre-approval unblocks parent |
| **[ADD](types/ADD.md)** | Addendum Report | Post-closure correction or supplement needed | Any executable | CLOSED | New child; parent stays CLOSED |
| **[VR](types/VR.md)** | Verification Record | Behavioral verification evidence required | CR, VAR, ADD | IN_EXECUTION | Born at v1.0 IN_EXECUTION (no pre-review) |

---

## 7.2 Naming Conventions

Child documents derive their ID from the parent using a hierarchical scheme:

| Parent | Child | Example |
|--------|-------|---------|
| `TP-001` | ER | `TP-001-ER-001`, `TP-001-ER-002` |
| `CR-042` | VAR | `CR-042-VAR-001` |
| `CR-042` | ADD | `CR-042-ADD-001` |
| `CR-042` | VR | `CR-042-VR-001` |
| `CR-042-VAR-001` | VR | `CR-042-VAR-001-VR-001` |
| `CR-042-ADD-001` | VR | `CR-042-ADD-001-VR-001` |

Children can nest. A VAR can spawn VRs. An ADD can spawn VRs. An ER could theoretically nest ERs (for a re-execution failure within an exception resolution). See [Document Control](02-Document-Control.md) for the full naming convention.

---

## 7.3 ER (Exception Report)

### When to Use

An ER is created when a test step within a Test Protocol (TP) or Test Case (TC) produces a result that does not match the expected outcome. ERs are exclusively for **test execution failures** -- if a non-test execution item fails, use a [VAR](#74-var-variance-report) instead.

### Content Requirements

An ER must document:

1. **Failed step reference** -- which TP/TC step failed and what was expected vs. observed
2. **Root cause analysis** -- why the step failed (code defect, environment issue, test design flaw, etc.)
3. **Resolution** -- what was done to address the failure
4. **Re-execution plan** -- how the failed step will be re-executed to demonstrate the fix

### Re-Execution Requirement

After the ER's resolution work is complete, the failed test step must be **re-executed** and the passing result recorded. This is non-negotiable -- the original failure evidence stays in the record (append-only), and the successful re-execution is added alongside it.

### Nested ERs

If re-execution itself fails, a new ER is created as a child of the original ER. This creates a traceable chain of failures and resolutions without overwriting history.

### Lifecycle

```
TP step fails
  --> Create ER (child of TP)
  --> ER goes through draft -> review -> approval -> execution
  --> Resolve the issue during ER execution
  --> Re-execute the failed TP step, record passing result
  --> ER post-review -> close
  --> Resume TP execution
```

---

## 7.4 VAR (Variance Report)

### When to Use

A VAR is created when execution of a **non-test** executable document (CR or INV) cannot proceed as planned. This covers situations like:

- An execution item produces an unexpected outcome
- The planned approach is discovered to be infeasible during execution
- External conditions change mid-execution, requiring deviation from the plan
- Scope grows beyond what was originally approved

VARs are **not** for test failures (use [ER](#73-er-exception-report)) and **not** for post-closure corrections (use [ADD](#75-add-addendum-report)).

### Type 1 vs Type 2

VARs come in two variants based on how they interact with the parent's workflow:

| Attribute | Type 1 | Type 2 |
|-----------|--------|--------|
| **Blocking behavior** | Parent cannot close until VAR is fully CLOSED | Parent can proceed once VAR is PRE_APPROVED |
| **Use case** | VAR work is prerequisite for parent completion | VAR work can be completed after parent closes |
| **Typical scenario** | Code fix needed before merge gate | Documentation update can follow separately |

**Type 2 is the efficiency mechanism.** When a variance occurs late in execution and the resolution is not a prerequisite for the parent's remaining work, Type 2 allows the parent to proceed to closure without waiting for the full VAR lifecycle to complete. The VAR still must be closed eventually -- it just does not block the parent.

### Content Requirements

A VAR must document:

1. **Variance description** -- what deviated from the plan and why
2. **Impact assessment** -- what parent execution items are affected
3. **Resolution plan** -- execution items describing how the variance will be resolved
4. **Scope handoff** -- explicit statement of what work moves from parent to child

### Scope Handoff

This is the critical integrity mechanism. When a VAR absorbs work from its parent, the handoff must explicitly specify:

- **What the parent accomplished** up to the point of variance
- **What the child absorbs** (the scope that moved from parent to VAR)
- **Confirmation that no scope was lost** in the transfer

The scope handoff prevents work from silently disappearing when execution deviates from plan.

### Lifecycle

```
CR execution hits unexpected outcome at EI-N
  --> Create VAR (child of CR)
  --> VAR goes through draft -> review -> approval
  --> [Type 2 only: parent can now proceed past the blocked point]
  --> Execute VAR resolution
  --> VAR post-review -> close
  --> [Type 1 only: parent can now proceed past the blocked point]
```

---

## 7.5 ADD (Addendum Report)

### When to Use

An ADD is created when a **closed** executable document needs correction or supplementation. The parent must already be in the CLOSED state. If the parent is still in execution, use a [VAR](#74-var-variance-report) instead.

Typical triggers:

- A defect is discovered in work completed under a closed CR
- Documentation produced during a closed CR needs correction
- Additional scope is identified that logically belongs to a closed CR's change

### Content Requirements

An ADD must document:

1. **Correction description** -- what needs to change and why
2. **Parent reference** -- the closed document being corrected
3. **Scope statement** -- execution items describing the correction work
4. **Scope handoff** -- what the parent originally delivered, what the ADD corrects or supplements, and confirmation of scope integrity

### Scope Handoff

The ADD scope handoff follows the same pattern as VAR, but in reverse: instead of absorbing scope from an in-progress parent, the ADD is adding or correcting scope on a completed parent.

### Lifecycle

```
Defect discovered in closed CR-042
  --> Create ADD (child of CR-042, which must be CLOSED)
  --> ADD goes through draft -> review -> approval -> execution
  --> Execute corrections
  --> ADD post-review -> close
```

---

## 7.6 VR (Verification Record)

### When to Use

A VR is created when an execution item requires **structured behavioral verification** -- evidence that a capability works as intended, collected through a defined procedure with observable outcomes. VRs are the QMS equivalent of GMP batch records: pre-approved evidence forms that are filled out during execution rather than authored freehand.

VRs are children of CRs, VARs, or ADDs. An execution item that requires a VR is flagged with `VR=Yes` in the parent's EI table.

### How VRs Differ from Other Child Documents

VRs follow a unique lifecycle:

| Attribute | ER / VAR / ADD | VR |
|-----------|----------------|-----|
| **Born at version** | 0.1 (draft) | 1.0 (pre-approved) |
| **Pre-review phase** | Yes (standard review/approval) | No -- skipped entirely |
| **First state** | DRAFT | IN_EXECUTION |
| **Authoring method** | Freehand markdown or interactive | Interactive only (`qms interact`) |
| **Independent review** | Has its own review/approval | Reviewed as part of parent's post-review |

The rationale: a VR's structure is governed by a pre-approved template. The verification procedure (what to test, what to expect) is defined during VR creation via the interactive engine. No separate pre-approval is needed because the template itself is the approved form.

### The GMP Batch Record Analogy

In pharmaceutical manufacturing, batch records are pre-approved forms that operators fill in during production. The form structure is validated once; each execution is a fill-in exercise. VRs work the same way:

1. The template (TEMPLATE-VR.md) defines the form structure and is itself a controlled document
2. Creating a VR instantiates the template for a specific verification
3. The author fills in the form via `qms interact`, recording evidence as execution proceeds
4. The completed VR is reviewed as part of the parent's post-review, not independently

### Content Requirements

A VR captures:

1. **Verification identification** -- parent document, related EIs, date
2. **Verification objective** -- the capability being verified (not the specific mechanism)
3. **Prerequisites** -- system state before verification begins (reproducible by a third party)
4. **Verification steps** (loop) -- for each step:
   - Instructions (what you are about to do)
   - Expected result (stated before execution)
   - Actual result (observed during execution, with primary evidence)
   - Outcome (Pass/Fail)
5. **Summary** -- overall outcome and narrative

### Evidence Standards

Evidence recorded in VRs must be:

| Standard | Meaning | Example |
|----------|---------|---------|
| **Observational** | Based on what was actually observed, not inferred | Paste terminal output, not "it worked" |
| **Contemporaneous** | Recorded at the time of observation, not reconstructed later | Engine-managed commits pin the project state at observation time |
| **Reproducible** | A third party can reproduce the conditions and verify | Prerequisites must specify exact branch, commit, environment |

The `commit: true` attribute on the `step_actual` prompt triggers an engine-managed git commit, recording the exact project state at the moment of evidence capture. The commit hash is stored in the response entry, creating an immutable link between the evidence and the codebase.

### Lifecycle

```
Parent EI flagged VR=Yes
  --> Create VR (child of parent) via qms create VR
  --> VR is born at v1.0, state: IN_EXECUTION (no pre-review)
  --> Author fills VR via qms interact (see 08-Interactive-Authoring.md)
  --> checkin compiles the .source.json into markdown
  --> VR enters post-review as part of parent's post-review cycle
  --> Parent post-approval triggers VR post-approval
  --> Parent close triggers VR close
```

VRs are authored exclusively through the [interactive authoring system](08-Interactive-Authoring.md). See that document for the template tag syntax, response model, and interaction commands.

---

## 7.7 Decision Guide: Which Child Document?

```
Is this a TEST step failure?
  YES --> ER
  NO  --> Is the parent still IN_EXECUTION?
            YES --> Is execution blocked or deviating from plan?
                      YES --> VAR
                      NO  --> (not a child document situation)
            NO  --> Is the parent CLOSED?
                      YES --> Is this a correction or supplement?
                              YES --> ADD
                              NO  --> (not a child document situation)
                      NO  --> (document not in a state that accepts children)

Does an execution item need structured behavioral evidence?
  YES --> VR (created during execution, regardless of other child documents)
```

---

**See also:**
- [06-Execution.md](06-Execution.md) -- Executable block structure, EI tables, evidence requirements
- [08-Interactive-Authoring.md](08-Interactive-Authoring.md) -- Interactive authoring system (VR authoring)
- [03-Workflows.md](03-Workflows.md) -- Document state machine and transitions
- [10-SDLC.md](10-SDLC.md) -- Verification Records as an RTM verification type
- [12-CLI-Reference.md](12-CLI-Reference.md) -- CLI commands for creating child documents
- [QMS-Glossary.md](QMS-Glossary.md) -- Term definitions
