# Post-Review Checklist

Use this checklist before routing an executable document for post-review (`qms route {DOC_ID} --review` from IN_EXECUTION). A thorough pre-flight prevents rejection cycles.

---

## Pre-Flight: Universal Checklist

These apply to **all** executable documents (CR, INV, TP, ER, VAR, ADD).

### Execution Items

- [ ] **Every EI has a recorded outcome.** Each execution item must have `Pass` or `Fail` in the Task Outcome column. No blanks, no "N/A", no "Pending."
- [ ] **Every Pass EI has specific evidence.** Evidence must be traceable (commit hashes, CLI output, document references) and contemporaneous (recorded when work was done).
- [ ] **Every Fail EI has an attached child document.** A failed EI requires:
  - VAR for non-test executable documents (CR, INV, VAR, ADD)
  - ER for test protocol failures (TP)
- [ ] **All Type 1 VARs are CLOSED.** Type 1 VARs block parent closure. They must complete their full lifecycle before the parent can proceed.
- [ ] **All Type 2 VARs are at least PRE_APPROVED.** Type 2 VARs unblock the parent at pre-approval. They can complete their lifecycle after the parent closes, but must be at least PRE_APPROVED.
- [ ] **All child ERs are CLOSED.** Exception Reports must complete their re-execution and close before the parent TP can proceed.
- [ ] **All VR-flagged EIs have completed VR documents.** If an EI has `VR=Yes`, a VR child document must exist and be filled in (via `qms interact`). VRs close when the parent closes (cascade close), but they must have recorded evidence.

### Execution Documentation

- [ ] **Execution summary is complete.** Section 11 (or equivalent) provides a narrative of what was accomplished, any deviations encountered, and the final state.
- [ ] **Execution comments capture deviations and decisions.** Any decision made during execution that is not captured in an EI or child document should be recorded in the execution comments table.
- [ ] **revision_summary reflects post-execution state.** Update frontmatter to describe the execution completion (e.g., `"Execution complete - all EIs pass"`).

### Child Document Status

| Child Type | Required State for Parent Post-Review |
|------------|--------------------------------------|
| VAR (Type 1) | CLOSED |
| VAR (Type 2) | PRE_APPROVED (minimum) |
| TP | CLOSED |
| ER | CLOSED |
| VR | Evidence recorded (closes with parent) |

---

## Pre-Flight: Code CR Additions

These apply specifically to CRs that modify controlled code in SDLC-governed systems (e.g., your application, qms-cli).

### SDLC Documents

- [ ] **RS is EFFECTIVE.** If the CR adds or modifies requirements, the Requirements Specification must have been updated, reviewed, approved, and reached EFFECTIVE status. Check: `qms status RS-001`.
- [ ] **RTM is EFFECTIVE.** The Requirements Traceability Matrix must be updated with verification evidence for new/modified requirements and approved to EFFECTIVE. Check: `qms status RTM-001`.
- [ ] **RTM contains a real qualified commit hash.** The Qualified Baseline section must have an actual CI-verified commit hash -- not "TBD", not a placeholder, not a branch name. This is the specific commit at which all tests pass.

### Code Governance

- [ ] **Execution branch has been merged to main.** The merge must use a standard merge commit (no squash). Verify: the qualified commit from the execution branch is reachable from `main`.
- [ ] **Merge commit hash is recorded.** The EI for the merge step should record the merge commit hash as evidence.
- [ ] **Qualified commit is reachable from main.** After merge, verify: `git log main --oneline | grep {qualified_commit_short}` shows the commit. If a squash merge was used (prohibited), the original commit hash will not be reachable.
- [ ] **Submodule pointer updated.** If the CR modifies a governed submodule, the submodule reference in the parent project must be updated to point to the post-merge state.
- [ ] **All tests pass at the qualified commit.** CI must have verified the test suite at the specific commit hash recorded in the RTM.

---

## Common Post-Review Rejection Reasons

Learn from previous rejections. These are the most common reasons QA rejects during post-review, and how to prevent them.

### 1. Missing or Incomplete Evidence

| Problem | Prevention |
|---------|-----------|
| EI evidence says "Tests pass" | Be specific: "pytest: 42 passed, 0 failed at commit abc1234" |
| EI evidence says "Done" | Describe what was done and link to the artifact (commit, document, screenshot) |
| Evidence recorded after the fact | Record evidence at execution time. Use engine-managed commits for VRs. |
| Commit hash not included | Always include the short hash and a brief description of what the commit contains |

### 2. Scope Integrity Violations

| Problem | Prevention |
|---------|-----------|
| An EI has no outcome recorded | Every EI must be Pass or Fail. No exceptions. |
| A planned EI was skipped without documentation | If an EI is no longer applicable, mark it Fail and create a VAR explaining why. |
| Work was done that is not in any EI | All execution work must be traceable to an approved EI. If scope grew, use a VAR. |
| Scope was dropped without a VAR | A Fail outcome without a child document is a scope integrity violation. |

### 3. Child Document Issues

| Problem | Prevention |
|---------|-----------|
| Type 1 VAR not CLOSED | Complete the full VAR lifecycle before routing parent for post-review |
| Type 2 VAR not yet PRE_APPROVED | VAR must at minimum reach pre-approval before parent can proceed |
| VR exists but has no evidence recorded | Complete the VR via `qms interact` before routing parent |
| ER not CLOSED | Complete re-execution and close the ER |

### 4. SDLC Document Gaps (Code CRs)

| Problem | Prevention |
|---------|-----------|
| RS not EFFECTIVE | Route RS through review/approval before routing the CR for post-review |
| RTM not EFFECTIVE | Route RTM through review/approval before routing the CR for post-review |
| RTM qualified baseline says "TBD" | Run CI, confirm tests pass, record the actual commit hash in the RTM |
| Execution branch not merged | Complete the merge gate (all tests pass + RS EFFECTIVE + RTM EFFECTIVE) before routing |
| Squash merge used | Prohibited. Re-merge using a standard merge commit. The original commit hashes must be reachable from main. |

### 5. Documentation Gaps

| Problem | Prevention |
|---------|-----------|
| Execution summary empty or boilerplate | Write a genuine narrative: what was done, what was encountered, what is the final state |
| No execution comments for decisions made during execution | Document any deviation from plan, tooling issue, or judgment call in the comments table |
| revision_summary not updated | Update frontmatter before final checkin |

---

## What Post-Reviewers Verify

Post-review is not just reading. Reviewers are verifying that the execution matches the approved plan. Here is what they check:

### QA Post-Review Focus

| Verification | Method |
|-------------|--------|
| **All EIs have outcomes** | Read the EI table; every row must have Pass or Fail |
| **Evidence is traceable** | For each EI, can they follow the evidence back to a source? (e.g., verify commit exists, document is EFFECTIVE) |
| **Scope integrity** | Compare approved EI list (static, from pre-approval) against recorded outcomes -- nothing dropped, nothing added without a VAR |
| **Child documents in correct states** | Check `qms status` for each child document |
| **Execution summary is accurate** | Does the summary match what the EI table shows? |

### TU Post-Review Focus

| Verification | Method |
|-------------|--------|
| **Code changes match the plan** | Diff the execution branch against main; changes should align with the CR scope |
| **Technical approach is sound** | The actual implementation should follow the proposed approach (or deviations should be documented in VARs) |
| **Test coverage is adequate** | Verification evidence (unit tests, VRs, qualitative proofs) covers the modified behavior |

### Key Difference: Pre-Review vs. Post-Review

| Pre-Review | Post-Review |
|-----------|------------|
| "Is the plan correct?" | "Was the plan executed correctly?" |
| Reviews sections 1-9 (proposed changes) | Reviews sections 10-12 (actual execution) |
| Checks for completeness of planning | Checks for completeness of evidence |
| "Would this approach work?" | "Did this approach work? Prove it." |

---

## Quick Reference: Post-Review Routing Commands

```bash
# Check all child document statuses
qms status {CHILD_DOC_ID}            # Repeat for each child

# Final checkin before routing
qms checkin {DOC_ID}                  # Or let auto-checkin handle it

# Route for post-review
qms route {DOC_ID} --review           # CLI infers post-review from IN_EXECUTION status

# If rejected: address feedback, then re-route
qms checkout {DOC_ID}                 # Returns to IN_EXECUTION
# ... fix issues ...
qms route {DOC_ID} --review           # Re-submit for post-review

# After post-review approval
qms route {DOC_ID} --approval         # Route for post-approval
# ... QA approves ...
qms close {DOC_ID}                    # Terminal state
```

---

## See Also

- [Review Guide](review-guide.md) -- General review process guidance
- [Routing Quick Reference](routing-quickref.md) -- Status transitions and routing mechanics
- [Execution](../06-Execution.md) -- EI table format, evidence requirements, scope integrity
- [Child Documents](../07-Child-Documents.md) -- VAR, ER, ADD, VR details
- [Code Governance](../09-Code-Governance.md) -- Merge gate, qualified commits
- [SDLC](../10-SDLC.md) -- RS, RTM, and qualification
- [QMS-Glossary](../QMS-Glossary.md) -- Term definitions
