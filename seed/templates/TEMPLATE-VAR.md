---
title: 'Variance Report Template'
revision_summary: 'CR-017: Initial migration to QMS control'
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

When creating a VAR from this template, copy from the EXAMPLE FRONTMATTER onward.
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
VARs are EXECUTABLE documents that encapsulate resolution work for variances.

WORKFLOW:
  DRAFT → IN_PRE_REVIEW → PRE_REVIEWED → IN_PRE_APPROVAL → PRE_APPROVED
       → IN_EXECUTION → IN_POST_REVIEW → POST_REVIEWED → IN_POST_APPROVAL
       → POST_APPROVED → CLOSED

CONCEPT:
A Variance Report (VAR) is a blocking child container that encapsulates
resolution work without cluttering the parent document with details.
VARs can be attached to any executable document (CR, INV, TC, TP).

VAR TYPES:
- Type 1: Full closure of VAR required to clear block on parent
- Type 2: Pre-approval of VAR sufficient to clear block on parent

Type 1: Use when resolution is critical—the parent cannot meaningfully
close until the fix is proven to work.

Type 2: Use when the variance does not affect conceptual closure of the
parent. The impacts are well understood and contained, and the parent's
core objectives have been met. Type 2 variances also prevent issues from
"falling off the radar"—they provide a dedicated container for follow-up
work that is logically tied to the parent but would otherwise keep the
parent open inefficiently while stray items are cleaned up.

PLACEHOLDER TYPES:
1. {{DOUBLE_CURLY}} — Replace when AUTHORING the VAR (design time)
2. [SQUARE_BRACKETS] — Replace when EXECUTING the VAR (run time)

VAR ID FORMAT:
  {PARENT_DOC_ID}-VAR-NNN
  Examples:
    CR-005-VAR-001 (variance from a CR)
    TP-001-TC-002-VAR-001 (variance from a TC within a TP)
    INV-003-VAR-001 (variance from an investigation)

NESTING:
- VARs can nest: if resolution work encounters issues, create child VAR
- Example: CR-005-VAR-001-VAR-001

LOCKED vs EDITABLE:
- Sections 1-6 are locked after pre-approval
- Section 7 (Resolution Work) and Section 8 (Closure) are editable during execution

Delete this comment block after reading.
================================================================================
-->

# {{VAR_ID}}: {{TITLE}}

## 1. Variance Identification

| Parent Document | Failed Item | VAR Type |
|-----------------|-------------|----------|
| {{PARENT_DOC_ID}} | {{ITEM_ID}} | {{TYPE_1_or_TYPE_2}} |

<!--
NOTE: Do NOT delete this comment. It provides guidance during document execution.

VAR TYPE:
- Type 1: Full closure required to clear block on parent
- Type 2: Pre-approval sufficient to clear block on parent
-->

---

## 2. Detailed Description

{{DETAILED_DESCRIPTION — What happened? What was expected vs. actual?}}

---

## 3. Root Cause

{{ROOT_CAUSE — Why did this happen?}}

---

## 4. Variance Type

{{VARIANCE_TYPE}}

<!--
NOTE: Do NOT delete this comment. It provides guidance during document execution.

Select one:
- Execution Error: Executor made a mistake or didn't follow instructions
- Scope Error: Plan/scope was written or designed incorrectly
- System Error: The system behaved unexpectedly
- Documentation Error: Error in a document other than the parent
- External Factor: Environmental or external issue
- Other: See Detailed Description
-->

---

## 5. Impact Assessment

{{IMPACT_ASSESSMENT — What is the effect on the parent document's objectives?}}

---

## 6. Proposed Resolution

{{PROPOSED_RESOLUTION — What will be done to address the root cause?}}

---

## 7. Resolution Work

<!--
================================================================================
RESOLUTION WORK INSTRUCTIONS (AUTHOR)
================================================================================
AUTHOR NOTE: Delete this comment block after reading.

This section contains the work performed to resolve the variance.
Choose the appropriate structure based on the parent document type:

FOR TEST-RELATED VARIANCES (parent is TC or TP):
  Use TC structure: Prerequisite Section, Test Script, Comments
  (per TC-TEMPLATE)

FOR CR/INV VARIANCES:
  Use EI table structure:
  | EI | Task Description | Execution Summary | Task Outcome | Performed By — Date |

FOR SIMPLE RESOLUTIONS:
  Use narrative + evidence format

If the resolution involves modifying the original scope/plan, reviewers must
verify that the revised approach meets the intent of the parent's objectives.
If objectives are modified, justify.
================================================================================
-->

<!--
NOTE: Do NOT delete this comment block. It provides guidance for execution.

If the resolution work encounters issues, create a nested VAR.
-->

### Resolution: {{PARENT_DOC_ID}}

{{RESOLUTION_WORK — Insert appropriate structure based on guidance above}}

---

### Resolution Comments

| Comment | Performed By — Date |
|---------|---------------------|
| [COMMENT] | [PERFORMER] — [DATE] |

<!--
NOTE: Do NOT delete this comment. It provides guidance during document execution.

Record observations, decisions, or issues encountered during resolution.
Add rows as needed.

This section is the appropriate place to attach nested VARs that do not
apply to any individual resolution item, but apply to the resolution as a whole.
-->

---

## 8. VAR Closure

| Details of Resolution | Outcome | Performed By — Date |
|-----------------------|---------|---------------------|
| [RESOLUTION_DETAILS] | [OUTCOME] | [PERFORMER] — [DATE] |

---

## 9. References

- **SOP-004:** Document Execution
- **{{PARENT_DOC_ID}}:** Parent document
- {{ADDITIONAL_REFERENCES}}

---

**END OF VARIANCE REPORT**
