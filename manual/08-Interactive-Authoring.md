# 8. Interactive Authoring

The interactive authoring system replaces freehand markdown editing with a template-driven state machine. Instead of opening a document and typing, the author responds to a sequence of prompts. The engine records each response with attribution, manages loops and branching, and compiles the collected data into a finished document.

Currently, interactive authoring supports [VR (Verification Record)](types/VR.md) documents only. The architecture is designed to extend to CRs, VARs, and other document types.

---

## 8.1 Concept

A traditional QMS document is authored by editing a markdown file directly. This works but creates several problems:

- Authors must know the document structure and SOP requirements
- Evidence attribution (who wrote what, when) is manual and error-prone
- Amendments overwrite history unless the author manually preserves it
- There is no enforcement of prompt sequencing or completeness

The interactive system solves these by separating **what to ask** (the template) from **what was answered** (the source data) from **what gets rendered** (the compiled document). The author never edits the output markdown directly.

---

## 8.2 Three File Layers

Every interactive document involves three artifacts:

| File | Location | Lifecycle | Purpose |
|------|----------|-----------|---------|
| `.interact` | User workspace | Transient (session) | Working copy of source data while checked out |
| `.source.json` | `.meta/` | Durable (permanent) | Authoritative record of all responses, amendments, and metadata |
| `.md` | Document directory | Derived (compiled) | Human-readable output, regenerated from source on checkin |

### Flow between layers

```
Template (TEMPLATE-VR.md)
    |
    v
[qms checkout] --> .interact (workspace session file)
    |
    v
[qms interact --respond] --> updates .interact in place
    |
    v
[qms checkin] --> .interact --> .source.json (permanent)
                             --> compiled .md (derived output)
                  .interact deleted from workspace
```

The `.interact` file is a JSON file with the same structure as `.source.json`. It exists only while the document is checked out. On checkin, the engine copies it to `.source.json` (durable storage) and compiles the markdown output.

---

## 8.3 Template Tags

Templates embed flow-control tags inside HTML comments. The tags define the prompt sequence, loops, gates, and terminal state. Everything between tags is guidance text shown to the author during interaction.

### Tag Reference

| Tag | Syntax | Purpose |
|-----|--------|---------|
| `@template` | `@template: TYPE \| version: N \| start: prompt_id` | Header declaring template type, version, and entry point |
| `@prompt` | `@prompt: id \| next: id` | Content prompt. Author's response is stored under `id` |
| `@gate` | `@gate: id \| type: yesno \| yes: id \| no: id` | Flow-control decision point. Routes to `yes` or `no` target |
| `@loop` | `@loop: name` | Start of a repeating block |
| `@end-loop` | `@end-loop: name` | End of a repeating block |
| `@end-prompt` | `@end-prompt` | Marks the end of guidance text after a prompt or gate |
| `@end` | `@end` | Terminal state -- all prompts complete |

### Prompt Attributes

| Attribute | Values | Effect |
|-----------|--------|--------|
| `next` | prompt ID | Unconditional transition to next prompt |
| `type` | `yesno` | Restricts response to "yes" or "no" |
| `yes` / `no` | prompt IDs | Conditional transitions (gates only) |
| `default` | value or keyword | Auto-fill value (author can override). Keywords: `today`, `current_user` |
| `commit` | `true` | Engine performs a git commit when this response is recorded |

### Example: VR Template Structure

This is a simplified view of the VR template showing the tag flow:

```
@template: VR | version: 5 | start: related_eis

@prompt: related_eis | next: objective
  "Which execution item(s) does this VR verify?"
@end-prompt

@prompt: objective | next: pre_conditions
  "State what capability is being verified..."
@end-prompt

@prompt: pre_conditions | next: step_instructions
  "Describe the system state before verification..."
@end-prompt

@loop: steps

  @prompt: step_instructions | next: step_expected
    "What are you about to do?"
  @end-prompt

  @prompt: step_expected | next: step_actual
    "What do you expect to observe?"
  @end-prompt

  @prompt: step_actual | next: step_outcome | commit: true
    "What did you observe?"
  @end-prompt

  @prompt: step_outcome | next: more_steps
    "Pass or Fail."
  @end-prompt

  @gate: more_steps | type: yesno | yes: step_instructions | no: summary_outcome
    "Do you have additional verification steps?"
  @end-prompt

@end-loop: steps

@prompt: summary_outcome | next: summary_narrative
  "Overall outcome? Pass or Fail."
@end-prompt

@prompt: summary_narrative | next: end
  "Brief narrative overview..."
@end-prompt

@end
```

The graph for this template:

```
related_eis --> objective --> pre_conditions --> [loop: steps]
                                                     |
                                                step_instructions
                                                     |
                                                step_expected
                                                     |
                                                step_actual (commit)
                                                     |
                                                step_outcome
                                                     |
                                                more_steps (gate)
                                                 /        \
                                              yes          no
                                               |            |
                                        step_instructions  [exit loop]
                                                            |
                                                     summary_outcome
                                                            |
                                                     summary_narrative
                                                            |
                                                          @end
```

---

## 8.4 Source Data Model

The `.source.json` (and `.interact` session file) is a JSON object with this structure:

```json
{
  "doc_id": "CR-042-VR-001",
  "template": "VR",
  "template_version": 5,
  "cursor": "step_expected",
  "cursor_context": {
    "loop": "steps",
    "iteration": 2
  },
  "metadata": {
    "parent_doc_id": "CR-042",
    "title": "Integration verification for diff command",
    "vr_id": "CR-042-VR-001"
  },
  "responses": {
    "related_eis": [
      {
        "value": "EI-6",
        "author": "claude",
        "timestamp": "2026-02-20T14:30:00Z"
      }
    ],
    "step_instructions.1": [
      {
        "value": "Run `qms diff SOP-001 --version 1.0`",
        "author": "claude",
        "timestamp": "2026-02-20T14:35:00Z"
      }
    ],
    "step_actual.1": [
      {
        "value": "Unified diff output showing section changes...",
        "author": "claude",
        "timestamp": "2026-02-20T14:36:00Z",
        "commit": "d73f154"
      }
    ]
  },
  "loops": {
    "steps": {
      "iterations": 2,
      "closed": false,
      "reopenings": []
    }
  },
  "gates": {
    "more_steps.1": {
      "value": "yes",
      "timestamp": "2026-02-20T14:37:00Z"
    }
  }
}
```

Key points:
- **`cursor`** tracks the current prompt (where the author is in the sequence)
- **`cursor_context`** carries loop/iteration state and goto-return addresses
- **Iteration-indexed IDs**: loop prompts use `base_id.N` format (e.g., `step_actual.1`, `step_actual.2`)
- **Responses are lists**, not scalars -- amendments append to the list

---

## 8.5 Interaction Lifecycle

### Starting an Interactive Session

```bash
qms checkout CR-042-VR-001     # Checks out document, creates .interact session
qms interact CR-042-VR-001     # Shows current prompt and guidance
```

Checkout creates the `.interact` session file in the user's workspace, initialized from the template's start prompt. If a `.source.json` already exists (from a previous checkout/checkin cycle), the session resumes from that state.

### Responding to Prompts

```bash
# Inline response
qms interact CR-042-VR-001 --respond "EI-6"

# Response from file (for long content like terminal output)
qms interact CR-042-VR-001 --respond --file /path/to/output.txt
```

The engine validates the response against the current cursor position, records it with attribution (author + timestamp), and advances the cursor to the next prompt. If the prompt has `commit: true`, the engine performs a git commit before recording the response.

### Checking Progress

```bash
qms interact CR-042-VR-001 --progress
```

Output:

```
Progress:
  [x] related_eis
  [x] objective
  [x] pre_conditions
  [x] step_instructions.1 [steps.1]
  [x] step_expected.1 [steps.1]
  [x] step_actual.1 (commit) [steps.1]
  [x] step_outcome.1 [steps.1]
  [x] more_steps.1 [steps.1]
  [ ] step_instructions.2 [steps.2]    <-- current
  ...
```

### Previewing Compiled Output

```bash
qms interact CR-042-VR-001 --compile
```

Compiles the current source data through the template and outputs the resulting markdown to stdout. This is a preview only -- it does not write to disk.

### Checking In

```bash
qms checkin CR-042-VR-001
```

Checkin performs three operations:
1. Copies `.interact` to `.source.json` (durable storage in `.meta/`)
2. Compiles the source through the template into the final `.md` document
3. Deletes the `.interact` session file from workspace

After checkin, the document can be routed for review or further workflow transitions.

---

## 8.6 Response Model

### Append-Only Entries

Every response is stored as a **list of entries**, not a single value. The initial response creates a one-element list. Amendments append new entries -- they never replace or delete prior entries.

Entry structure:

| Field | Required | Description |
|-------|----------|-------------|
| `value` | Yes | The response content |
| `author` | Yes | Who recorded this entry |
| `timestamp` | Yes | ISO 8601 UTC timestamp |
| `reason` | Amendments only | Why the entry was amended |
| `commit` | Commit-enabled only | Git commit hash pinning project state |

### Amendments

To amend a previously-answered prompt, use `--goto` to navigate to it, then `--respond` with a `--reason`:

```bash
# Navigate to the prompt
qms interact CR-042-VR-001 --goto step_expected.1 --reason "Clarifying expected output format"

# Record amended response
qms interact CR-042-VR-001 --respond "Expect unified diff with --- and +++ headers" --reason "Clarifying expected output format"
```

The original response is preserved. In the compiled document, superseded entries render with ~~strikethrough~~ and the active entry renders normally. All entries include attribution lines.

### Compiled Rendering

The compiler transforms responses into context-appropriate output:

| Context | Rendering |
|---------|-----------|
| **Table cell** | Active value only (no attribution, no amendment trail) |
| **Block** | Blockquote with attribution line(s) below |
| **Code block** | Fenced code block with attribution below |

Example of a block with amendment trail in compiled output:

```markdown
> ~~Expect 200 OK response~~
> Expect unified diff with --- and +++ headers

*-- claude, 2026-02-20 14:32:00 | Amended: Clarifying expected output format*
*-- claude, 2026-02-20 14:35:00*
```

---

## 8.7 Engine-Managed Commits

Prompts with `commit: true` trigger automatic git commits at the moment of response. This is designed for evidence capture -- pinning the exact project state when an observation is recorded.

### What Happens

1. Author submits response to a commit-enabled prompt
2. Engine runs `git add -A` in the project working tree
3. Engine runs `git commit` with a system-generated message
4. Engine captures the short commit hash
5. Hash is stored in the response entry's `commit` field
6. Author's response is then recorded with the commit hash attached

### Commit Message Format

```
[QMS] auto-commit | CR-042-VR-001 | step_actual.1 | Evidence capture during VR execution
```

### Why This Matters

The commit hash creates a verifiable link between evidence and code state. A reviewer can checkout that commit to see the exact code, configuration, and output files that existed at the moment the evidence was captured. This is the "contemporaneous" part of the [evidence standards](07-Child-Documents.md#evidence-standards).

---

## 8.8 Navigation

### goto (Amend a Previous Response)

```bash
qms interact DOC_ID --goto prompt_id --reason "reason for amendment"
```

Navigates the cursor to a previously-answered prompt. The current cursor position is saved so the engine can return after the amendment. Responding in goto mode requires `--reason`.

After the amendment response is recorded, the cursor automatically returns to where it was before the goto.

### cancel-goto

```bash
qms interact DOC_ID --cancel-goto
```

Cancels an active goto and returns the cursor to the saved position without recording an amendment.

### reopen (Add Iterations to a Closed Loop)

```bash
qms interact DOC_ID --reopen steps --reason "Additional verification step needed"
```

Reopens a loop that was previously closed (by answering "no" at its gate). A new iteration starts, and the cursor moves to the first prompt in the loop. After the new iteration(s) are complete and the gate is answered "no" again, the cursor returns to where it was before the reopen.

Reopenings are recorded in the source data with reason, author, and timestamp.

---

## 8.9 Command Reference

| Command | Effect |
|---------|--------|
| `qms interact DOC_ID` | Show current prompt, guidance, and status |
| `qms interact DOC_ID --respond "value"` | Record response to current prompt |
| `qms interact DOC_ID --respond --file path` | Record response from file contents |
| `qms interact DOC_ID --respond "yes"` | Answer a gate prompt (yes/no) |
| `qms interact DOC_ID --progress` | Show checklist of all prompts with fill status |
| `qms interact DOC_ID --compile` | Preview compiled markdown output |
| `qms interact DOC_ID --goto id --reason "..."` | Navigate to prompt for amendment |
| `qms interact DOC_ID --cancel-goto` | Cancel active goto, return to saved position |
| `qms interact DOC_ID --reopen loop --reason "..."` | Reopen a closed loop for more iterations |

All commands require the document to be checked out to the current user.

---

## 8.10 Sequential Enforcement

The engine enforces strict sequential prompt ordering. You cannot skip ahead or respond out of order. The cursor advances only when the current prompt receives a valid response. This guarantees that:

- Every prompt in the sequence is addressed
- Loop iterations are complete before the gate is reached
- Evidence capture commits happen at the correct point in the sequence
- The progress report accurately reflects what has and has not been answered

The only way to revisit a previous prompt is through `--goto`, which preserves the current position and returns to it after the amendment.

---

**See also:**
- [07-Child-Documents.md](07-Child-Documents.md) -- VR lifecycle, evidence standards, when to use each child type
- [06-Execution.md](06-Execution.md) -- Executable block structure and EI tables
- [TEMPLATE Reference](types/TEMPLATE.md) -- How templates are controlled documents with dual-copy system
- [VR Reference](types/VR.md) -- VR-specific CLI enforcement and interactive session details
- [12-CLI-Reference.md](12-CLI-Reference.md) -- Full CLI command reference
- [QMS-Glossary.md](QMS-Glossary.md) -- Term definitions
