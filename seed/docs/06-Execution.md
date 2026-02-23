# 6. Execution

Executable documents ([CRs](types/CR.md), [INVs](types/INV.md), [TPs](types/TP.md), [ERs](types/ER.md), [VARs](types/VAR.md), [ADDs](types/ADD.md), [VRs](types/VR.md)) share a common execution model. This document covers the structure of the executable block, how execution items are tracked, evidence requirements, and the principle of scope integrity.

> **Related docs:** [04-Change-Control.md](04-Change-Control.md) for CR-specific content, [05-Deviation-Management.md](05-Deviation-Management.md) for INV-specific content, [07-Child-Documents.md](07-Child-Documents.md) for child document types created during execution.

---

## The Executable Block

Every executable document contains an **executable block** -- the section where implementation work is planned and recorded. The block has two categories of fields:

### Static Fields vs. Editable Fields

| Field Type | Definition | When Set | Can Be Modified During Execution? |
|------------|-----------|----------|-----------------------------------|
| **Static** | Defined at authoring time; part of the approved scope | Before approval | No |
| **Editable** | Filled in during execution; records actual work performed | During execution | Yes |

**Static fields** are locked at approval. They define *what was approved*. Changing them would change the approved scope, which requires a [VAR](07-Child-Documents.md).

**Editable fields** are where execution evidence is recorded. They are blank at approval and populated during the IN_EXECUTION phase.

### Example: An EI Row

```
Static:   "EI-3: Implement the dropdown widget per Section 5 design"
Editable: actual outcome, evidence, signature, timestamp
```

The static part is the approved task description. The editable part is filled in when the task is actually performed.

---

## EI Table Format

The Execution Items (EI) table is the core tracking mechanism. Each row represents one discrete unit of work.

### Columns

| Column | Type | Description |
|--------|------|-------------|
| **EI #** | Static | Sequential identifier (EI-1, EI-2, ...) |
| **Task Description** | Static | What must be done -- the approved scope for this item |
| **Expected Outcome** | Static | What success looks like for this task |
| **Actual Outcome** | Editable | What actually happened -- filled during execution |
| **Evidence** | Editable | Proof of completion (see Evidence Requirements below) |
| **Task Outcome** | Editable | **Pass** or **Fail** |
| **Performed By** | Editable | Who executed this item (user identity) |
| **Date** | Editable | When the item was executed |

### Example EI Table

| EI # | Task Description | Expected Outcome | Actual Outcome | Evidence | Outcome | By | Date |
|------|-----------------|------------------|----------------|----------|---------|----|------|
| EI-1 | Create execution branch from main@abc123 | Branch exists | Branch `cr-045/exec` created from abc123 | `git log --oneline -1` output | Pass | claude | 2026-02-15 |
| EI-2 | Implement dropdown widget | Widget renders in toolbar | Widget renders, responds to click events | Commit def456, screenshot | Pass | claude | 2026-02-15 |
| EI-3 | Update RTM with new requirement traces | RTM reflects new widget requirements | Could not complete -- requirement IDs not yet assigned | See VAR-001 | Fail | claude | 2026-02-16 |

---

## Document States During Execution

Executable documents pass through a specific sequence of states:

```
PRE_APPROVED ──release──> IN_EXECUTION ──route review──> POST_REVIEWED
     │                         │                              │
     │                         │                              ├──reject──> IN_EXECUTION
     │                         │                              │            (revert possible)
     │                         │                              │
     │                         │                         route approval
     │                         │                              │
     │                         │                        POST_APPROVED
     │                         │                              │
     │                         │                           close
     │                         │                              │
     │                         │                           CLOSED
     │                         │
     │                    (if issues found during post-review)
     │                         │
     │                    revert back to IN_EXECUTION
     │
  (document sits here until owner releases it)
```

### State Transitions

| From | Action | To | Who |
|------|--------|----|-----|
| PRE_APPROVED | `release` | IN_EXECUTION | Document owner |
| IN_EXECUTION | `route --review` | POST_REVIEWED | Document owner |
| POST_REVIEWED | `approve` | POST_APPROVED | QA/Reviewer |
| POST_REVIEWED | `reject` | (back for revision) | QA/Reviewer |
| POST_REVIEWED | `revert` | IN_EXECUTION | Document owner |
| POST_APPROVED | `close` | CLOSED | Document owner |

### Key Points

- **PRE_APPROVED** is a holding state. The document is approved but no work has started. The owner must explicitly release it.
- **IN_EXECUTION** is the active work phase. EI editable fields are populated here.
- **POST_REVIEWED** is where the review team verifies execution quality.
- **CLOSED** is terminal. No further modifications are possible. If corrections are needed after closure, an [ADD (Addendum Report)](07-Child-Documents.md) must be created.

---

## Pre/Post Execution Commit Requirements

Execution must be bookended by git commits that establish the code state:

### Pre-Execution Commit

Before beginning execution work, record the starting point:
- The commit hash from which the execution branch is created
- This goes in EI-1 (typically "Create execution branch")

### Post-Execution Commit

After all execution work is complete:
- All code changes must be committed
- The final commit hash is recorded in the execution summary
- This commit becomes the candidate for the qualified commit (see [09-Code-Governance.md](09-Code-Governance.md))

### Why This Matters

The commit bookends create a verifiable window: "The code was at state X before this CR, and at state Y after." Post-reviewers can diff these commits to verify that only approved changes were made.

---

## Scope Integrity

**Scope integrity is the principle that approved scope cannot be silently dropped.**

Every static EI that was approved must have a documented outcome. There are only two valid outcomes:

| Outcome | Meaning | What Is Required |
|---------|---------|-----------------|
| **Pass** | The task was completed as described | Evidence of completion |
| **Fail** | The task could not be completed as described | A child document (VAR or ER) explaining why and resolving the gap |

### What Scope Integrity Prohibits

- Deleting an EI from the table because it turned out to be unnecessary
- Leaving an EI blank with no outcome
- Marking an EI as "N/A" without a VAR documenting why
- Completing a task differently than described without a VAR

### How Deviations Are Handled

When an EI cannot be executed as approved:

1. Mark the EI outcome as **Fail**
2. Create a child document:
   - **VAR** for non-test executable documents (CRs, INVs)
   - **ER** for test execution failures (TPs)
3. The child document captures: what went wrong, why, and how it was resolved
4. The child document reference goes in the EI's evidence column

This ensures traceability: the approved scope is preserved in the static fields, the actual outcome is recorded in the editable fields, and any gap between them is fully documented.

---

## Evidence Requirements

Every EI must include evidence demonstrating its completion. The type of evidence depends on the nature of the task.

### Evidence Types

| Evidence Type | When to Use | Example |
|---------------|-------------|---------|
| **Commit hash** | Code changes | `abc1234` with brief description of what the commit contains |
| **CLI output** | System verification | Output of `qms status`, `git log`, test runner results |
| **Screenshot** | Visual verification | UI rendering, before/after comparisons |
| **Document reference** | QMS document changes | `SOP-002 v2.0 EFFECTIVE` |
| **Test results** | Automated verification | CI output, unit test pass/fail summary |
| **Prose description** | Qualitative verification | Explanation of manual verification steps and observations |

### Evidence Standards

- Evidence must be **specific**. "Tests pass" is insufficient. "pytest output: 42 passed, 0 failed (commit abc1234)" is sufficient.
- Evidence must be **contemporaneous**. Record it when the work is done, not retroactively.
- Evidence must be **traceable**. A reader should be able to follow the evidence back to the source (the commit, the file, the test output).

---

## Task Outcomes: Pass and Fail

### Pass

A **Pass** outcome means:
- The task was completed as described in the static Task Description
- The Expected Outcome was achieved
- Evidence is recorded proving completion

No additional documentation is required beyond the EI table entry.

### Fail

A **Fail** outcome means:
- The task could not be completed as described, OR
- The Expected Outcome was not achieved

A Fail **requires** an attached child document:

| Parent Document Type | Child Document for Failures |
|---------------------|---------------------------|
| CR, INV, VAR, ADD | **VAR** (Variance Report) |
| TP (Test Protocol) | **ER** (Exception Report) |

The child document must explain the deviation, analyze its cause, and document the resolution. See [07-Child-Documents.md](07-Child-Documents.md) for child document details.

### There Is No "Skip" or "N/A"

If an approved EI turns out to be unnecessary, it still cannot be skipped. The outcome is Fail with a VAR explaining why the task is no longer applicable and confirming that dropping it does not affect the overall change objectives.

---

## Verification Records (VRs)

A special case in the execution model: **Verification Records** are pre-approved evidence forms that are born directly in IN_EXECUTION state -- they skip the pre-review phase entirely. VRs are used for structured behavioral verification and are children of CRs, VARs, or ADDs. See [07-Child-Documents.md](07-Child-Documents.md) for details.

---

## Quick Reference: Execution Commands

```bash
# Release an approved document for execution
qms release CR-045

# After execution, route for post-review
qms route CR-045 --review

# If post-review reveals issues, revert to execution
qms revert CR-045 --reason "Need to add missing evidence for EI-3"

# After post-review approval, close
qms close CR-045
```

See [12-CLI-Reference.md](12-CLI-Reference.md) for the full command reference.

---

## See Also

- [03-Workflows.md](03-Workflows.md) -- Full state machine diagrams for executable and non-executable documents
- [04-Change-Control.md](04-Change-Control.md) -- CR-specific content requirements and post-review gates
- [09-Code-Governance.md](09-Code-Governance.md) -- Execution branch workflow and qualified commits
- [QMS-Policy.md](QMS-Policy.md) -- Evidence adequacy and scope integrity judgment criteria

---

## Glossary References

Key terms used in this document: [Executable Block](QMS-Glossary.md), [Executable Document](QMS-Glossary.md), [Execution Item](QMS-Glossary.md), [Static Field](QMS-Glossary.md), [Editable Field](QMS-Glossary.md), [Evidence](QMS-Glossary.md), [Task Outcome](QMS-Glossary.md), [VAR](QMS-Glossary.md), [ER](QMS-Glossary.md), [Verification Record](QMS-Glossary.md), [CLOSED](QMS-Glossary.md), [Scope Handoff](QMS-Glossary.md).
