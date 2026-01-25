---
title: 'Test Case Template'
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

NOTE: This is a DOCUMENT FRAGMENT template. Test Cases (TCs) do not exist in
isolation within the QMS—they are composed into Test Protocols (TPs) or other
executable documents. When creating actual Test Cases, omit the frontmatter
(the parent TP provides document control).
================================================================================
-->

<!--
================================================================================
TEMPLATE USAGE GUIDE
================================================================================

PLACEHOLDER TYPES:
1. {{DOUBLE_CURLY}} — Replace when AUTHORING the test case (design time)
2. [SQUARE_BRACKETS] — Replace when EXECUTING the test case (run time)

After authoring:
- NO {{...}} placeholders should remain
- All [...] placeholders should remain until execution

ID HIERARCHY:
- Test Case ID: TC-NNN (within parent TP)
- Step ID: TC-NNN-NNN (e.g., TC-001-001, TC-001-002)
- ER ID: TC-NNN-ER-NNN (e.g., TC-001-ER-001)
- Nested ER ID: TC-NNN-ER-NNN-ER-NNN (e.g., TC-001-ER-001-ER-001)

Full hierarchy example:
  TP-001
  └── TP-001-TC-001
      ├── TP-001-TC-001-001 (step)
      ├── TP-001-TC-001-002 (step)
      └── TP-001-TC-001-ER-001 (exception)
          └── TP-001-TC-001-ER-001-ER-001 (nested exception)

Delete this comment block after reading.
================================================================================
-->

## {{TEST_CASE_ID}}: {{TEST_CASE_TITLE}}

### Prerequisite Section

| Test Case ID | Objectives | Prerequisites | Performed By — Date |
|--------------|------------|---------------|---------------------|
| {{TEST_CASE_ID}} | {{OBJECTIVES}} | {{PREREQUISITES}} | [PERFORMER] — [DATE] |

The signature above indicates that all listed test prerequisites have been satisfied and that the test script below is ready for execution.

---

### Test Script

**Instructions:** Test execution must be performed in accordance with SOP-004 Document Execution. The individual test steps must be executed in the order shown. If a test step fails, execution of the test script must pause. The executor of the test will explain what occurred in the Actual Result field, mark the outcome of the step as "Fail", sign the step, and follow the ER workflow to document and remedy the testing failure.

**Acceptance Criteria:** A test case is accepted when either: (1) all test steps pass (Actual Results match Expected Results), or (2) a step failed, subsequent steps are marked N/A with ER reference, and the ER contains a successful full re-execution of the test case and is closed.

| Step | REQ ID | Instruction | Expected Result | Actual Result | Pass/Fail | Performed By — Date |
|------|--------|-------------|-----------------|---------------|-----------|---------------------|
| {{TEST_CASE_ID}}-001 | {{REQ_ID}} | {{INSTRUCTION}} | {{EXPECTED}} | [ACTUAL] | [Pass/Fail] | [PERFORMER] — [DATE] |
| {{TEST_CASE_ID}}-002 | {{REQ_ID}} | {{INSTRUCTION}} | {{EXPECTED}} | [ACTUAL] | [Pass/Fail] | [PERFORMER] — [DATE] |
| {{TEST_CASE_ID}}-003 | {{REQ_ID}} | {{INSTRUCTION}} | {{EXPECTED}} | [ACTUAL] | [Pass/Fail] | [PERFORMER] — [DATE] |

<!--
AUTHOR NOTE: Delete this comment after reading.

Each test step row has design-time and run-time columns:
- Columns 1-4 (Step, REQ ID, Instruction, Expected Result): Fill during drafting
- Columns 5-7 (Actual Result, Pass/Fail, Performed By): Left for executor
-->

<!--
NOTE: Do NOT delete this comment. It provides guidance during document execution.

Add rows as needed. When adding rows, fill columns 5-7 during execution.
-->

---

### Test Execution Comments

| Comment | Performed By — Date |
|---------|---------------------|
| [COMMENT] | [PERFORMER] — [DATE] |

<!--
NOTE: Do NOT delete this comment. It provides guidance during document execution.

Record observations, deviations, or issues encountered during execution.
Add rows as needed.

This section is the appropriate place to attach ERs that do not apply
to any individual test step, but apply to the test script or protocol as a
whole (e.g., environmental issues, systemic problems discovered during testing).
-->

---

**END OF TEST CASE**
