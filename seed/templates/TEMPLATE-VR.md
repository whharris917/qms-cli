---
title: Verification Record Template
revision_summary: 'CR-095: Remove redundant prompts/sections, strip labels, subsection headings'
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

When creating a VR from this template, the interaction engine handles
instantiation. VRs are authored via `qms interact`, not freehand editing.
================================================================================
-->

<!--
@template: VR | version: 5 | start: related_eis

Schema Tag Reference
====================

Flow Tags:
  @prompt: id | next: id           Content prompt. Response stored in {{id}}.
  @gate: id | type: yesno | ...    Flow-control prompt. Routes only, no compiled content.
  @loop: name                      Repeating block start. {{_n}} = iteration counter.
  @end-loop: name                  Repeating block end.
  @end-prompt                      Guidance boundary. Ends guidance text after a prompt/gate.
  @end                             Terminal state.

Attributes:
  next: id                         Unconditional transition.
  type: yesno                      Prompt/gate accepts yes or no.
  yes: id / no: id                 Conditional transitions for yesno types.
  default: value                   Auto-fill value (author can override).
  commit: true                     Engine commits project state when response is recorded.

Response Model
==============

Every response is a timestamped list, not a scalar. The initial response
creates a single-entry list. Amendments append to the list -- they never
replace or delete prior entries.

Entry structure:
  - value:      The response content
  - author:     Who recorded this entry
  - timestamp:  When this entry was recorded (ISO 8601)
  - reason:     Why the entry was amended (omitted for initial entry)
  - commit:     Git commit hash (present only on commit-enabled responses)
-->

---
title: '{{title}}'
revision_summary: 'Initial draft'
---

# {{vr_id}}: {{title}}

## 1. Verification Identification

<!-- @prompt: related_eis | next: objective -->

Which execution item(s) in the parent document does this VR verify? (e.g., EI-3, or EI-3 and EI-4)

<!-- @end-prompt -->

| Parent Document | Related EI(s) | Date |
|-----------------|---------------|------|
| {{parent_doc_id}} | {{related_eis}} | {{date}} |

---

## 2. Verification Objective

<!-- @prompt: objective | next: pre_conditions -->

State what CAPABILITY is being verified -- not what specific mechanism is being tested. Frame the objective broadly enough that you naturally check adjacent behavior during the procedure.

Good: "Verify that service health monitoring detects running and stopped services correctly"
Avoid: "Verify the health check endpoint returns 200"

<!-- @end-prompt -->

{{objective}}

---

## 3. Prerequisites

<!-- @prompt: pre_conditions | next: step_instructions -->

Describe the state of the system BEFORE verification begins. A person with terminal access but no knowledge of this project must be able to reproduce these conditions.

Include as applicable: branch and commit checked out, services running (which, what ports), container state, non-default configuration, data state, relevant environment details (OS, Python version, etc.).

<!-- @end-prompt -->

{{pre_conditions}}

---

## 4. Verification Steps

<!-- @loop: steps -->

### 4.{{_n}} Step {{_n}}

<!-- @prompt: step_instructions | next: step_expected -->

What are you about to do? Describe the action and provide the exact command, click target, or navigation path. Commands must be copy-pasteable -- not retyped or abbreviated.

<!-- @end-prompt -->

**{{step_instructions}}**

<!-- @prompt: step_expected | next: step_actual -->

What do you expect to observe? State this BEFORE executing -- not after. Good verification covers both sides: confirming what should be present and confirming what should be absent. A step might check that a service responds correctly, or that an error no longer appears, or that an unrelated subsystem remains unaffected. All of these are evidence.

<!-- @end-prompt -->

{{step_expected}}

<!-- @prompt: step_actual | next: step_outcome | commit: true -->

What did you observe? Reference primary evidence: paste actual terminal output, or attach raw output via --respond --file. Do not summarize or paraphrase. If the output is long, paste the relevant portion and note what was omitted.

The commit hash recorded on this response pins the project state at the moment of observation. A verifier can checkout this commit to see the exact code, configuration, and any output files referenced below.

<!-- @end-prompt -->

```
{{step_actual}}
```

<!-- @prompt: step_outcome | next: more_steps -->

Did the observed output match your expectation? Pass or Fail. If Fail, note the discrepancy.

<!-- @end-prompt -->

{{step_outcome}}

<!-- @gate: more_steps | type: yesno | yes: step_instructions | no: summary_outcome -->

Do you have additional verification steps to record?

<!-- @end-prompt -->

<!-- @end-loop: steps -->

---

## 5. Summary

<!-- @prompt: summary_outcome | next: summary_narrative -->

Considering all steps above, what is the overall outcome? Pass if all steps passed and nothing unexpected was observed. Fail if any step failed or if unexpected behavior was discovered.

<!-- @end-prompt -->

{{summary_outcome}}

<!-- @prompt: summary_narrative | next: end -->

Brief narrative overview of the verification: what was tested, the general approach, and any notable observations -- even if they don't affect the outcome. If any step failed, reference the discrepancy and any VAR created.

<!-- @end-prompt -->

{{summary_narrative}}

<!-- @end -->

---

**END OF VERIFICATION RECORD**
