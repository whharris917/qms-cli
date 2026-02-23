# TC -- Test Case

## Document Type Summary

| Property | Value |
|----------|-------|
| **Type code** | `TC` |
| **Standalone QMS document** | **No** -- TC is a document fragment |
| **Embedded in** | Test Protocols ([TP](TP.md)) and Exception Reports ([ER](ER.md) re-test sections) |
| **Template** | `QMS/TEMPLATE/TEMPLATE-TC.md` |
| **Has its own frontmatter** | No -- parent TP provides document control |
| **Has its own metadata** | No -- no `.meta/TC/` directory, no sidecar file |

---

## 1. What a TC Is (and Is Not)

A Test Case is **not** a standalone document in the QMS. It has no independent lifecycle, no metadata sidecar, no separate ID in `.meta/`. Instead, it is a **structural fragment** embedded as a subsection within a TP or ER.

The `TEMPLATE-TC.md` file is a QMS-controlled template document that defines the canonical structure all Test Cases must follow. When authoring a TP, each TC section copies this structure verbatim into the TP body.

**Key consequence:** TCs cannot be created, checked out, routed, or approved independently. All lifecycle operations happen at the parent TP (or ER) level.

The template's own notice states:

> This is a DOCUMENT FRAGMENT template. Test Cases (TCs) do not exist in isolation within the QMS -- they are composed into Test Protocols (TPs) or other executable documents. When creating actual Test Cases, omit the frontmatter (the parent TP provides document control).

---

## 2. Naming Convention

| Scope | ID Format | Example |
|-------|-----------|---------|
| Within a TP | `TC-NNN` | `TC-001`, `TC-002` |
| Step within a TC | `TC-NNN-NNN` | `TC-001-001`, `TC-001-002` |
| ER for a TC | `TC-NNN-ER-NNN` | `TC-001-ER-001` |
| Nested ER | `TC-NNN-ER-NNN-ER-NNN` | `TC-001-ER-001-ER-001` |

Full-qualified IDs include the TP prefix:

```
CR-001-TP-001
  CR-001-TP-001-TC-001
    CR-001-TP-001-TC-001-001         (step)
    CR-001-TP-001-TC-001-002         (step)
    CR-001-TP-001-TC-001-ER-001      (exception report)
      CR-001-TP-001-TC-001-ER-001-ER-001  (nested exception)
```

TCs are numbered sequentially within their parent: TC-001, TC-002, etc. Steps within a TC are numbered sequentially: TC-001-001, TC-001-002, etc.

---

## 3. Template Structure

### Heading

```markdown
## {{TEST_CASE_ID}}: {{TEST_CASE_TITLE}}
```

Uses `##` (H2) in the standalone template. When embedded in a TP's Section 3, the heading level becomes `###` (H3).

### 3.1 Prerequisite Section

```markdown
### Prerequisite Section

| Test Case ID | Objectives | Prerequisites | Performed By -- Date |
|--------------|------------|---------------|---------------------|
| {{TEST_CASE_ID}} | {{OBJECTIVES}} | {{PREREQUISITES}} | [PERFORMER] -- [DATE] |

The signature above indicates that all listed test prerequisites have been
satisfied and that the test script below is ready for execution.
```

| Column | Phase | Description |
|--------|-------|-------------|
| Test Case ID | Authoring | The TC identifier (e.g., `TC-001`) |
| Objectives | Authoring | What this test case verifies |
| Prerequisites | Authoring | Conditions that must be met before execution |
| Performed By -- Date | **Execution** | Executor signature and date confirming prerequisites are met |

### 3.2 Test Script

The section opens with two standard blocks of boilerplate text:

**Instructions:** Mandates execution per SOP-004. Steps must be executed in order. On failure, execution pauses. The executor records what happened in Actual Result, marks the step "Fail", signs it, and follows the ER workflow.

**Acceptance Criteria:** A test case is accepted when either (1) all test steps pass, or (2) a step failed, subsequent steps are marked N/A with ER reference, and the ER contains a successful full re-execution and is closed.

#### Step Table

```markdown
| Step | REQ ID | Instruction | Expected Result | Actual Result | Pass/Fail | Performed By -- Date |
|------|--------|-------------|-----------------|---------------|-----------|---------------------|
| {{TEST_CASE_ID}}-001 | {{REQ_ID}} | {{INSTRUCTION}} | {{EXPECTED}} | [ACTUAL] | [Pass/Fail] | [PERFORMER] -- [DATE] |
| {{TEST_CASE_ID}}-002 | {{REQ_ID}} | {{INSTRUCTION}} | {{EXPECTED}} | [ACTUAL] | [Pass/Fail] | [PERFORMER] -- [DATE] |
| {{TEST_CASE_ID}}-003 | {{REQ_ID}} | {{INSTRUCTION}} | {{EXPECTED}} | [ACTUAL] | [Pass/Fail] | [PERFORMER] -- [DATE] |
```

| Column | Phase | Description |
|--------|-------|-------------|
| Step | Authoring | Step ID following `TC-NNN-NNN` format |
| REQ ID | Authoring | Requirement being verified by this step |
| Instruction | Authoring | What the executor must do |
| Expected Result | Authoring | What should happen if the system is correct |
| Actual Result | **Execution** | What actually happened (filled by executor) |
| Pass/Fail | **Execution** | Outcome of this step (filled by executor) |
| Performed By -- Date | **Execution** | Executor signature and date |

**Design-time columns (1-4):** Filled during TP authoring. Locked after pre-approval.

**Run-time columns (5-7):** Left blank until execution. Filled by executor.

The template contains a preserved comment (not to be deleted) instructing executors that rows may be added as needed and columns 5-7 are filled during execution.

### 3.3 Test Execution Comments

```markdown
### Test Execution Comments

| Comment | Performed By -- Date |
|---------|---------------------|
| [COMMENT] | [PERFORMER] -- [DATE] |
```

Records observations, deviations, or issues encountered during execution. Also the appropriate place to attach ERs that apply to the test script or protocol as a whole (not to a specific step). Rows are added as needed.

---

## 4. Static vs Editable Content

| Content | Locked After Pre-Approval | Editable During Execution |
|---------|--------------------------|--------------------------|
| Prerequisite Section (ID, Objectives, Prerequisites) | Yes | No |
| Prerequisite Section (Performed By -- Date) | n/a (blank) | Yes |
| Test Script columns 1-4 (Step, REQ ID, Instruction, Expected) | Yes | No |
| Test Script columns 5-7 (Actual, Pass/Fail, Performed By) | n/a (blank) | Yes |
| Test Execution Comments | n/a (blank) | Yes |

**Rule:** The test design (what to test and what to expect) is frozen at pre-approval. Only execution evidence (what happened) is filled during execution.

---

## 5. Placeholder Convention

| Syntax | Phase | Example |
|--------|-------|---------|
| `{{DOUBLE_CURLY}}` | Authoring | `{{TEST_CASE_ID}}`, `{{REQ_ID}}`, `{{INSTRUCTION}}`, `{{EXPECTED}}`, `{{OBJECTIVES}}`, `{{PREREQUISITES}}` |
| `[SQUARE_BRACKETS]` | Execution | `[ACTUAL]`, `[Pass/Fail]`, `[PERFORMER]`, `[DATE]`, `[COMMENT]` |

After authoring is complete:
- **Zero** `{{...}}` placeholders should remain
- **All** `[...]` placeholders should remain (filled during execution)

---

## 6. CLI Behavior

Since TC is not a standalone document type in the QMS, there are **no direct CLI commands** for Test Cases.

`TC` does not appear in `DOCUMENT_TYPES` in `qms_config.py`:

```python
DOCUMENT_TYPES = {
    "SOP": {...},
    "CR": {...},
    "INV": {...},
    "TP": {...},
    "ER": {...},
    "VAR": {...},
    "VR": {...},
    "ADD": {...},
    "TEMPLATE": {...},
}
# Note: no "TC" entry
```

| Operation | Available | Notes |
|-----------|-----------|-------|
| `qms create TC` | **No** | `TC` is not in `get_all_document_types()`. CLI returns "Unknown document type 'TC'". |
| `qms checkout TC-001` | **No** | `get_doc_type("TC-001")` raises `ValueError`. |
| `qms route TC-001` | **No** | Same -- no independent ID resolution. |
| `qms status TC-001` | **No** | Same. |

To work on a TC, you check out the parent TP and edit the TC subsection within it.

The TC template itself (`QMS/TEMPLATE/TEMPLATE-TC.md`) is a QMS-controlled template document with its own frontmatter (`title: 'Test Case Template'`, `revision_summary`) and can be revised through the standard TEMPLATE document workflow. But instances of TCs embedded in TPs are just markdown sections.

---

## 7. Acceptance Criteria

Per the template's embedded instructions, a test case is accepted when **either**:

1. **All test steps pass** -- Actual Results match Expected Results for every step.
2. **A step failed** -- subsequent steps are marked N/A with ER reference, and the ER contains a successful full re-execution of the test case and is closed.

---

## 8. Failure Workflow

When a step fails during execution:

1. Executor fills the Actual Result column explaining what occurred
2. Executor marks the step outcome as "Fail"
3. Executor signs the step (Performed By -- Date)
4. **Execution pauses** -- no further steps in the TC are executed
5. An [Exception Report (ER)](ER.md) is created as a child of the parent TP
6. Remaining steps in the TC are marked N/A with a reference to the ER
7. The ER contains a full re-execution of the test case (not just the failed step)

---

## 9. How TCs Appear Inside a TP

Within a TP's Section 3 (Test Cases), each TC is inserted as a `###` subsection. The TP template shows the insertion pattern:

```markdown
## 3. Test Cases

### TC-001: {{TEST_CASE_TITLE}}

<!-- Insert TC-001 content per TC-TEMPLATE -->

---

### TC-002: {{TEST_CASE_TITLE}}

<!-- Insert TC-002 content per TC-TEMPLATE -->
```

Each TC expands into the full Prerequisite Section, Test Script, and Test Execution Comments structure defined by TEMPLATE-TC.

---

## 10. How TCs Appear Inside an ER

The ER re-test section (Section 6) replicates the full TC structure for re-execution:

```markdown
## 6. Re-test

### Re-test: {{TC_ID}}

#### Prerequisite Section
| Test Case ID | Objectives | Prerequisites | Performed By -- Date |
|...|...|...|...|

#### Test Script
| Step | REQ ID | Instruction | Expected Result | Actual Result | Pass/Fail | Performed By -- Date |
|...|...|...|...|...|...|...|

#### Test Execution Comments
| Comment | Performed By -- Date |
|...|...|
```

The re-test may have different, more, or fewer steps than the original if the test script required correction. Reviewers must verify that revised scripts still meet the intent of the original objectives. If the TC objectives themselves are modified, this must be justified.

---

## See Also

- [TP Reference](TP.md) -- Test Protocols that contain TC fragments
- [ER Reference](ER.md) -- Exception Reports that re-execute TCs
- [TEMPLATE Reference](TEMPLATE.md) -- TEMPLATE-TC as a controlled document
- [Execution](../06-Execution.md) -- Static vs editable field concepts
