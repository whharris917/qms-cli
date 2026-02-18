---
title: '{{TITLE}}'
revision_summary: 'Initial draft'
---

<!--
================================================================================
TEMPLATE USAGE GUIDE
================================================================================

DOCUMENT TYPE:
VRs are EXECUTABLE documents that are BORN IN_EXECUTION at v1.0.
The approved VR template serves as the pre-approval authority (batch record
model). VRs skip the DRAFT through PRE_APPROVED phases entirely.

From IN_EXECUTION onward, VRs follow the standard executable post-execution
workflow: post-review, post-approval, and closure.

CONCEPT:
A Verification Record (VR) is a lightweight child document that provides
structured, auditor-ready evidence of behavioral verification. VRs are the
primary mechanism for documenting unscripted integration testing.

VRs are the pinnacle of proof: what you show an auditor who asks
"demonstrate that CR-XYZ-EI-N passed."

EVIDENCE STANDARDS:
- Evidence must be OBSERVATIONAL: what was done, what was observed
- Evidence must NOT be ASSERTIONAL: "ad hoc test printed PASS" is insufficient
- Evidence must be CONTEMPORANEOUS: recorded at the time of testing
- Evidence must be REPRODUCIBLE: a Verifier with terminal access but no project
  background knowledge should be able to follow the procedure and confirm
  matching results

SCOPE GUIDANCE:
VR objectives should describe the CAPABILITY being verified, not the specific
mechanism. Default to forest-level scope:
  GOOD:  "Verify service health monitoring works correctly"
  AVOID: "Verify the health check endpoint returns 200"

The broader framing naturally leads the Performer to check adjacent behavior.
Narrow, surgical scope should be the exception, not the default.

WORKFLOW:
  create (IN_EXECUTION v1.0, checked out) -> fill in -> checkin
  -> route post-review -> QA review -> route post-approval -> QA approve
  -> close

VR ID FORMAT:
  {PARENT_DOC_ID}-VR-NNN
  Examples:
    CR-089-VR-001 (verification for a CR)
    CR-089-VAR-001-VR-001 (verification for a VAR)
    CR-089-ADD-001-VR-001 (verification for an ADD)

SIGNATURE TYPES (per SOP-004):
- Performer: Fills in the VR contemporaneously during testing
- Reviewer: QA evaluates the completed VR during parent post-review
- Verifier: (future) Independently reproduces the procedure to confirm results

WHEN TO CREATE A VR:
VRs are created for execution items flagged with "Yes" in the VR column
of the parent document's EI table. The VR column is set during planning
(static field) and the VR ID is recorded during execution (editable field).

HOW TO FILL IN A VR:
1. Set up: Fill in Sections 1-3 (identification, objective, pre-conditions)
2. Prepare: Establish the pre-conditions described in Section 3
3. Execute: Perform the verification, recording procedure and observations
   in Sections 4-5 AS YOU GO -- do not backfill after the fact
4. Assess: Record outcome in Section 6, including negative verification
5. Sign: Record signature in Section 7

Delete this comment block after reading.
================================================================================
-->

# {{VR_ID}}: {{TITLE}}

## 1. Verification Identification

| Parent Document | Related EI(s) | Date |
|-----------------|---------------|------|
| [PARENT_DOC_ID] | [EI-N] | [DATE] |

---

## 2. Verification Objective

<!--
NOTE: Do NOT delete this comment. It provides guidance during execution.

State what CAPABILITY is being verified -- not what specific mechanism is
being tested. The objective should be broad enough that the Performer
naturally checks adjacent behavior.

GOOD:  "Verify that the unified logging system produces consistent,
        readable output across all services"
AVOID: "Verify that git_mcp/server.py line 42 uses the new log format"
-->

**Objective:** [OBJECTIVE -- What capability is being verified?]

**Expected Outcome:** [EXPECTED -- What does success look like? Describe in observable terms.]

---

## 3. Pre-Conditions

<!--
NOTE: Do NOT delete this comment. It provides guidance during execution.

Record the state of the system BEFORE verification begins. A Verifier must
be able to reproduce these conditions to repeat the verification.

Include as applicable:
- Branch and commit checked out
- Services running (which ones, which ports)
- Container state (image version, running/stopped)
- Configuration (any non-default settings)
- Data state (clean database, seeded data, etc.)
- Environment (OS, Python version, other relevant tools)
-->

| Pre-Condition | State |
|---------------|-------|
| [CONDITION] | [STATE] |
| [CONDITION] | [STATE] |
| [CONDITION] | [STATE] |

---

## 4. Procedure

<!--
NOTE: Do NOT delete this comment. It provides guidance during execution.

Record what you DID, step by step, AS YOU DO IT. Do not summarize after
the fact. Include:
- Exact commands run (copy-paste, not paraphrase)
- Actions taken in GUIs (click X, navigate to Y)
- Order of operations
- Any deviations from what you initially planned

The procedure must be detailed enough that a Verifier who knows how to
operate a terminal -- but does not know this project's architecture -- could
follow these steps and arrive at the same observations.
-->

| Step | Action | Detail |
|------|--------|--------|
| 1 | [ACTION] | [EXACT COMMAND OR DESCRIPTION] |
| 2 | [ACTION] | [EXACT COMMAND OR DESCRIPTION] |
| 3 | [ACTION] | [EXACT COMMAND OR DESCRIPTION] |

<!--
NOTE: Do NOT delete this comment. It provides guidance during execution.

Add rows as needed. Prefer more granularity over less -- it is better to
record too many steps than too few.
-->

---

## 5. Observations

<!--
NOTE: Do NOT delete this comment. It provides guidance during execution.

Record what you OBSERVED at each step. Include:
- Actual terminal output (copy-paste relevant portions)
- Log file contents (excerpt the relevant lines)
- System behavior (what happened visually, what changed)
- Anything unexpected, even if it doesn't affect the outcome

Do NOT paraphrase output. Copy-paste the actual text. The Reviewer must
be able to evaluate the evidence on its own merits without having been
present during testing.
-->

### Step 1: [ACTION REFERENCE]

**Observed:**

```
[PASTE ACTUAL OUTPUT HERE]
```

### Step 2: [ACTION REFERENCE]

**Observed:**

```
[PASTE ACTUAL OUTPUT HERE]
```

### Step 3: [ACTION REFERENCE]

**Observed:**

```
[PASTE ACTUAL OUTPUT HERE]
```

<!--
NOTE: Do NOT delete this comment. It provides guidance during execution.

Add sections as needed, one per procedure step that produced observable
output. Steps with no meaningful output may be omitted or noted briefly.
-->

---

## 6. Outcome

### 6.1 Positive Verification

<!--
NOTE: Do NOT delete this comment. It provides guidance during execution.

Does the observed behavior match the expected outcome stated in Section 2?
-->

| Expected Outcome | Actual Outcome | Match? |
|-----------------|----------------|--------|
| [FROM SECTION 2] | [WHAT WAS ACTUALLY OBSERVED] | [Yes/No] |

### 6.2 Negative Verification

<!--
NOTE: Do NOT delete this comment. It provides guidance during execution.

What should NOT have happened? Verify it didn't. This section catches
side effects, regressions, and unintended consequences.

If not applicable for this VR, write "N/A -- no negative conditions identified"
and delete the table.
-->

| Condition | Should NOT Occur | Occurred? |
|-----------|-----------------|-----------|
| [CONDITION] | [UNDESIRED BEHAVIOR] | [Yes/No] |

### 6.3 Overall Outcome

**Outcome:** [Pass / Fail]

<!--
NOTE: Do NOT delete this comment. It provides guidance during execution.

- Pass: Observed behavior matches expected outcome AND no negative
  conditions occurred
- Fail: Observed behavior does not match expected outcome, OR a negative
  condition occurred. If Fail, note which section contains the discrepancy
  and reference any VAR created to address it.
-->

[If Fail: Brief explanation and VAR reference if applicable]

---

## 7. Signature

| Role | Identity | Date |
|------|----------|------|
| Performed By | [PERFORMER] | [DATE] |

<!--
NOTE: Do NOT delete this comment. It provides guidance during execution.

The Performer signature attests: "I performed these steps, observed these
results, and recorded them contemporaneously."

Additional signature rows may be added if a Witness or Verifier participated:

| Witnessed By | [WITNESS] | [DATE] |
| Verified By  | [VERIFIER] | [DATE] |
-->

---

## 8. References

- **{{PARENT_DOC_ID}}:** Parent document
- **SOP-004:** Document Execution

---

**END OF VERIFICATION RECORD**
