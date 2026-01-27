---
title: 'Exception Report Template'
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

When creating an ER from this template, copy from the EXAMPLE FRONTMATTER onward.
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
ERs are EXECUTABLE documents created when a test step fails.

WORKFLOW:
  DRAFT → IN_PRE_REVIEW → PRE_REVIEWED → IN_PRE_APPROVAL → PRE_APPROVED
       → IN_EXECUTION → IN_POST_REVIEW → POST_REVIEWED → IN_POST_APPROVAL
       → POST_APPROVED → CLOSED

PLACEHOLDER TYPES:
1. {{DOUBLE_CURLY}} — Replace when AUTHORING the ER (design time)
2. [SQUARE_BRACKETS] — Replace when EXECUTING the ER (run time)

After authoring:
- NO {{...}} placeholders should remain
- All [...] placeholders should remain until execution

ID FORMAT:
  {TC_ID}-ER-NNN
  Example: TP-001-TC-001-ER-001

NESTING:
- Re-test section follows TC-TEMPLATE structure
- ERs can nest: if re-testing fails, create child ER
- Example: TP-001-TC-001-ER-001-ER-001

LOCKED vs EDITABLE (per SOP-004 Section 9.2):
- Sections 1-5 are locked after pre-approval
  (Exception ID, Description, Root Cause, Proposed Corrective Action, Exception Type)
- Section 6 (Re-test) and Section 7 (Closure) are editable during execution

Delete this comment block after reading.
================================================================================
-->

# {{ER_ID}}: {{TITLE}}

## 1. Exception Identification

| Parent Test Case | Failed Step |
|------------------|-------------|
| {{TC_ID}} | {{STEP_ID}} |

---

## 2. Detailed Description

{{DETAILED_DESCRIPTION — What happened? What was expected vs. actual?}}

---

## 3. Root Cause

{{ROOT_CAUSE — Why did this happen?}}

---

## 4. Proposed Corrective Action

{{PROPOSED_CORRECTIVE_ACTION — What will be done to address the root cause before re-testing?}}

---

## 5. Exception Type

{{EXCEPTION_TYPE}}

<!--
NOTE: Do NOT delete this comment. It provides guidance during document execution.

Select one:
- Test Script Error: Test itself was written or designed incorrectly
- Test Execution Error: Tester made a mistake by not following instructions as written
- System Error: The system under test behaved unexpectedly
- Documentation Error: Error in a document other than the test script itself
- Other: See Detailed Description
-->

---

## 6. Re-test

<!--
================================================================================
RE-TEST INSTRUCTIONS (AUTHOR)
================================================================================
AUTHOR NOTE: Delete this comment block after reading.

This section contains a full re-execution of the test case (not just the
failed step). The re-test may have different, more, or fewer steps than
the original if the test script itself required correction.

Follow TC-TEMPLATE structure for the re-test.

If the test script is modified, reviewers must verify that the revised test
script meets the intent of the original test script's objectives. If the TC
objectives themselves are modified, this must be justified.
================================================================================
-->

<!--
NOTE: Do NOT delete this comment block. It provides guidance for execution.

If the re-test fails, create a nested ER.
-->

### Re-test: {{TC_ID}}

#### Prerequisite Section

| Test Case ID | Objectives | Prerequisites | Performed By — Date |
|--------------|------------|---------------|---------------------|
| {{TC_ID}} | {{OBJECTIVES}} | {{PREREQUISITES}} | [PERFORMER] — [DATE] |

The signature above indicates that all listed test prerequisites have been satisfied and that the test script below is ready for execution.

---

#### Test Script

**Instructions:** Test execution must be performed in accordance with SOP-004 Document Execution. The individual test steps must be executed in the order shown. If a test step fails, execution of the test script must pause. The executor of the test will explain what occurred in the Actual Result field, mark the outcome of the step as "Fail", sign the step, and create a nested ER to document and remedy the testing failure.

**Acceptance Criteria:** A test case is accepted when either: (1) all test steps pass (Actual Results match Expected Results), or (2) a step failed, subsequent steps are marked N/A with nested ER reference, and the nested ER contains a successful full re-execution and is closed.

| Step | REQ ID | Instruction | Expected Result | Actual Result | Pass/Fail | Performed By — Date |
|------|--------|-------------|-----------------|---------------|-----------|---------------------|
| {{STEP_ID}}-001 | {{REQ_ID}} | {{INSTRUCTION}} | {{EXPECTED}} | [ACTUAL] | [Pass/Fail] | [PERFORMER] — [DATE] |
| {{STEP_ID}}-002 | {{REQ_ID}} | {{INSTRUCTION}} | {{EXPECTED}} | [ACTUAL] | [Pass/Fail] | [PERFORMER] — [DATE] |
| {{STEP_ID}}-003 | {{REQ_ID}} | {{INSTRUCTION}} | {{EXPECTED}} | [ACTUAL] | [Pass/Fail] | [PERFORMER] — [DATE] |

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

#### Test Execution Comments

| Comment | Performed By — Date |
|---------|---------------------|
| [COMMENT] | [PERFORMER] — [DATE] |

<!--
NOTE: Do NOT delete this comment. It provides guidance during document execution.

Record observations, deviations, or issues encountered during execution.
Add rows as needed.

This section is the appropriate place to attach nested ERs that do not apply
to any individual test step, but apply to the re-test as a whole.
-->

---

## 7. ER Closure

| Details of Resolution | Outcome | Performed By — Date |
|-----------------------|---------|---------------------|
| [RESOLUTION_DETAILS] | [OUTCOME] | [PERFORMER] — [DATE] |

---

## 8. References

- **SOP-004:** Document Execution
- **TC-TEMPLATE:** Test Case structure
- **{{TC_ID}}:** Parent test case
- {{ADDITIONAL_REFERENCES}}

---

**END OF EXCEPTION REPORT**
