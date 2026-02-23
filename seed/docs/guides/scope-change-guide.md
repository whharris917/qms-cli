# Scope Change Guide

How to handle situations where the approved scope does not match what needs to happen during execution. This guide covers the scope integrity principle and the formal mechanisms for dealing with scope mismatches.

---

## The Scope Integrity Principle

**Approved scope cannot be silently dropped.**

Every static EI that was approved must have a documented outcome. The only two valid outcomes are:

| Outcome | Meaning |
|---------|---------|
| **Pass** | The task was completed as described |
| **Fail** | The task could not be completed as described; a child document (VAR or ER) explains why |

There is no "Skip," no "N/A," no "Deferred," and no "Removed." If an EI exists in the approved plan, it must be resolved through one of these two paths.

**Why this matters:** The pre-approval process exists so that reviewers and approvers can evaluate the plan. If scope can be silently dropped during execution, the approval becomes meaningless. The scope integrity principle ensures that any deviation from the approved plan is visible, documented, and reviewed.

---

## Scenario: EI Is Unnecessary

**Situation:** During execution, you discover that an approved EI does not need to be done. Perhaps the problem it was meant to solve was already fixed by a previous EI, or the underlying assumption turned out to be wrong.

**What you cannot do:**
- Delete the EI from the table
- Leave it blank
- Mark it as "N/A" or "Skipped"
- Mark it as Pass without actually doing the work

**What you must do:**

1. Mark the EI as **Fail**
2. In Actual Outcome: Explain why the task is unnecessary
3. Create a **VAR** (typically Type 2) documenting:
   - The variance: "EI-N is no longer applicable because [reason]"
   - Impact assessment: Confirm that skipping this EI does not affect the CR's objectives
   - Resolution: "No action required; the work is unnecessary because [reason]"
4. Reference the VAR in the EI's Evidence column

**Example:**

```markdown
| EI-4 | Update config.py with new timeout value | config.py reflects 30s timeout | EI-2 already set timeout to 30s as part of the broader refactor; this EI is redundant | See CR-045-VAR-001 | Fail | claude | 2026-02-15 |
```

**The VAR can be lightweight.** A Type 2 VAR with a one-paragraph description and a single EI ("Confirm no impact from skipping parent EI-4") is sufficient. The point is traceability, not bureaucracy.

---

## Scenario: Additional Work Discovered

**Situation:** During execution, you discover that additional work is needed beyond what was approved. Maybe a new dependency was found, or the implementation revealed a secondary change requirement.

**What you cannot do:**
- Add new EIs to the parent document's approved EI table
- Perform the extra work without documenting it
- Claim an existing EI covers work it was not designed for

**What you must do:**

The path depends on what the additional work is:

### If the work is closely related to an existing EI's objectives

Create a **VAR** on the parent document. The VAR's resolution plan includes the additional work as its own EI table. The parent EI can still pass if its literal scope was completed, with the VAR handling the discovered extra work.

### If the work is independent or substantial

Create a **new CR** for the additional work. Reference it in the parent's Execution Comments table:

```markdown
| Comment | Performed By -- Date |
|---------|---------------------|
| During EI-3 implementation, discovered that the input handler also needs updating. Out of scope for this CR. Created CR-046 to address. | claude -- 2026-02-15 |
```

### Decision aid

| Extra work... | Mechanism |
|---------------|-----------|
| Is a direct consequence of an EI failure | VAR on the current document |
| Supports the current CR's objectives but was not planned | VAR on the current document |
| Is independent of the current CR's objectives | New CR |
| Is large enough to warrant its own review/approval | New CR |
| Affects systems outside the current CR's scope | New CR |

---

## Scenario: EI Was Written Incorrectly (Intent Is Correct)

**Situation:** The EI description contains an error (wrong file name, incorrect function reference, typo in a value), but the *intent* of the EI is clear and correct.

**What you cannot do:**
- Edit the static EI description (it is locked after approval)
- Pretend the error does not exist

**What you must do:**

Execute the EI according to its **correct intent**, and document the discrepancy:

1. In Actual Outcome: Note the error and what you did instead
2. Create a **VAR** (Type 2) documenting:
   - The authoring error in the EI description
   - Confirmation that the intent was executed correctly
   - That this is a documentation error, not a scope deviation
3. Mark the EI as **Fail** (because the literal description was not followed)
4. Reference the VAR

**Example:**

```markdown
| EI-3 | Update auth_handler.py with new validator | File updated with validator | EI description references "auth_handler.py" (singular) but the actual file is "auth_handlers.py" (plural). Updated the correct file per design intent. | See CR-045-VAR-001 (Type 2, documentation error) | Fail | claude | 2026-02-15 |
```

**Note on proportionality:** Yes, creating a VAR for a typo feels heavy. But the alternative -- silently executing something different from what was approved -- undermines the approval process. The VAR is lightweight (Type 2, minimal content) and provides the traceability that makes the system work.

---

## Scenario: EI Was Written Incorrectly and Intent Was Wrong

**Situation:** The EI description is wrong *and* the intended approach is wrong. The approved plan needs genuine correction.

**What you must do:**

1. **Stop execution** of the affected EI
2. Mark the EI as **Fail** with an explanation in Actual Outcome
3. Create a **VAR** (likely Type 1) documenting:
   - What was wrong with the EI
   - Why the original intent was incorrect
   - The correct approach (as the VAR's resolution plan)
   - Impact on other EIs in the parent
4. The VAR goes through full pre-review and pre-approval to validate the corrected approach
5. Execute the correct approach under the VAR
6. Close the VAR before (Type 1) or alongside (Type 2) the parent

**Why Type 1 is likely:** If the original intent was wrong, the correction is probably a prerequisite for the parent's objectives. The reviewers who approved the original plan should see the revised approach before it is executed.

---

## Scenario: Scope Is Too Broad

**Situation:** The approved scope includes work that is no longer needed, or work that should be done under a different CR. You want to reduce the scope.

**What you cannot do:**
- Remove EIs from the approved plan
- Mark EIs as Pass without doing them
- Defer EIs without formal documentation

**What you must do:**

For each EI you want to drop, follow the "EI Is Unnecessary" scenario above. Each dropped EI gets a Fail outcome and a VAR explaining why it is being dropped.

**If multiple EIs are being dropped for the same reason**, a single VAR can cover all of them:

```markdown
VAR Title: "EIs 5-7 unnecessary after EI-2 refactoring"

Variance Description:
EIs 5, 6, and 7 were planned as incremental updates to the service configuration.
EI-2's implementation resolved the underlying issue comprehensively, making
these incremental steps unnecessary.

Resolution: No action required. Confirmed that the CR's objectives are fully
met by EIs 1-4.
```

---

## Scenario: Scope Is Too Narrow

**Situation:** The approved scope does not include work that is necessary to achieve the CR's stated objectives.

**What you must do:**

This is the "Additional Work Discovered" scenario. The mechanism depends on the nature of the additional work:

| If the missing work... | Use |
|------------------------|-----|
| Is a prerequisite for an existing EI | VAR (Type 1) with resolution EIs covering the missing work |
| Supports the CR objectives but is independent | VAR (Type 2) or new CR |
| Is entirely outside the CR's stated purpose | New CR |

**The parent's objectives cannot expand.** If the additional work changes the Purpose or Scope sections of the CR, that is not a VAR -- that is a fundamental scope change that may require withdrawing and revising the CR, or creating a new CR.

---

## The "Different Execution Mechanism" Rule

Sometimes the approved EI says "do X" but during execution you discover that the correct way to achieve the EI's goal is to "do Y" instead. The outcome is the same, but the mechanism is different.

**Examples:**
- EI says "update config.py" but the setting was moved to `settings.json`
- EI says "add a unit test" but integration test coverage already exists and is more appropriate
- EI says "modify function `solve()`" but the function was renamed to `resolve()` in a prior EI

**The rule:** If the mechanism changes but the outcome matches the Expected Outcome, this is still a VAR situation. You executed something different from what was approved, even if the result is equivalent.

**However**, the VAR can be Type 2 and lightweight:
- Variance description: "Mechanism changed from X to Y; outcome is equivalent"
- Impact assessment: "None -- the CR objective is achieved"
- Resolution: "Executed via mechanism Y. Result matches Expected Outcome."

**Do not mark the EI as Pass** just because the outcome looks right. The static description was not followed, so the outcome is Fail with an attached VAR. The VAR documents that the deviation was intentional, understood, and equivalent.

---

## Minimizing Bureaucracy Without Sacrificing Integrity

Scope changes create overhead. Here is how to keep it proportional:

### Batch Related Deviations

If multiple EIs are affected by the same root cause, create one VAR that covers all of them. Do not create a separate VAR per EI.

### Use Type 2 for Non-Blocking Issues

Type 2 VARs unblock the parent quickly. If the deviation does not affect the parent's ability to close, Type 2 is almost always correct.

### Keep VAR Content Minimal When Appropriate

A VAR for a typo in an EI description does not need a multi-page root cause analysis. One paragraph each for description, impact, and resolution is sufficient.

### Front-Load Quality in EI Design

The best way to avoid scope change overhead is to write good EIs during authoring:
- Be specific but not brittle (reference concepts, not just file names)
- Include enough context that the intent is clear even if details change
- Flag known uncertainties in the Implementation Plan narrative

### Document Scope Deviations in Execution Comments

Minor observations that do not rise to VAR level (but are worth noting) go in the Execution Comments table:

```markdown
| Comment | Performed By -- Date |
|---------|---------------------|
| EI-3 references "Section 5" but the relevant content is in Section 4 after the reorganization in EI-1. Executed per correct section. No functional impact. | claude -- 2026-02-15 |
```

**Important:** This is for *observations*, not for scope deviations. If the EI's static description does not match what was executed, a VAR is required regardless of how minor the discrepancy seems. The Execution Comments table is supplementary context, not a substitute for formal deviation handling.

---

## Decision Summary

| Situation | Action | Document Type |
|-----------|--------|---------------|
| EI is unnecessary | Fail + explain | VAR (Type 2) |
| Extra work needed (related) | Add to child | VAR |
| Extra work needed (independent) | Separate track | New CR |
| EI description wrong, intent right | Execute intent, document discrepancy | VAR (Type 2) |
| EI description wrong, intent wrong | Stop, reassess | VAR (Type 1) |
| Want to drop EIs | Fail each + explain | VAR (one VAR can cover multiple EIs) |
| Need to add EIs | Cannot add to parent | VAR or new CR |
| Mechanism changed, outcome same | Fail + explain equivalence | VAR (Type 2) |

---

**See also:**
- [Execution Policy](../06-Execution.md) -- Scope integrity principle, EI table structure
- [Failure Decision Guide](failure-decision-guide.md) -- When the issue is a failure, not a scope change
- [Child Documents](../07-Child-Documents.md) -- VAR, ADD, ER lifecycle details
- [VAR Reference](../types/VAR.md) -- VAR template structure and Type 1/Type 2 details
- [QMS-Policy](../QMS-Policy.md) -- Governing policy
- [QMS-Glossary](../QMS-Glossary.md) -- Term definitions
