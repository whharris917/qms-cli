---
title: 'Test Protocol Template'
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

When creating a TP from this template, copy from the EXAMPLE FRONTMATTER onward.
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
TPs are EXECUTABLE documents that define and execute verification testing.

WORKFLOW:
  DRAFT → IN_PRE_REVIEW → PRE_REVIEWED → IN_PRE_APPROVAL → PRE_APPROVED
       → IN_EXECUTION → IN_POST_REVIEW → POST_REVIEWED → IN_POST_APPROVAL
       → POST_APPROVED → CLOSED

PLACEHOLDER TYPES:
1. {{DOUBLE_CURLY}} — Replace when AUTHORING the protocol (design time)
2. [SQUARE_BRACKETS] — Replace when EXECUTING the protocol (run time)

After authoring:
- NO {{...}} placeholders should remain
- All [...] placeholders should remain until execution

ID HIERARCHY:
- Protocol ID: TP-NNN
- Test Case ID: TP-NNN-TC-NNN (e.g., TP-001-TC-001)
- Step ID: TP-NNN-TC-NNN-NNN (e.g., TP-001-TC-001-001)
- ER ID: TP-NNN-TC-NNN-ER-NNN (e.g., TP-001-TC-001-ER-001)
- Nested ER: TP-NNN-TC-NNN-ER-NNN-ER-NNN

TEMPLATE NESTING:
- Test Cases follow TC-TEMPLATE structure
- Insert TC sections using the format shown in Section 3
- Do not duplicate TC-TEMPLATE content here—reference it

LOCKED vs EDITABLE:
- Sections 1-2 are locked after pre-approval
- Section 3 (Test Cases) and Section 4 (Summary) are editable during execution

Delete this comment block after reading.
================================================================================
-->

# {{TP_ID}}: {{TITLE}}

## 1. Purpose

{{PURPOSE — What does this test protocol verify? What system/feature is under test?}}

---

## 2. Scope

| System | Version | Commit |
|--------|---------|--------|
| {{SYSTEM_NAME}} | {{SYSTEM_VERSION}} | {{COMMIT_HASH}} |

---

## 3. Test Cases

<!--
================================================================================
TEST CASE INSTRUCTIONS
================================================================================
Insert Test Cases below following TC-TEMPLATE structure:

  ### TC-NNN: {{TEST_CASE_TITLE}}

  #### Prerequisite Section
  (per TC-TEMPLATE)

  #### Test Script
  (per TC-TEMPLATE)

  #### Test Execution Comments
  (per TC-TEMPLATE)

Number TCs sequentially: TC-001, TC-002, etc.
Step IDs follow format: TC-NNN-001, TC-NNN-002, etc.

See TC-TEMPLATE for full structure and boilerplate content.

Delete this comment block after reading.
================================================================================
-->

### TC-001: {{TEST_CASE_TITLE}}

<!-- Insert TC-001 content per TC-TEMPLATE -->

---

### TC-002: {{TEST_CASE_TITLE}}

<!-- Insert TC-002 content per TC-TEMPLATE -->

---

## 4. Protocol Summary

### 4.1 Overall Result

[OVERALL_RESULT — Pass / Fail / Pass with Exceptions]

### 4.2 Execution Summary

[EXECUTION_SUMMARY — Overall narrative of test execution, significant observations, deviations from plan]

---

## 5. References

- **SOP-004:** Document Execution
- **SOP-006:** SDLC Governance
- **TC-TEMPLATE:** Test Case structure
- {{ADDITIONAL_REFERENCES}}

---

**END OF TEST PROTOCOL**
