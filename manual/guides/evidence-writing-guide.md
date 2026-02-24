# Evidence Writing Guide

How to write execution evidence that will pass review. This guide is for anyone filling in EI editable fields during document execution.

---

## The Third-Party Reviewer Test

Before recording evidence, ask yourself:

> Could someone who was not present during execution -- and has no prior knowledge of this project -- read this evidence and verify that the work was completed?

If the answer is no, your evidence is insufficient. The reviewer should never have to ask "but how do I know this actually happened?" Good evidence answers that question before it is asked.

---

## Evidence by EI Type

### Code Changes

**What the reviewer needs:** Which code changed, what the change does, and proof it was committed.

| Quality | Example |
|---------|---------|
| Bad | "Updated the auth module" |
| Bad | "Committed changes to my-app" |
| Acceptable | "Commit `abc1234`: Added `validate_token()` to `auth.py`" |
| Good | "Commit `abc1234`: Added `validate_token()` function to `auth.py` implementing JWT validation per Section 4 design. Also updated `middleware.py` to register the new validator in the request pipeline." |

**Minimum requirements:**
- Commit hash (short form `abc1234` is fine)
- Which files were modified
- What the modification does (not just "updated" or "changed")

**For multi-file changes**, group logically:

```
Commit abc1234:
- auth.py: Added validate_token() function
- middleware.py: Registered new validator in request pipeline
- config.py: Added TOKEN_EXPIRY_SECONDS constant (3600)
```

### Document Updates

**What the reviewer needs:** Which document, which version, and what changed.

| Quality | Example |
|---------|---------|
| Bad | "Updated the SOP" |
| Acceptable | "SOP-002 updated to v2.0" |
| Good | "SOP-002 v2.0 EFFECTIVE: Added reviewer pre-approval checklist (Section 4.3) per INV-005-CAPA-001. New checklist contains 8 verification items covering section completeness, placeholder resolution, and scope consistency." |

**Minimum requirements:**
- Document ID and version number
- Document status (EFFECTIVE, DRAFT, etc.)
- Summary of what was modified

### Configuration Changes

**What the reviewer needs:** The before state, the after state, and why it changed.

| Quality | Example |
|---------|---------|
| Bad | "Updated config" |
| Acceptable | "Set MAX_RETRIES to 5 in config.py" |
| Good | "config.py: Changed `MAX_RETRIES` from 3 to 5 to accommodate increased timeout frequency after connection pooling was added. Before: `MAX_RETRIES = 3`. After: `MAX_RETRIES = 5`. Commit `def5678`." |

**Minimum requirements:**
- Configuration file or location
- Previous value (before)
- New value (after)
- Commit hash if the change is in code

### VR-Flagged Items

When an EI has `VR=Yes`, the VR document contains the detailed evidence. The EI evidence column should reference the VR, not duplicate its contents.

| Quality | Example |
|---------|---------|
| Bad | "Verified the feature works" (no VR reference) |
| Bad | (Copying full VR test output into the EI) |
| Good | "See CR-042-VR-001 (CLOSED, Pass). VR verified dropdown rendering, click handling, and keyboard navigation across 4 verification steps." |

**The rule:** Point to the VR. Summarize the outcome. Do not duplicate the VR content in the EI table.

### Branch/Repository Operations

| Quality | Example |
|---------|---------|
| Bad | "Created the branch" |
| Good | "Branch `cr-045/exec` created from `main@abc1234`. Verified: `git log --oneline -1` shows `abc1234 Update project state document...`" |

### QMS Workflow Actions

| Quality | Example |
|---------|---------|
| Bad | "Routed for review" |
| Good | "VAR-001 routed for pre-review. `qms status CR-045-VAR-001` confirms IN_PRE_REVIEW, v0.1, assignees: [qa]." |

---

## Common Evidence Pitfalls

### 1. Assertional Language

**The problem:** Stating that something is true without showing it.

| Assertional (bad) | Observational (good) |
|-------------------|---------------------|
| "Tests pass" | "pytest output: 42 passed, 0 failed (commit abc1234)" |
| "The widget renders correctly" | "Screenshot shows dropdown at (120, 45) with 3 menu items visible" |
| "No regressions observed" | "Full test suite: 142 passed, 0 failed, 0 skipped. Diff from baseline: +2 new tests, 0 removed." |
| "The fix works" | "Reproduced original failure scenario. After applying commit def5678, request handler completes in 200ms (previously timed out at 30s+)." |

**The test:** If you can write the sentence *without having done the work*, it is assertional. Evidence must contain information that could only come from actually performing the task.

### 2. Missing Artifacts

**The problem:** Describing what was done but not providing the traceable artifact.

| Missing artifact (bad) | With artifact (good) |
|------------------------|---------------------|
| "Committed the fix" | "Commit `abc1234`: Fixed off-by-one in pagination loop" |
| "Updated the document" | "SOP-002 v2.0 EFFECTIVE, Section 4.3 added" |
| "Test passed" | "CI run #147: all green. Log: [link or paste of summary]" |

**The rule:** Every evidence statement must include at least one traceable artifact -- a commit hash, document version, CLI output, or screenshot.

### 3. Post-Hoc Reconstruction

**The problem:** Writing evidence after the fact from memory instead of recording it when the work is done.

**How to avoid it:**
- Record evidence immediately after completing each EI
- Copy-paste actual terminal output, do not paraphrase from memory
- If you forgot to capture output, re-run the verification command and note that it is a re-verification
- Use [engine-managed commits](../08-Interactive-Authoring.md) for VR evidence -- these pin the exact project state at observation time

**Why it matters:** Reconstructed evidence is less reliable. Timestamps will not match the actual work. Details will be approximate. A reviewer cannot distinguish "I verified this at 2pm" from "I think I verified this at 2pm."

### 4. Vague Scope References

| Vague (bad) | Specific (good) |
|-------------|----------------|
| "Updated several files" | "Modified `auth.py`, `middleware.py`, and `config.py`" |
| "Per the design" | "Per Section 4 of CR-042 (Proposed State)" |
| "As discussed" | "Per Lead decision during EI-2 execution (see Execution Comments)" |

---

## Execution Summary vs. Evidence Artifacts

These are two different things that serve two different purposes.

### Evidence Artifacts (EI Table: Evidence Column)

Traceable, verifiable proof that a specific task was completed. Answers: **"What proves this was done?"**

```
Commit abc1234: Added validate_token() function to auth.py
```

### Execution Summary (Narrative Section)

A narrative overview of the entire execution phase. Answers: **"What happened during execution, and what is the final state?"**

```
Execution proceeded per plan. EI-1 through EI-4 completed without deviation.
EI-5 encountered an unexpected test regression requiring VAR-001 (Type 2).
The VAR was pre-approved and will be resolved separately.
Final code state: commit ghi7890 on branch cr-045/exec.
All 5 EIs executed: 4 Pass, 1 Fail (with attached VAR-001).
```

**Do not confuse them.** The execution summary is not a replacement for per-EI evidence. The evidence column must stand on its own -- the summary provides context but is not the proof.

---

## Multi-Commit EIs

When a single EI spans multiple commits (common for implementation tasks), document all of them.

### Option A: List All Commits

```
Evidence:
- Commit abc1234: Added validation function
- Commit def5678: Registered validator in request pipeline
- Commit ghi9012: Added unit tests (3 tests, all passing)
```

### Option B: Range With Summary

```
Evidence:
Commits abc1234..ghi9012 (3 commits):
- Added validate_token() function and pipeline registration
- Added 3 unit tests covering edge cases
Final state verified at ghi9012.
```

### Option C: Single Squash Reference

If commits were squashed before recording evidence:

```
Evidence:
Commit jkl3456 (squashed from 3 development commits):
Token validation implementation including function, pipeline registration, and tests.
```

**Preference order:** Option A (most traceable) > Option B (acceptable) > Option C (acceptable if squash happened).

---

## Model EI Execution

Here is a complete, well-evidenced EI table entry:

```markdown
| EI # | Task Description | Expected Outcome | Actual Outcome | Evidence | Outcome | By | Date |
|------|-----------------|------------------|----------------|----------|---------|----|------|
| EI-3 | Implement token validation per Section 4 design | Auth module validates JWT tokens within 200ms latency budget | Token validation working correctly. Auth module validates tokens in 45ms average across 100-request benchmark. | Commit abc1234: Added `validate_token()` to `auth.py` (validation implementation) and `middleware.py` (pipeline registration). Commit def5678: Added 3 unit tests to `test_auth.py` -- all passing. Config: `TOKEN_EXPIRY_SECONDS = 3600` added to `config.py`. | Pass | claude | 2026-02-15 |
```

**What makes this good:**
1. Actual Outcome is specific and measurable (45ms average, 100-request benchmark)
2. Evidence names every modified file and what changed in each
3. Two commit hashes provide full traceability
4. Test results are included (3 tests, all passing)
5. Configuration change is documented with the actual value

---

## Quick Checklist

Before marking an EI complete, verify:

- [ ] Evidence contains at least one traceable artifact (commit hash, document version, CLI output)
- [ ] Evidence is specific enough to pass the third-party reviewer test
- [ ] No assertional language without backing observations
- [ ] VR-flagged items reference the VR document, not duplicate its content
- [ ] Multi-commit work lists all relevant commits
- [ ] Configuration changes include before/after values
- [ ] Evidence was recorded at execution time, not reconstructed later

---

**See also:**
- [Execution Policy](../06-Execution.md) -- EI table structure, evidence requirements, scope integrity
- [VR Authoring Guide](vr-authoring-guide.md) -- Evidence standards specific to Verification Records
- [Failure Decision Guide](failure-decision-guide.md) -- What to record when an EI fails
- [QMS-Glossary](../QMS-Glossary.md) -- Term definitions
