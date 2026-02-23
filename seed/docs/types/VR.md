# Document Type: VR (Verification Record)

## Overview

A Verification Record (VR) is an **executable**, **attachment-type**, **interactive** document that records behavioral verification of execution items. See [Child Documents](../07-Child-Documents.md) for the conceptual overview and [Interactive Authoring](../08-Interactive-Authoring.md) for the template-driven authoring system. VRs are unique in the QMS in three ways:

1. **Born IN_EXECUTION**: VRs skip the entire pre-approval lifecycle. They are created directly in `IN_EXECUTION` at version `1.0`.
2. **Attachment type**: VRs are cascade-closed when their parent closes, and can close from any non-terminal status.
3. **Interactive authoring**: VRs are authored via a template-driven prompting engine (`qms interact`), not freehand Markdown editing.

---

## Template Structure

Source: `QMS/TEMPLATE/TEMPLATE-VR.md`

The VR template is an **interactive template** -- it contains embedded `@prompt`, `@gate`, and `@loop` tags that drive the interaction engine rather than being edited directly.

### Frontmatter

```yaml
---
title: '{{title}}'
revision_summary: 'Initial draft'
---
```

### Template Header

```
@template: VR | version: 5 | start: related_eis
```

| Field | Value | Purpose |
|-------|-------|---------|
| name | VR | Template identity |
| version | 5 | Schema version (used for source compatibility) |
| start | related_eis | First prompt in the authoring flow |

### Sections

| # | Section | Prompts | Purpose |
|---|---------|---------|---------|
| 1 | Verification Identification | `related_eis` | Which parent EIs this VR verifies |
| 2 | Verification Objective | `objective` | Capability being verified (not mechanism) |
| 3 | Prerequisites | `pre_conditions` | System state before verification begins |
| 4 | Verification Steps | `step_instructions`, `step_expected`, `step_actual`, `step_outcome`, `more_steps` (loop) | Repeating step cycle |
| 5 | Summary | `summary_outcome`, `summary_narrative` | Overall pass/fail and narrative |

### Prompt Flow

```
related_eis -> objective -> pre_conditions -> [LOOP: steps]
  step_instructions -> step_expected -> step_actual (commit) -> step_outcome -> more_steps (gate)
    yes -> step_instructions (next iteration)
    no  -> summary_outcome -> summary_narrative -> END
```

### Prompt Detail

| Prompt ID | Type | Next | Attributes | Guidance Summary |
|-----------|------|------|------------|------------------|
| `related_eis` | prompt | objective | | Which parent EIs does this VR verify? |
| `objective` | prompt | pre_conditions | | State the CAPABILITY being verified, not mechanism |
| `pre_conditions` | prompt | step_instructions | | System state before verification -- must be reproducible |
| `step_instructions` | prompt | step_expected | loop: steps | What you are about to do (copy-pasteable commands) |
| `step_expected` | prompt | step_actual | loop: steps | What you expect BEFORE executing |
| `step_actual` | prompt | step_outcome | loop: steps, **commit: true** | What you observed (raw evidence, not summary) |
| `step_outcome` | prompt | more_steps | loop: steps | Pass or Fail with discrepancy note |
| `more_steps` | gate (yesno) | yes: step_instructions, no: summary_outcome | loop: steps | More verification steps? |
| `summary_outcome` | prompt | summary_narrative | | Overall Pass/Fail |
| `summary_narrative` | prompt | end | | Brief narrative overview |

The `step_actual` prompt has `commit: true`, meaning the engine performs an automatic git commit when this response is recorded, pinning the project state to the observation moment.

---

## Interactive Authoring System

VRs are authored through a four-layer system of files and engines.

### The Three File Layers

| Layer | File | Location | Purpose |
|-------|------|----------|---------|
| Session | `{DOC_ID}.interact` | User workspace | Live authoring state (JSON). Created on checkout, deleted on checkin. |
| Source | `{DOC_ID}.source.json` | `.meta/{type}/` | Permanent record of all responses. Written on checkin. |
| Compiled | `{DOC_ID}.md` | `QMS/{path}/` | Rendered Markdown. Generated from source + template on checkin. |

### Template Tag Vocabulary

Tags are embedded in HTML comments within the template Markdown.

**Flow tags:**

| Tag | Syntax | Purpose |
|-----|--------|---------|
| `@template` | `@template: name \| version: N \| start: id` | Template header (required, exactly once) |
| `@prompt` | `@prompt: id \| next: id [\| commit: true] [\| default: value]` | Content prompt. Response stored in `{{id}}`. |
| `@gate` | `@gate: id \| type: yesno \| yes: id \| no: id` | Flow-control decision. Routes only, no compiled content. |
| `@loop` | `@loop: name` | Repeating block start. `{{_n}}` = iteration counter. |
| `@end-loop` | `@end-loop: name` | Repeating block end. |
| `@end-prompt` | `@end-prompt` | Guidance boundary marker. Ends guidance text after a prompt/gate. |
| `@end` | `@end` | Terminal state. |

**Attributes:**

| Attribute | Used On | Purpose |
|-----------|---------|---------|
| `next: id` | @prompt | Unconditional transition to next node |
| `type: yesno` | @gate | Gate accepts yes or no |
| `yes: id` / `no: id` | @gate | Conditional routing |
| `default: value` | @prompt | Auto-fill value (author can override). Special values: `today`, `current_user` |
| `commit: true` | @prompt | Engine commits project state when response is recorded |

### Response Model (REQ-INT-008, REQ-INT-009)

Every response is a **timestamped append-only list**, not a scalar. The initial response creates a single-entry list. Amendments append -- they never replace or delete prior entries.

```json
{
  "responses": {
    "objective": [
      {
        "value": "Verify API endpoint returns correct response",
        "author": "claude",
        "timestamp": "2026-02-22T01:15:00Z"
      }
    ],
    "step_actual.1": [
      {
        "value": "Output: 4 constraints satisfied",
        "author": "claude",
        "timestamp": "2026-02-22T01:20:00Z",
        "commit": "abc1234"
      },
      {
        "value": "Output: 5 constraints satisfied (rerun after fix)",
        "author": "claude",
        "timestamp": "2026-02-22T02:00:00Z",
        "reason": "Reran after hotfix applied",
        "commit": "def5678"
      }
    ]
  }
}
```

Entry fields:

| Field | Always Present | Purpose |
|-------|----------------|---------|
| `value` | Yes | The response content |
| `author` | Yes | Who recorded this entry |
| `timestamp` | Yes | When recorded (ISO 8601 UTC) |
| `reason` | Only on amendments | Why the entry was amended |
| `commit` | Only on commit-enabled prompts | Git commit hash at moment of observation |

### Source File Structure (REQ-INT-006)

```json
{
  "doc_id": "CR-091-VR-001",
  "template": "VR",
  "template_version": 5,
  "cursor": "step_expected",
  "cursor_context": { "loop": "steps", "iteration": 2 },
  "metadata": {
    "parent_doc_id": "CR-091",
    "vr_id": "CR-091-VR-001",
    "title": "Verify interactive engine"
  },
  "responses": { ... },
  "loops": {
    "steps": {
      "iterations": 2,
      "closed": false,
      "reopenings": []
    }
  },
  "gates": {
    "more_steps.1": { "value": "yes", "timestamp": "..." }
  }
}
```

### Iteration-Indexed IDs

Prompts inside a `@loop` block get iteration-indexed IDs: `{base_id}.{N}`.

| Source Key | Meaning |
|------------|---------|
| `step_instructions.1` | Step 1 instructions |
| `step_actual.2` | Step 2 actual observation |
| `more_steps.1` | Gate decision after step 1 |

Functions `make_iteration_id(base, N)` and `parse_iteration_id(id)` in `interact_source.py` handle this.

---

## The Interaction Engine (`interact_engine.py`)

The `InteractEngine` class manages the authoring session.

### Core Operations

| Method | Purpose |
|--------|---------|
| `get_current_prompt_info()` | Returns status, guidance, and display ID for the current prompt |
| `respond(value, author, reason, commit_hash)` | Record response to current prompt, advance cursor |
| `respond_gate(value, author)` | Record yes/no gate decision, route accordingly |
| `goto(prompt_id, reason)` | Navigate to a previously-answered prompt for amendment |
| `cancel_goto()` | Cancel amendment mode, return to previous position |
| `reopen_loop_cmd(loop_name, reason, author)` | Reopen a closed loop for additional iterations |
| `get_progress()` | List all prompts with fill status |

### Cursor Management

The engine tracks position via `cursor` (current node ID) and `cursor_context` (loop name, iteration number, goto return info).

- **Sequential enforcement** (REQ-INT-014): Responses must be given in template order. You cannot skip ahead.
- **Amendment mode**: `goto` saves current position, moves to target; after responding, returns automatically.
- **Loop reopening**: Closed loops can be reopened with a reason, starting a new iteration.

### Contextual Interpolation (REQ-INT-015)

Guidance text supports `{{id}}` placeholders that resolve to:
1. `{{_n}}` -- current loop iteration number
2. Metadata fields (e.g., `{{parent_doc_id}}`)
3. Previously recorded responses (e.g., `{{objective}}`)

---

## The Compiler (`interact_compiler.py`)

`compile_document(source, template_text)` transforms source + template into final Markdown.

### Compilation Pipeline

| Phase | Operation |
|-------|-----------|
| 0 | Strip template preamble (template's own frontmatter and notice) |
| 1 | Strip all `@tag` comments and inter-tag guidance prose; `@end-prompt` marks guidance boundary |
| 1.5 | Auto-inject metadata: `date` (earliest response), `performer` (all authors), `performed_date` (latest response) |
| 2 | Substitute `{{placeholders}}` with context-aware rendering |
| 3 | Expand loop iterations with subsection numbering |
| 4 | Clean up excessive blank lines |

### Context-Aware Rendering (REQ-INT-024)

| Context | Rendering |
|---------|-----------|
| **Table row** (line starts with `\|`) | Value only, no attribution |
| **Block** (any other line) | Blockquote with attribution lines below |

Amendment trails render superseded entries with strikethrough (`~~old value~~`).

### Loop Expansion (REQ-INT-025)

The template contains a single step block with `{{_n}}` placeholders. The compiler expands this into numbered subsections:

```markdown
### 4.1 Step 1

**Instructions:**
> Run the test suite

*-- claude, 2026-02-22 01:15:00*

**Expected:**
> All tests pass

*-- claude, 2026-02-22 01:15:30*

**Actual:**

```
4 tests passed, 0 failed
```

*-- claude, 2026-02-22 01:16:00 | commit: abc1234*

**Outcome:**
> Pass

*-- claude, 2026-02-22 01:16:30*
```

Each step subsection has four labeled blocks: Instructions, Expected, Actual (in a code fence), Outcome.

---

## CLI Commands

### `qms interact {DOC_ID}` (no flags)

Shows current prompt status and guidance text.

### `qms interact {DOC_ID} --respond "value"`

Records a response to the current prompt. For gates, accepts "yes" or "no".

### `qms interact {DOC_ID} --respond --file path`

Reads response from a file (useful for long evidence output).

### `qms interact {DOC_ID} --goto {prompt_id} --reason "why"`

Navigates to a previously-answered prompt for amendment. Saves current position for automatic return.

### `qms interact {DOC_ID} --cancel-goto`

Cancels amendment mode and returns to saved position.

### `qms interact {DOC_ID} --reopen {loop_name} --reason "why"`

Reopens a closed loop for additional iterations.

### `qms interact {DOC_ID} --progress`

Shows fill status of all prompts: `[x]` filled, `[ ]` unfilled.

### `qms interact {DOC_ID} --compile`

Previews compiled Markdown output to stdout (does not write to QMS).

---

## Engine-Managed Commits (REQ-INT-020)

When a prompt has `commit: true` (only `step_actual` in the VR template), the engine:

1. Stages all changes in the project working tree (`git add -A`)
2. Commits with message: `[QMS] auto-commit | {doc_id} | {prompt_id} | Evidence capture during VR execution`
3. Records the short commit hash (7 chars) in the response entry

This pins the project state at the exact moment of observation, enabling verifiers to checkout that commit to see the code/config/output that produced the evidence.

---

## Naming Convention

```
{PARENT_DOC_ID}-VR-NNN
```

| Example | Meaning |
|---------|---------|
| `CR-091-VR-001` | First VR under CR-091 |
| `CR-091-VAR-001-VR-001` | VR under a VAR |
| `CR-091-ADD-001-VR-001` | VR under an ADD |

**ID pattern regex** (from `qms_schema.py`):
```python
re.compile(r"^(?:CR|INV)-\d{3}(?:-(?:VAR|ADD)-\d{3})*-VR-\d{3}$")
```

---

## Parent/Child Relationships

| Relationship | Details |
|--------------|---------|
| Valid parent types | [CR](CR.md), [VAR](VAR.md), [ADD](ADD.md) |
| Invalid parent types | INV, TP, ER, SOP, etc. |
| Required parent state | **IN_EXECUTION** (enforced at creation time) |
| Children | None (VRs are leaf documents) |
| Attachment flag | `True` -- enables cascade close and relaxed close rules |

---

## CLI Creation

```bash
qms --user claude create VR --parent CR-091 --title "Verify bug fix"
```

**Required flags:**

| Flag | Required | Purpose |
|------|----------|---------|
| `--parent` | Yes | Parent document ID (must be IN_EXECUTION) |
| `--title` | Yes | Document title |

**CLI enforcement at creation** (`commands/create.py`):

1. `--parent` flag is required
2. Parent type must be CR, VAR, or ADD:
   ```python
   if doc_type == "VR" and parent_type not in ("CR", "VAR", "ADD"):
       print("Error: VR documents must have a CR, VAR, or ADD parent")
       return 1
   ```
3. Parent must exist
4. **Parent must be IN_EXECUTION**:
   ```python
   if doc_type == "VR":
       parent_meta = read_meta(parent_id, parent_type)
       if not parent_meta or parent_meta.get("status") != "IN_EXECUTION":
           print(f"Error: VR documents can only be created against IN_EXECUTION parents.")
           return 1
   ```
5. **Born IN_EXECUTION** (REQ-DOC-017): Meta is created then immediately overridden:
   ```python
   if doc_type == "VR":
       meta["status"] = "IN_EXECUTION"
       meta["version"] = "1.0"
       meta["execution_phase"] = "post_release"
   ```
6. Interactive session is initialized: template is parsed, source is created, `.interact` file is written to workspace
7. A placeholder `.md` file is written to workspace (not the compiled document)

---

## Lifecycle

VR has a **truncated lifecycle** -- it skips the entire pre-approval workflow:

```
Created as IN_EXECUTION (v1.0)
  -> IN_POST_REVIEW -> POST_REVIEWED
  -> IN_POST_APPROVAL -> POST_APPROVED
  -> CLOSED
```

The rationale: the VR template *is* the pre-approved protocol. The template was approved through the TEMPLATE document control process. Creating a VR from it is analogous to releasing a pre-approved document for execution.

### Status Transitions

| From | Action | To |
|------|--------|----|
| IN_EXECUTION | route --review | IN_POST_REVIEW |
| IN_POST_REVIEW | review (recommend) | POST_REVIEWED |
| POST_REVIEWED | route --approval | IN_POST_APPROVAL |
| IN_POST_APPROVAL | approve | POST_APPROVED |
| POST_APPROVED | close | CLOSED |

**Additional transitions:**

| From | Action | To | Notes |
|------|--------|----|-------|
| IN_POST_REVIEW | withdraw | IN_EXECUTION | |
| IN_POST_APPROVAL | withdraw | POST_REVIEWED | |
| IN_POST_APPROVAL | reject | POST_REVIEWED | |
| POST_REVIEWED | checkout | IN_EXECUTION | Continue execution |
| POST_REVIEWED | revert | IN_EXECUTION | |

**Attachment-specific behavior:**

VRs have `"attachment": True` in config, which enables special close rules in `commands/close.py`:

```python
is_attachment = get_all_document_types().get(doc_type, {}).get("attachment", False)
if is_attachment:
    if current_status in (Status.CLOSED, Status.RETIRED):
        print(f"Error: {doc_id} is already {current_status.value}.")
        return 1
    # Otherwise: close from ANY non-terminal status
```

This means VRs can be closed from IN_EXECUTION, IN_POST_REVIEW, POST_REVIEWED, etc. -- not just POST_APPROVED. This is essential for cascade close behavior when the parent closes.

---

## Checkin Behavior

VR checkin follows a special interactive path (`_checkin_interactive` in `commands/checkin.py`):

1. Detects `.interact` session file in workspace
2. Loads the session (source data)
3. Loads the seed template (`qms-cli/seed/templates/TEMPLATE-VR.md`)
4. **Compiles** source + template into Markdown via `compile_document()`
5. Archives previous version if IN_EXECUTION
6. Writes compiled Markdown to QMS draft path
7. Saves source to `.meta/{type}/{DOC_ID}.source.json` (permanent record)
8. Updates meta (clears checked_out)
9. Removes `.interact` session and workspace placeholder from workspace

The compiled Markdown is what gets reviewed and approved -- reviewers see the rendered document, not the raw source data.

---

## Checkout Behavior

VR checkout follows an interactive path (`_init_interactive_session` in `commands/checkout.py`):

1. Checks for existing `.source.json` in `.meta/` (from previous checkin)
2. If found, seeds the session from it (resuming where the author left off)
3. If not found, creates a fresh source from the template
4. Saves `.interact` session file to workspace
5. Creates a placeholder `.md` in workspace with instructions to use `qms interact`

---

## Cascade Close

When a parent document closes, `_cascade_close_attachments` in `commands/close.py` handles VRs:

1. Scans `.meta/VR/` for children matching `{parent_id}-VR-NNN`
2. For checked-out VRs: auto-compiles from `.interact` session or `.source.json` or empty source
3. Promotes draft to effective
4. Records CLOSE + STATUS_CHANGE in audit trail
5. Updates meta to CLOSED
6. Cleans up workspace files across all users

This ensures VRs are properly finalized even if they were still being authored when the parent closed.

---

## Configuration

From `qms_config.py`:

```python
"VR": {"path": "CR", "executable": True, "prefix": "VR", "attachment": True}
```

| Property | Value | Meaning |
|----------|-------|---------|
| path | `"CR"` | VRs are stored under the CR document tree |
| executable | `True` | Full executable workflow (but born post-release) |
| prefix | `"VR"` | ID prefix for nested numbering |
| attachment | `True` | Enables cascade close and relaxed close rules |

---

## See Also

- [Interactive Authoring](../08-Interactive-Authoring.md) -- Template tags, source data model, interaction lifecycle
- [Child Documents](../07-Child-Documents.md) -- VR lifecycle, evidence standards, GMP batch record analogy
- [SDLC](../10-SDLC.md) -- VRs as an RTM verification type
- [TEMPLATE Reference](TEMPLATE.md) -- How TEMPLATE-VR is governed (dual-copy system)
- [QMS Glossary](../QMS-Glossary.md) -- Term definitions
