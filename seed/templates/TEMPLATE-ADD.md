---
title: 'Addendum Report Template'
revision_summary: 'CR-082: Initial creation'
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

When creating an ADD from this template, copy from the EXAMPLE FRONTMATTER onward.
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
ADDs are EXECUTABLE documents that encapsulate post-closure corrections.

WORKFLOW:
  DRAFT -> IN_PRE_REVIEW -> PRE_REVIEWED -> IN_PRE_APPROVAL -> PRE_APPROVED
       -> IN_EXECUTION -> IN_POST_REVIEW -> POST_REVIEWED -> IN_POST_APPROVAL
       -> POST_APPROVED -> CLOSED

CONCEPT:
An Addendum Report (ADD) is a child document created to correct or supplement
a closed executable document. ADDs provide a lightweight, formal mechanism for
post-closure corrections without requiring a full INV/CAPA cycle.

ADD vs VAR vs INV:
- VAR: Handles execution failures *during* active work (parent is IN_EXECUTION)
- ADD: Handles corrections discovered *after* closure (parent is CLOSED)
- INV: Handles quality events requiring formal investigation (any timing)

PARENT STATE REQUIREMENT:
ADDs can only be created against CLOSED parents. The CLI enforces this
constraint at creation time.

VALID PARENT TYPES:
CR, INV, VAR, ADD (not TP or ER — test corrections use ER/nested ER)

PLACEHOLDER TYPES:
1. {{DOUBLE_CURLY}} — Replace when AUTHORING the ADD (design time)
2. [SQUARE_BRACKETS] — Replace when EXECUTING the ADD (run time)

ADD ID FORMAT:
  {PARENT_DOC_ID}-ADD-NNN
  Examples:
    CR-005-ADD-001 (addendum to a CR)
    INV-003-ADD-001 (addendum to an investigation)
    CR-005-VAR-001-ADD-001 (addendum to a VAR)

NESTING:
- ADDs can nest: if correction work encounters issues, create child ADD or VAR
- Example: CR-005-ADD-001-ADD-001

LOCKED vs EDITABLE:
- Sections 1-4 are locked after pre-approval
- Sections 5-7 are editable during execution

Delete this comment block after reading.
================================================================================
-->

# {{ADD_ID}}: {{TITLE}}

## 1. Addendum Identification

| Parent Document | Discovery Context | ADD Scope |
|-----------------|-------------------|-----------|
| {{PARENT_DOC_ID}} | {{HOW_DISCOVERED}} | {{BRIEF_SCOPE}} |

<!--
NOTE: Do NOT delete this comment. It provides guidance during document execution.

DISCOVERY CONTEXT: How was the omission or correction need discovered?
Examples: "Post-closure review", "Downstream dependency identified gap",
"User reported missing configuration", "Audit finding"
-->

---

## 2. Description of Omission

{{DESCRIPTION — What was omitted, missed, or needs correction in the parent document?
What was the expected state vs. the actual state discovered post-closure?}}

---

## 3. Impact Assessment

{{IMPACT — What is the effect on the parent document's objectives and deliverables?
Does this affect downstream documents, systems, or processes?}}

---

## 4. Correction Plan

{{CORRECTION_PLAN — How will the omission be addressed?}}

| EI | Task Description |
|----|------------------|
| EI-1 | {{TASK}} |
| EI-2 | {{TASK}} |

<!--
NOTE: Do NOT delete this comment. It provides guidance during document execution.

Define the execution items needed to complete the correction.
These become the static fields in the execution table below.
-->

---

## 5. Execution

<!--
EXECUTION PHASE INSTRUCTIONS
============================
NOTE: Do NOT delete this comment block. It provides guidance for execution.

- Sections 1-4 are PRE-APPROVED content - do NOT modify during execution
- Only THIS TABLE and the sections below should be edited during execution phase

TASK OUTCOME:
- Pass: Task completed as planned
- Fail: Task could not be completed as planned - attach VAR with explanation
-->

| EI | Task Description | Execution Summary | Task Outcome | Performed By — Date |
|----|------------------|-------------------|--------------|---------------------|
| EI-1 | {{DESCRIPTION}} | [SUMMARY] | [Pass/Fail] | [PERFORMER] — [DATE] |
| EI-2 | {{DESCRIPTION}} | [SUMMARY] | [Pass/Fail] | [PERFORMER] — [DATE] |

<!--
NOTE: Do NOT delete this comment. It provides guidance during document execution.

Add rows as needed. When adding rows, fill columns 3-5 during execution.
-->

---

### Execution Comments

| Comment | Performed By — Date |
|---------|---------------------|
| [COMMENT] | [PERFORMER] — [DATE] |

<!--
NOTE: Do NOT delete this comment. It provides guidance during document execution.

Record observations, decisions, or issues encountered during execution.
Add rows as needed.
-->

---

## 6. Scope Handoff

<!--
NOTE: Do NOT delete this comment. It provides guidance during document execution.

Complete this section to confirm nothing was lost between the parent and this ADD.
-->

| Item | Status |
|------|--------|
| What the parent accomplished | [SUMMARY] |
| What this ADD corrects or supplements | [SUMMARY] |
| Confirmation no scope items were lost | [Yes/No — if No, explain] |

---

## 7. Execution Summary

<!--
NOTE: Do NOT delete this comment. It provides guidance during document execution.

Complete this section after all EIs are executed.
Summarize the overall outcome and any deviations from the plan.
-->

[EXECUTION_SUMMARY]

---

## 8. References

- **SOP-001:** Document Control
- **SOP-004:** Document Execution (Section 9B: Addendum Reports)
- **{{PARENT_DOC_ID}}:** Parent document
- {{ADDITIONAL_REFERENCES}}

---

**END OF ADDENDUM REPORT**
