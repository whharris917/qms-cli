---
title: 'Change Record Template'
revision_summary: Initial release
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
revision_summary: Initial release
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

---

## 8. Testing Summary

{{TESTING - Describe how the implementation will be verified}}

- {{Test case 1}}
- {{Test case 2}}
- {{Test case 3}}

---

## 9. Implementation Plan

{{IMPLEMENTATION - Detailed plan for executing the change}}

### 9.1 {{Phase/Component 1}}

1. {{Step one}}
2. {{Step two}}
3. {{Step three}}

### 9.2 {{Phase/Component 2}}

1. {{Step one}}
2. {{Step two}}

---

## 10. Execution

<!--
EXECUTION PHASE INSTRUCTIONS
============================
NOTE: Do NOT delete this comment block. It provides guidance for execution.

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
