# 5. Deviation Management

When something goes wrong -- a process is not followed, a product defect is discovered, or an approved plan cannot be executed -- the QMS uses **Investigations (INVs)** to analyze what happened and prevent recurrence. This document covers when to investigate, how INVs are structured, and how corrective actions flow back into the system.

> **Related docs:** [04-Change-Control.md](04-Change-Control.md) for CRs that implement CAPA fixes, [06-Execution.md](06-Execution.md) for how INVs are executed, [07-Child-Documents.md](07-Child-Documents.md) for VARs (execution-time deviations).

---

## Two Types of Deviations

| Type | Definition | Examples |
|------|-----------|----------|
| **Procedural Deviation** | A problem with a procedure as approved, or with the actual use of a procedure | SOP step was skipped; review checklist was incomplete; CLI allowed an invalid state transition |
| **Product Deviation** | A problem with the product itself | Code bug; design flaw; incorrect output; UI rendering error |

The distinction matters because it determines where the corrective action lands:

- **Procedural deviations** lead to [SOP](types/SOP.md) updates, tooling fixes, or process changes
- **Product deviations** lead to code fixes, design changes, or [requirement](types/RS.md) updates

Both types are investigated using the same INV document structure.

---

## When to Create an Investigation

### Create an INV When:

- An approved procedure was not followed (intentionally or accidentally)
- A QMS process failure is discovered (e.g., a document was approved with missing sections)
- A defect is found in a previously qualified system
- An execution item fails and the root cause is unclear or systemic
- A pattern of recurring issues suggests a deeper problem

### Do NOT Create an INV When:

- An execution item fails due to a known, localized issue -- use a [VAR](07-Child-Documents.md) instead
- A test step fails during a Test Protocol -- use an [ER (Exception Report)](07-Child-Documents.md) instead
- The issue is a simple scope change during execution -- use a VAR
- You want to track a feature request or improvement idea -- use your project backlog

### Decision Guide

```
Something went wrong during execution
    |
    ├── Is this a test failure in a TP? --> ER (Exception Report)
    ├── Is this an execution deviation with clear local cause? --> VAR (Variance Report)
    └── Is this systemic, unclear, or involves process failure? --> INV (Investigation)
```

---

## INV Content Requirements

An Investigation document contains these sections:

| Section | Purpose |
|---------|---------|
| **Description of Deviation** | What happened, when, and where it was discovered |
| **Impact Assessment** | What is affected -- documents, code, other CRs, system state |
| **Root Cause Analysis** | Systematic analysis of *why* the deviation occurred |
| **CAPAs** | Corrective and Preventive Actions to address the root cause |
| **Execution** | The executable block where CAPA implementation is tracked |
| **Execution Summary** | Post-execution narrative of what was done |
| **References** | Related documents, CRs, SOPs |

---

## Root Cause Analysis

Root cause analysis is the core intellectual work of an INV. The goal is to identify the **fundamental reason** the deviation occurred -- not just the proximate trigger.

### Approach

1. **Describe the observable facts.** What exactly happened? When? What was the expected behavior?
2. **Trace the causal chain.** Work backward from the deviation to its origin. Use "5 Whys" or similar techniques.
3. **Identify the root cause.** The root cause is the point in the chain where intervention would have prevented the deviation.
4. **Distinguish root cause from contributing factors.** There may be multiple factors, but the root cause is the one that, if removed, would have prevented the event.

### Example

```
Deviation: CR-042 was approved with an empty Testing Summary section.

Why was it empty?          The author forgot to populate it.
Why wasn't it caught?      The reviewer did not check for completeness.
Why didn't the reviewer?   The review checklist doesn't include a section-completeness check.
Why not?                   The SOP defines review criteria in general terms, not as a checklist.

Root cause: SOP-002 lacks a concrete pre-approval checklist for reviewers.
Contributing factor: Author oversight (addressed by the checklist fix).
```

---

## CAPAs: Corrective and Preventive Actions

CAPAs are **a category of execution item within an INV** -- they are not standalone documents. Each CAPA is recorded as an EI in the INV's executable block.

### Corrective vs. Preventive

| Type | Definition | Addresses |
|------|-----------|-----------|
| **Corrective Action** | Eliminates the cause of an *existing* deviation and/or remediates its consequences | What already happened |
| **Preventive Action** | Eliminates the cause of a *potential future* deviation | What might happen again |

A single INV typically contains both types. Using the example above:

- **Corrective:** Re-review CR-042 to verify the Testing Summary gap did not affect the approved change (remediating the specific instance)
- **Preventive:** Update SOP-002 to include a reviewer pre-approval checklist (preventing recurrence)

### CAPA Implementation via Child CRs

CAPAs that require changes to code, SOPs, or other controlled documents are implemented through **child Change Records**. The flow is:

```
INV-005 (Investigation)
 ├── EI-1: Root cause analysis (documented in INV)
 ├── EI-2: Corrective Action -- re-review CR-042 (done directly)
 ├── EI-3: Preventive Action -- update SOP-002
 │    └── CR-050 (child CR implementing the SOP change)
 └── EI-4: Verify CAPA effectiveness
```

The INV's EI table references the child CRs. The child CRs go through their own full lifecycle (review, approval, execution, closure). The INV cannot close until its CAPA CRs reach appropriate states.

### What CAPAs Are NOT

- CAPAs are not standalone documents in this QMS. They exist only as EIs within an INV.
- CAPAs are not optional. Every INV must define at least one CAPA.
- CAPAs are not vague intentions. Each must be a concrete, verifiable action with a clear completion criterion.

---

## INV Execution

Like all executable documents, INVs follow the execution lifecycle described in [06-Execution.md](06-Execution.md):

```
DRAFT --> Review --> Approval --> PRE_APPROVED --> Release
    --> IN_EXECUTION --> Execute CAPAs --> Post-Review --> CLOSED
```

### Pre-Approval Phase

During authoring and review, the INV establishes:
- The deviation description and impact
- The root cause analysis
- The planned CAPAs (as EIs in the execution block)

Reviewers evaluate whether the root cause analysis is sound and the CAPAs are adequate.

### Execution Phase

During execution, the initiator:
- Implements each CAPA
- Creates child CRs for changes requiring document control
- Records evidence of completion for each EI
- Documents any deviations from the planned CAPAs (via VARs if needed)

### Post-Review and Closure

Post-review verifies:
- All CAPAs were implemented
- Child CRs are closed or pre-approved as appropriate
- Evidence demonstrates the root cause has been addressed
- No scope was silently dropped

---

## Closure Criteria

An INV can be closed when ALL of the following are satisfied:

| Criterion | Description |
|-----------|-------------|
| All EIs executed | Every execution item has a recorded outcome (Pass or Fail with attached child document) |
| Child CRs resolved | All CAPA-implementing CRs are CLOSED or otherwise resolved |
| Evidence complete | Every EI has documented evidence |
| Root cause addressed | The corrective and preventive actions demonstrably address the identified root cause |
| Post-review approved | QA has approved the post-execution review |

---

## The Recursive Governance Connection

Investigations are the QMS's self-correction mechanism. When a process failure occurs:

1. The INV analyzes the failure
2. CAPAs identify improvements to the process
3. Child CRs implement those improvements (often as SOP updates)
4. The updated SOPs govern future work

This creates the recursive governance loop described in [01-Overview.md](01-Overview.md): the QMS uses its own document control mechanisms to improve itself. Every process failure becomes a traceable input to process improvement.

---

## Quick Reference: INV Workflow Commands

```bash
# Create an Investigation
qms create INV --title "CR-042 approved with empty Testing Summary"

# Check out, edit, check in
qms checkout INV-005
# ... populate deviation description, root cause, CAPAs ...
qms checkin INV-005

# Route for review and approval
qms route INV-005 --review
qms route INV-005 --approval

# Release for execution
qms release INV-005

# Execute CAPAs, then route for post-review
qms route INV-005 --review
qms route INV-005 --approval

# Close
qms close INV-005
```

See [12-CLI-Reference.md](12-CLI-Reference.md) for the full command reference.

---

## See Also

- [INV Reference](types/INV.md) -- Detailed INV template structure, CLI enforcement, and CAPA table format
- [04-Change-Control.md](04-Change-Control.md) -- CRs that implement CAPA fixes
- [07-Child-Documents.md](07-Child-Documents.md) -- VAR and ER for execution-time deviations
- [QMS-Policy.md](QMS-Policy.md) -- When to investigate (judgment criteria)

---

## Glossary References

Key terms used in this document: [INV](QMS-Glossary.md), [Deviation](QMS-Glossary.md), [Root Cause](QMS-Glossary.md), [CAPA](QMS-Glossary.md), [Corrective Action](QMS-Glossary.md), [Preventive Action](QMS-Glossary.md), [Procedural Deviation](QMS-Glossary.md), [Product Deviation](QMS-Glossary.md), [VAR](QMS-Glossary.md), [ER](QMS-Glossary.md).
