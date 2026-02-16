---
title: Change Record Template
revision_summary: 'CR-086: Update execution instructions with pre/post-execution commit
  guidance and fix repository language'
---

<!--
================================================================================
TEMPLATE DOCUMENT NOTICE
================================================================================
This template is a QMS-controlled document. The frontmatter contains only:
- title: Document title
- revision_summary: Description of changes in this revision

All other metadata (version, status, responsible_user, dates) is managed
automatically by the QMS CLI in sidecar files (.meta/) per SOP-001 Section 5.

When creating a CR from this template, copy from the EXAMPLE FRONTMATTER onward.
================================================================================
-->

---
title: '{{TITLE}}'
revision_summary: 'Initial draft'
---

<!--
================================================================================
TEMPLATE USAGE GUIDE
================================================================================

DOCUMENT TYPE:
CRs are EXECUTABLE documents that authorize implementation activities.

WORKFLOW:
  DRAFT -> IN_PRE_REVIEW -> PRE_REVIEWED -> IN_PRE_APPROVAL -> PRE_APPROVED
       -> IN_EXECUTION -> IN_POST_REVIEW -> POST_REVIEWED -> IN_POST_APPROVAL
       -> POST_APPROVED -> CLOSED

PLACEHOLDER TYPES:
1. {{DOUBLE_CURLY}} - Replace when DRAFTING (before routing for review)
2. [SQUARE_BRACKETS] - Replace during EXECUTION (after release)

After authoring:
- NO {{...}} placeholders should remain
- All [...] placeholders should remain until execution

Authors may define additional execution placeholders as needed. Use square
brackets for any field that must be filled during execution.

ID FORMAT:
  CR-NNN
  Example: CR-001, CR-015

LOCKED vs EDITABLE:
- Sections 1-9 are locked after pre-approval
- Sections 10-12 are editable during execution
- Section 13 may be updated to add references discovered during execution

STRUCTURE (per SOP-002 Section 6):
Pre-Approved Content (locked after pre-approval):
  1. Purpose
  2. Scope (Context, Changes Summary, Files Affected)
  3. Current State
  4. Proposed State
  5. Change Description
  6. Justification
  7. Impact Assessment
  8. Testing Summary
  9. Implementation Plan

Execution Content (editable during execution):
  10. Execution (EI table, comments)
  11. Execution Summary
  12. References

CODE CR PATTERNS:
When a CR modifies controlled code (any system with SDLC governance):
- Include Section 7.4 (Development Controls) and 7.5 (Qualified State Continuity)
- Use the standardized implementation phases in Section 9
- RS and RTM must be EFFECTIVE before merging to main (SOP-006 Section 7.4)
- The qualified commit is the execution branch commit verified by CI (SOP-005 Section 7.1.2)
- RTM must reference this execution branch commit hash -- not the merge commit
- Merge type: regular merge commit (--no-ff). Squash merges are prohibited (SOP-005 Section 7.1.3)
- Qualification happens on the execution branch; main stays qualified throughout
- Integration verification is required before merge (SOP-002 Section 6.8): exercise
  changed functionality through user-facing levers to demonstrate it works

The pattern ensures:
- main branch is always in a qualified state
- No code merges without approved requirements and passing tests
- Changed functionality is verified in a running system, not only via automated tests
- The qualified commit hash in the RTM is reachable on main via merge commit
- Full traceability from requirements to verified implementation

Delete this comment block after reading.
================================================================================
-->

# CR-XXX: {{TITLE}}

## 1. Purpose

{{PURPOSE - What problem does this CR solve? What improvement does it introduce?}}

---

## 2. Scope

### 2.1 Context

{{CONTEXT - Reference parent investigation, CAPA, or driving document. If none, state the origin of this change (e.g., "Independent improvement identified during development" or "User-requested enhancement").}}

- **Parent Document:** {{PARENT_DOC_ID or "None"}}

### 2.2 Changes Summary

{{CHANGES_SUMMARY - Brief description of what will change}}

### 2.3 Files Affected

{{FILES_AFFECTED - List each file and describe changes}}

- `{{path/to/file1}}` - {{description of changes}}
- `{{path/to/file2}}` - {{description of changes}}

---

## 3. Current State

{{CURRENT_STATE - Concise declarative statement(s) describing what exists now. Use present tense.}}

---

## 4. Proposed State

{{PROPOSED_STATE - Concise declarative statement(s) describing what will exist after the change. Use present tense.}}

---

## 5. Change Description

{{CHANGE_DESCRIPTION - Full technical details of the change. Structure is flexible based on complexity.}}

### 5.1 {{Component/Area 1}}

{{Details for this component}}

### 5.2 {{Component/Area 2}}

{{Details for this component}}

---

## 6. Justification

{{JUSTIFICATION - Why is this change needed?}}

- {{The problem being solved or improvement being made}}
- {{Impact of not making this change}}
- {{How the proposed solution addresses the root cause}}

---

## 7. Impact Assessment

### 7.1 Files Affected

| File | Change Type | Description |
|------|-------------|-------------|
| `{{path/to/file}}` | {{Create/Modify/Delete}} | {{Brief description}} |

### 7.2 Documents Affected

| Document | Change Type | Description |
|----------|-------------|-------------|
| {{DOC-ID}} | {{Create/Modify}} | {{Brief description}} |

### 7.3 Other Impacts

{{OTHER_IMPACTS - External systems, interfaces, dependencies, or "None"}}

### 7.4 Development Controls

<!--
Include this section when the CR modifies controlled code.
Delete this section for document-only CRs.
-->

This CR implements changes to {{SYSTEM}}, a controlled {{submodule/codebase}}. Development follows established controls:

1. **Test environment isolation:** Development in a non-QMS-controlled directory (e.g., `.test-env/`, `/projects/` for containerized agents, or other gitignored location)
2. **Branch isolation:** All development on branch `{{BRANCH_NAME}}`
3. **Write protection:** `.claude/settings.local.json` blocks direct writes to `{{SYSTEM}}/`
4. **Qualification required:** All new/modified requirements must have passing tests before merge
5. **CI verification:** Tests must pass on GitHub Actions for dev branch
6. **PR gate:** Changes merge to main only via PR after RS/RTM approval
7. **Submodule update:** Parent repo updates pointer only after PR merge

### 7.5 Qualified State Continuity

<!--
Include this section when the CR modifies controlled code.
Delete this section for document-only CRs.
-->

| Phase | main branch | RS/RTM Status | Qualified Release |
|-------|-------------|---------------|-------------------|
| Before CR | Current commit | EFFECTIVE v{{N}}.0 | {{SYS}}-{{M}}.0 |
| During execution | Unchanged | DRAFT (checked out) | {{SYS}}-{{M}}.0 (unchanged) |
| Post-approval | Merged from {{BRANCH}} | EFFECTIVE v{{N+1}}.0 | {{SYS}}-{{M+1}}.0 |

---

## 8. Testing Summary

<!--
NOTE: Do NOT delete this comment. It provides guidance during document authoring.

For code CRs, address both categories per SOP-002 Section 6.8:
1. Automated verification: unit tests, qualification tests, CI
2. Integration verification: what will be exercised through user-facing levers
   in a running system to demonstrate the change is effective

For document-only CRs, a description of procedural verification is sufficient.
Delete the subsections below and use a simple list.
-->

### Automated Verification

{{AUTOMATED_TESTING - Unit tests, CI checks, qualification tests}}

- {{Test case 1}}
- {{Test case 2}}

### Integration Verification

{{INTEGRATION_TESTING - What will be launched, what functionality will be exercised through user-facing levers, what behavior demonstrates the change is effective}}

- {{Verification step 1}}
- {{Verification step 2}}

---

## 9. Implementation Plan

<!--
For code CRs, use these standardized phases. Adjust as needed.
For document-only CRs, simplify to relevant steps.
-->

{{IMPLEMENTATION - Detailed plan for executing the change}}

### 9.1 Phase 1: Test Environment Setup

<!--
Include for code CRs. Delete for document-only CRs.
-->

1. Verify/create a non-QMS-controlled working directory (e.g., `.test-env/`, `/projects/`, or other appropriate location)
2. Clone/update {{SYSTEM}} from GitHub
3. Create and checkout branch `{{BRANCH_NAME}}`
4. Verify clean test environment

### 9.2 Phase 2: Requirements (RS Update)

<!--
Include for code CRs that add/modify requirements. Delete if not applicable.
-->

1. Checkout SDLC-{{NS}}-RS in production QMS
2. Add/modify requirements as needed
3. Checkin RS, route for review and approval

### 9.3 Phase 3: Implementation

1. Implement changes per Change Description
2. Test locally
3. Commit to dev branch

### 9.4 Phase 4: Qualification

<!--
Include for code CRs. Delete for document-only CRs.
-->

1. Add/update qualification tests
2. Run full test suite, verify all tests pass
3. Push to dev branch
4. Verify GitHub Actions CI passes
5. Document qualified commit hash

### 9.5 Phase 5: Integration Verification

<!--
Include for code CRs. Delete for document-only CRs.

This phase verifies the implementation in a running system before proceeding
to RTM update and merge. It is distinct from Phase 4 (automated qualification)
and from Phase 7 step 7 (post-merge smoke test):
- Phase 4: Do the automated tests pass? (CI gate)
- Phase 5: Does it actually work when you use it? (integration verification)
- Phase 7 step 7: Did the merge itself introduce any problems? (post-merge smoke test)
-->

1. Launch the application/system with the execution branch code
2. Exercise changed functionality through user-facing levers
3. Confirm the change is effective and no obvious regressions in related functionality
4. Document what was exercised and what was observed

### 9.6 Phase 6: RTM Update and Approval

<!--
Include for code CRs that add/modify requirements. Delete if not applicable.
-->

1. Checkout SDLC-{{NS}}-RTM in production QMS
2. Add verification evidence referencing CI-verified commit
3. Checkin RTM, route for review and approval
4. **Verify RTM reaches EFFECTIVE status before proceeding to Phase 7**

### 9.7 Phase 7: Merge and Submodule Update

<!--
Include for code CRs. Delete for document-only CRs.
-->

**Prerequisite:** RS and RTM must both be EFFECTIVE before proceeding (per SOP-006 Section 7.4).

1. Verify RS is EFFECTIVE (document status check)
2. Verify RTM is EFFECTIVE (document status check)
3. Create PR to merge dev branch to main
4. Merge PR using merge commit -- not squash (per SOP-005 Section 7.1.3)
5. Verify qualified commit hash from execution branch is reachable on main
6. Update submodule pointer in parent repo
7. Verify functionality in production context

### 9.8 Phase 8: Documentation (if applicable)

1. Update CLAUDE.md or other documentation as needed

---

## 10. Execution

<!--
EXECUTION PHASE INSTRUCTIONS
============================
NOTE: Do NOT delete this comment block. It provides guidance for execution.

PRE-EXECUTION: After releasing for execution, the first execution item is to
commit and push the project repository (including all submodules) to capture
the pre-execution baseline (per SOP-004 Section 5). Record the commit hash
in EI-1's execution summary.

POST-EXECUTION: The final execution item is to commit and push the project
repository (including all submodules) to capture the post-execution state
(per SOP-004 Section 5). Record the commit hash in the final EI's execution
summary.

- Sections 1-9 are PRE-APPROVED content - do NOT modify during execution
- Only THIS TABLE and the comment sections below should be edited during execution phase

COLUMNS:
- EI: Execution item identifier
- Task Description: What to do (static, from Implementation Plan)
- Execution Summary: Narrative of what was done, evidence, observations (editable)
- Task Outcome: Pass or Fail (editable)
- Performed By - Date: Signature (editable)

TASK OUTCOME:
- Pass: Task completed as planned
- Fail: Task could not be completed as planned - attach VAR with explanation

VAR TYPES (see VAR-TEMPLATE):
- Type 1: Use when the failed task is critical to CR objectives
- Type 2: Use when impact is contained and CR can conceptually close

EXECUTION SUMMARY EXAMPLES:
- "Implemented per plan. Commit abc123."
- "Modified src/module.py:45-67. Unit tests passing."
- "Created SOP-007 (now EFFECTIVE)."
-->

| EI | Task Description | Execution Summary | Task Outcome | Performed By - Date |
|----|------------------|-------------------|--------------|---------------------|
| EI-1 | {{DESCRIPTION}} | [SUMMARY] | [Pass/Fail] | [PERFORMER] - [DATE] |
| EI-2 | {{DESCRIPTION}} | [SUMMARY] | [Pass/Fail] | [PERFORMER] - [DATE] |
| EI-3 | {{DESCRIPTION}} | [SUMMARY] | [Pass/Fail] | [PERFORMER] - [DATE] |

<!--
AUTHOR NOTE: Delete this comment after reading.

Each EI row has design-time and run-time columns:
- Columns 1-2 (EI, Task Description): Fill during drafting
- Columns 3-5 (Execution Summary, Task Outcome, Performed By): Left for executor
-->

<!--
NOTE: Do NOT delete this comment. It provides guidance during document execution.

Add rows as needed. When adding rows, fill columns 3-5 during execution.
-->

---

### Execution Comments

| Comment | Performed By - Date |
|---------|---------------------|
| [COMMENT] | [PERFORMER] - [DATE] |

<!--
NOTE: Do NOT delete this comment. It provides guidance during document execution.

Record observations, decisions, or issues encountered during execution.
Add rows as needed.

This section is the appropriate place to attach VARs that do not apply
to any individual execution item, but apply to the CR as a whole.
-->

---

## 11. Execution Summary

<!--
NOTE: Do NOT delete this comment. It provides guidance during document execution.

Complete this section after all EIs are executed.
Summarize the overall outcome and any deviations from the plan.
-->

[EXECUTION_SUMMARY]

---

## 12. References

{{REFERENCES - List related documents. At minimum, reference governing SOPs.}}

- **SOP-001:** Document Control
- **SOP-002:** Change Control

---

**END OF DOCUMENT**
