---
title: 'Investigation Template'
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

When creating an INV from this template, copy from the EXAMPLE FRONTMATTER onward.
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
INVs are EXECUTABLE documents for investigating deviations and implementing
corrective/preventive actions (CAPAs).

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
  INV-NNN
  Example: INV-001, INV-002

CAPA FORMAT:
  INV-NNN-CAPA-NNN
  Example: INV-001-CAPA-001, INV-001-CAPA-002

LOCKED vs EDITABLE:
- Sections 1-6 are locked after pre-approval
- Sections 7-10 are editable during execution

STRUCTURE (per SOP-003 Section 5):
Pre-Approved Content (locked after pre-approval):
  1. Purpose
  2. Scope (Context, Deviation Type, Systems/Documents Affected)
  3. Background
  4. Description of Deviation(s)
  5. Impact Assessment
  6. Root Cause Analysis

Execution Content (editable during execution):
  7. Remediation Plan (CAPAs)
  8. Execution Comments
  9. Execution Summary
  10. References

Delete this comment block after reading.
================================================================================
-->

# INV-XXX: {{TITLE}}

## 1. Purpose

{{PURPOSE - Why does this investigation exist? What deviation or quality event triggered it?}}

---

## 2. Scope

### 2.1 Context

{{CONTEXT - How was the deviation discovered? Reference triggering event or document.}}

- **Triggering Event:** {{EVENT_DESCRIPTION or "None"}}
- **Related Document:** {{DOC_ID or "None"}}

### 2.2 Deviation Type

{{DEVIATION_TYPE - Procedural or Product per SOP-003 Section 2}}

- **Type:** {{Procedural / Product}}

### 2.3 Systems/Documents Affected

{{AFFECTED - List impacted systems, files, or documents}}

- `{{path/to/file1}}` - {{description}}
- `{{DOC-ID}}` - {{description}}

---

## 3. Background

{{BACKGROUND - Context and circumstances of the deviation}}

### 3.1 Expected Behavior

{{EXPECTED - What was expected to happen?}}

### 3.2 Actual Behavior

{{ACTUAL - What actually happened?}}

### 3.3 Discovery

{{DISCOVERY - When and how was the deviation discovered?}}

### 3.4 Timeline

| Date | Event |
|------|-------|
| {{DATE}} | {{EVENT}} |
| {{DATE}} | {{EVENT}} |

---

## 4. Description of Deviation(s)

{{DESCRIPTION - Full details of the deviation(s) being investigated}}

### 4.1 Facts and Observations

{{FACTS - Objective observations about the deviation}}

### 4.2 Evidence

{{EVIDENCE - Documents reviewed, system states observed, evidence collected}}

- {{Evidence item 1}}
- {{Evidence item 2}}

---

## 5. Impact Assessment

### 5.1 Systems Affected

| System | Impact | Description |
|--------|--------|-------------|
| {{SYSTEM}} | {{High/Medium/Low}} | {{Brief description}} |

### 5.2 Documents Affected

| Document | Impact | Description |
|----------|--------|-------------|
| {{DOC-ID}} | {{High/Medium/Low}} | {{Brief description}} |

### 5.3 Other Impacts

{{OTHER_IMPACTS - Users, workflows, external systems, or "None"}}

---

## 6. Root Cause Analysis

{{ROOT_CAUSE_ANALYSIS - Analysis to identify fundamental cause(s) of the deviation}}

### 6.1 Contributing Factors

{{FACTORS - What factors contributed to this deviation?}}

- {{Factor 1}}
- {{Factor 2}}

### 6.2 Root Cause(s)

{{ROOT_CAUSES - The fundamental reason(s) for the deviation}}

---

## 7. Remediation Plan (CAPAs)

<!--
CAPA EXECUTION INSTRUCTIONS
===========================
NOTE: Do NOT delete this comment block. It provides guidance for execution.

- Sections 1-6 are PRE-APPROVED content - do NOT modify during execution
- Only THIS TABLE and the sections below should be edited during execution phase

CAPA TYPES (per SOP-003 Section 6):
- Corrective Action: Eliminate cause of existing deviation and/or remediate consequences
- Preventive Action: Eliminate cause of potential future deviation; continuous improvement

COLUMNS:
- CAPA: CAPA identifier (e.g., INV-001-CAPA-001)
- Type: Corrective or Preventive
- Description: What the CAPA accomplishes (static)
- Implementation: How it will be implemented, child CR references (editable)
- Outcome: Pass or Fail (editable)
- Verified By - Date: Signature (editable)

CHILD CRs:
CAPAs may spawn child CRs. Reference them in the Implementation column.
All child CRs must be CLOSED before the INV can be closed.
-->

| CAPA | Type | Description | Implementation | Outcome | Verified By - Date |
|------|------|-------------|----------------|---------|---------------------|
| INV-XXX-CAPA-001 | {{Corrective/Preventive}} | {{DESCRIPTION}} | [IMPLEMENTATION] | [Pass/Fail] | [VERIFIER] - [DATE] |
| INV-XXX-CAPA-002 | {{Corrective/Preventive}} | {{DESCRIPTION}} | [IMPLEMENTATION] | [Pass/Fail] | [VERIFIER] - [DATE] |

<!--
AUTHOR NOTE: Delete this comment after reading.

Each CAPA row has design-time and run-time columns:
- Columns 1-3 (CAPA, Type, Description): Fill during drafting
- Columns 4-6 (Implementation, Outcome, Verified By): Left for executor
-->

<!--
NOTE: Do NOT delete this comment. It provides guidance during document execution.

Add rows as needed. When adding rows, fill columns 4-6 during execution.
-->

---

## 8. Execution Comments

| Comment | Performed By - Date |
|---------|---------------------|
| [COMMENT] | [PERFORMER] - [DATE] |

<!--
NOTE: Do NOT delete this comment. It provides guidance during document execution.

Record observations, decisions, or issues encountered during CAPA execution.
Add rows as needed.

This section is the appropriate place to attach VARs that do not apply
to any individual CAPA, but apply to the INV as a whole.
-->

---

## 9. Execution Summary

<!--
NOTE: Do NOT delete this comment. It provides guidance during document execution.

Complete this section after all CAPAs are executed.
Summarize the overall outcome and any deviations from the plan.
-->

[EXECUTION_SUMMARY]

---

## 10. References

{{REFERENCES - List related documents. At minimum, reference governing SOPs.}}

- **SOP-001:** Document Control
- **SOP-003:** Deviation Management

---

**END OF DOCUMENT**
