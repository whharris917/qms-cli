# VR Authoring Guide

Practical guide for creating, filling, and closing Verification Records. This is for someone who is about to author a VR or is in the middle of one.

---

## When Is a VR Needed?

A VR is needed when an execution item (EI) in the parent document has `VR=Yes` in the VR column of the EI table. The VR flag means the EI requires **structured behavioral verification** -- proof that a capability works as intended, collected through a defined procedure with observable outcomes.

**VR-flagged items are planned before execution.** The decision to flag an EI with VR=Yes happens during authoring (pre-approval), not during execution. If you discover during execution that an EI needs behavioral verification but it was not flagged, you can still create a VR -- but this should be noted as a scope addition in the Execution Comments.

**Not every EI needs a VR.** Simple code commits, document updates, and configuration changes are adequately evidenced by commit hashes and CLI output in the EI evidence column. VRs are for verification that requires multiple steps, specific preconditions, and observable outputs.

---

## VR Lifecycle

VRs have a unique, truncated lifecycle compared to other documents:

```
Create VR (born at v1.0, state: IN_EXECUTION)
    |
    v
Fill VR via qms interact (prompt-by-prompt)
    |
    v
Check in (compiles .interact -> .source.json -> .md)
    |
    v
VR enters post-review as part of parent's post-review
    |
    v
Parent post-approval triggers VR post-approval
    |
    v
Parent close triggers VR close (cascade)
```

**Key differences from other child documents:**

| What | VR | VAR / ADD / ER |
|------|-----|----------------|
| Born at | v1.0, IN_EXECUTION | v0.1, DRAFT |
| Pre-approval needed | No | Yes |
| Authoring method | Interactive only (`qms interact`) | Freehand markdown |
| Independent review | No (reviewed with parent) | Yes (own review/approval cycle) |
| Closure | Cascade-closed when parent closes | Independently closed |

**Why no pre-approval?** The VR template is itself a controlled document. Creating a VR from it is like filling in a pre-approved form. The form structure has already been validated; you are just recording observations.

---

## Creating a VR

### Prerequisites

- Parent document must be IN_EXECUTION
- Parent document type must be CR, VAR, or ADD
- You need the parent document ID and a title

### Command

```bash
qms create VR --parent CR-045 --title "Verify token validation under load"
```

**What happens on creation:**
1. VR is created at v1.0, state: IN_EXECUTION (skips entire pre-approval lifecycle)
2. Interactive session is initialized from the VR template
3. VR is automatically checked out to your workspace
4. A `.interact` session file is created, ready for prompting

### After Creation: Start Interacting

```bash
qms interact CR-045-VR-001
```

This shows you the first prompt and its guidance text. You are now in the interactive authoring flow.

---

## The Interactive Authoring Flow

VRs are authored through a sequence of prompts. You respond to each prompt in order. The engine records your responses with attribution (who, when) and manages the flow.

### The Prompt Sequence

```
1. related_eis      -- Which parent EIs does this VR verify?
2. objective        -- What capability is being verified?
3. pre_conditions   -- System state before verification begins
4. [LOOP: steps]
   a. step_instructions  -- What you are about to do
   b. step_expected      -- What you expect to observe
   c. step_actual        -- What you actually observed (engine commits here)
   d. step_outcome       -- Pass or Fail
   e. more_steps         -- More steps? (yes/no gate)
5. summary_outcome     -- Overall Pass or Fail
6. summary_narrative   -- Brief narrative overview
```

### Responding to Prompts

```bash
# See the current prompt and guidance
qms interact CR-045-VR-001

# Respond inline
qms interact CR-045-VR-001 --respond "EI-3, EI-4"

# Respond from a file (for long output like terminal logs)
qms interact CR-045-VR-001 --respond --file /tmp/test-output.txt

# Check progress
qms interact CR-045-VR-001 --progress
```

### The Step Loop

The verification steps form a repeating loop. For each step:

1. You describe what you are about to do (instructions)
2. You state what you expect to see (expected) -- **before executing**
3. You execute the step and record what you observed (actual)
4. You record Pass or Fail (outcome)
5. You answer whether there are more steps (gate)

If you answer "yes" to the gate, a new step iteration begins. If "no," the loop closes and you move to the summary.

---

## Writing Good VR Content

### Objective: What You Are Proving, Not What You Are Doing

The objective describes the **capability** being verified, not the specific test actions.

| Bad (mechanism-focused) | Good (capability-focused) |
|------------------------|--------------------------|
| "Run the module and check output" | "Verify that the authentication module validates JWT tokens within the configured latency budget" |
| "Test the dropdown widget" | "Verify that the toolbar dropdown renders, responds to click events, and closes on outside click" |
| "Check that the config was updated" | "Verify that the application reads and applies the updated retry count from configuration" |

**The test:** Could you change the implementation and still use the same objective? If yes, it is capability-focused. If changing the implementation would require rewriting the objective, it is mechanism-focused.

### Pre-Conditions: Reproducible System State

Pre-conditions must be specific enough that someone with terminal access (but no project knowledge) could reproduce the starting state.

| Bad | Good |
|-----|------|
| "System is running" | "Application launched via `python main.py` from commit `abc1234` on branch `cr-045/exec`" |
| "Latest code" | "Branch `cr-045/exec` at commit `abc1234`. No uncommitted changes. Python 3.11, dependencies installed per requirements.txt." |
| "Config is set" | "`config.py` has `MAX_RETRIES = 5`, `REQUEST_TIMEOUT = 30`. Verified via `grep MAX_RETRIES src/config.py`." |

**Minimum requirements:**
- Branch and commit hash
- Relevant configuration values
- Environment details that affect behavior (Python version, OS if relevant)
- Any manual setup steps performed before verification

### Steps: Exact Commands, Not Paraphrases

Step instructions must be executable. A reader should be able to copy-paste them and get the same result.

| Bad | Good |
|-----|------|
| "Run the tests" | "Execute: `python -m pytest tests/test_auth.py -v`" |
| "Open the app and try the dropdown" | "1. Launch: `python main.py`\n2. Click the tool selector in the top toolbar\n3. Observe the dropdown menu" |
| "Check the config" | "Execute: `grep -n REQUEST_TIMEOUT src/config.py`" |

**For multi-step instructions**, use numbered sub-steps:

```
1. Launch the application: `python main.py`
2. Navigate to the user management page
3. Click "Create New User"
4. Fill in required fields: username "testuser", email "test@example.com"
5. Click "Submit"
6. Observe the confirmation message and redirect
7. Verify the new user appears in the user list
```

### Observations: Copy-Paste Actual Output

The `step_actual` prompt is where evidence lives. This is the most important part of the VR.

| Bad | Good |
|-----|------|
| "Tests passed" | "```\n$ python -m pytest tests/test_auth.py -v\ntests/test_auth.py::test_valid_token PASSED\ntests/test_auth.py::test_expired_token PASSED\ntests/test_auth.py::test_malformed_token PASSED\n3 passed in 0.42s\n```" |
| "Dropdown appeared" | "Dropdown rendered at position (120, 45). Menu contains 3 items: 'Select', 'Edit', 'Delete'. Font renders at 14px. Background color: #2a2a2a." |
| "It works" | "Auth module validated token in 45ms. Response status: 200 OK with correct user payload. Terminal output:\n```\nAuth: token validated, user_id=42, expires_in=3600s\n```" |

**Rules for observations:**
1. **Copy-paste terminal output** -- do not retype or summarize
2. **Describe visual results specifically** -- positions, colors, counts, text content
3. **Include measurements** -- iteration counts, timing, tolerance values
4. **Note unexpected but acceptable variations** -- "Expected 12 iterations, observed 14; within acceptable range"

### Outcomes: Expected vs. Actual Comparison

The step outcome is Pass or Fail. If Fail, include a brief discrepancy note.

```
Pass
```

or

```
Fail -- Expected 3 menu items but observed 2. "Brush" option missing from dropdown.
```

---

## The Append-Only Response Model

Every response in a VR is permanent. If you need to correct or update a previous response, you **amend** it -- you do not replace it.

### How Amendments Work

```bash
# Navigate to the response you want to amend
qms interact CR-045-VR-001 --goto step_expected.1 --reason "Correcting expected iteration count"

# Record the amended response
qms interact CR-045-VR-001 --respond "Solver converges in fewer than 20 iterations" --reason "Correcting expected iteration count"
```

**What happens in the source data:**
- The original response stays in the list
- The amendment is appended with a reason and timestamp
- In the compiled document, the original renders with ~~strikethrough~~ and the amendment renders normally
- Both entries include attribution lines

**When to amend:**
- You made an error in a previous response
- Conditions changed and a prior statement is no longer accurate
- A reviewer requested clarification during post-review (via `revert` back to execution)

**When NOT to amend:**
- You want to add more detail to the current step -- just include it in the current response
- You want to redo a step -- add a new step iteration via the loop instead

### Why Append-Only Matters

The VR is an evidence record. If responses could be silently replaced, a reviewer could not trust that the evidence reflects what actually happened. The append-only model ensures that the full history is visible: original observation, any corrections, and the reasons for those corrections.

---

## Engine-Managed Commits

The `step_actual` prompt has `commit: true`. This means the engine automatically performs a git commit when you record your observation.

### What Happens

1. You submit your `step_actual` response
2. The engine runs `git add -A` in the project working tree
3. The engine runs `git commit` with an auto-generated message:
   ```
   [QMS] auto-commit | CR-045-VR-001 | step_actual.1 | Evidence capture during VR execution
   ```
4. The engine records the commit hash (e.g., `abc1234`) in the response entry
5. Your response is stored with the commit hash attached

### Why This Matters

The commit hash creates a verifiable link between your observation and the code state. A reviewer can:
- Checkout that commit to see the exact code that produced the observation
- Verify that the code matches what the VR claims was tested
- Confirm that the observation was contemporaneous (not reconstructed later)

### What You Need to Know

- **Do not commit manually before responding to `step_actual`.** The engine handles it.
- **Ensure your working tree is clean** before starting the step (no unrelated uncommitted changes). The engine commits everything.
- **The commit hash appears in the compiled document** next to the attribution line.
- **If you need to do work between steps** (like modifying code), commit that work manually before the engine-managed commit fires.

---

## Common VR Mistakes

### 1. Assertional Evidence

**The mistake:** Writing what you believe to be true instead of what you observed.

| Assertional | Observational |
|-------------|--------------|
| "The feature works correctly" | "Terminal output: `3 passed, 0 failed`" |
| "The widget renders as expected" | "Screenshot: dropdown at (120, 45), 3 items visible, #2a2a2a background" |
| "Performance is acceptable" | "Request handler completed in 45ms (0.045s). Baseline was 38ms (0.038s)." |

**The test:** Could you write this sentence without having run the step? If yes, it is assertional.

### 2. Vague Steps

**The mistake:** Steps that cannot be reproduced by someone else.

| Vague | Reproducible |
|-------|-------------|
| "Test the module" | "Execute: `python -m pytest tests/test_auth.py::test_valid_token -v`" |
| "Verify the UI" | "1. Launch `python main.py`\n2. Navigate to the login page\n3. Enter test credentials\n4. Observe the response" |
| "Check the output" | "Execute: `grep MAX_RETRIES src/config.py` and verify output shows `MAX_RETRIES = 5`" |

### 3. Post-Hoc Filling

**The mistake:** Running all your verification steps first, then filling in the VR prompts from memory afterward.

**Why it is wrong:**
- The `step_expected` must be written *before* you execute the step (it is a prediction, not a description)
- The engine-managed commit on `step_actual` pins the project state at observation time -- if you fill in later, the commit does not match the observation moment
- Memory is unreliable; contemporaneous recording is a fundamental evidence standard

**The correct flow:**
1. Write `step_instructions` (what you will do)
2. Write `step_expected` (what you predict will happen)
3. Execute the step
4. Immediately write `step_actual` (what you observed) -- the engine commits here
5. Write `step_outcome` (Pass or Fail)

### 4. Skipping Pre-Conditions

**The mistake:** Jumping straight to verification steps without documenting the starting state.

**Why it matters:** Without pre-conditions, a reviewer cannot determine whether the verification was conducted under valid conditions. "Tests pass" means nothing if you do not know which branch, which commit, or which configuration was in effect.

### 5. Summarizing Instead of Quoting

**The mistake:** Paraphrasing terminal output or test results instead of copying them.

| Summarized | Quoted |
|------------|--------|
| "All three tests passed" | "```\ntests/test_auth.py::test_valid_token PASSED\ntests/test_auth.py::test_expired_token PASSED\ntests/test_auth.py::test_malformed_token PASSED\n3 passed in 0.42s\n```" |

**When output is very long**, use `--respond --file` to capture it from a file:

```bash
# Capture output to a file
python -m pytest tests/ -v > /tmp/test-output.txt 2>&1

# Respond with file contents
qms interact CR-045-VR-001 --respond --file /tmp/test-output.txt
```

### 6. Mixing Steps and Observations

**The mistake:** Including actions in the observation, or observations in the instructions.

```
step_instructions: "Run pytest and verify 3 tests pass"   <-- wrong: includes expected outcome
step_actual: "Ran pytest, then also checked config.py"      <-- wrong: includes actions not in instructions
```

Keep them separate:
- Instructions: what you will do (actions only)
- Expected: what you predict (outcomes only)
- Actual: what you observed (observations only)

---

## The Reproducibility Standard

> Could someone with terminal access but no project knowledge reproduce this verification?

This is the bar. Every VR should be reproducible by a competent person who:

- Has access to the repository and can checkout the specified commit
- Has the required toolchain installed (as specified in the project's setup documentation)
- Can read and follow written instructions
- Has **no prior knowledge** of the project's architecture, history, or conventions

If your pre-conditions say "use the standard config" -- fail. There is no "standard" for someone unfamiliar with the project. If your instructions say "run the test suite" -- fail. Which test suite? Where? With what flags?

**Self-test:** Before checking in a VR, mentally hand it to someone who just cloned the repo. Could they follow it? If not, add detail.

---

## Checking In and Closing

### Check In

```bash
qms checkin CR-045-VR-001
```

Checkin:
1. Copies your `.interact` session to `.source.json` (permanent record)
2. Compiles the source + template into the final `.md` document
3. Deletes the `.interact` file from your workspace

After checkin, the VR contains the compiled markdown document that reviewers will see.

### Closure

VRs are **cascade-closed** when their parent document closes. You do not close a VR independently. The sequence is:

1. Parent routes for post-review (VR is reviewed as part of this)
2. Parent receives post-approval
3. Parent closes -- VR is automatically cascade-closed

If the VR is still checked out when the parent closes, the engine auto-compiles it before closing.

---

## Reopening a Closed Loop

If you closed the step loop (answered "no" to "more steps?") but then realize you need additional verification steps:

```bash
qms interact CR-045-VR-001 --reopen steps --reason "Additional verification step needed for edge case"
```

This reopens the loop at a new iteration. After completing the new step(s) and answering "no" at the gate again, the cursor returns to where it was before the reopen.

---

## Quick Reference: VR Interaction Commands

| Command | Purpose |
|---------|---------|
| `qms interact DOC_ID` | Show current prompt and guidance |
| `qms interact DOC_ID --respond "value"` | Record response to current prompt |
| `qms interact DOC_ID --respond --file path` | Record response from file |
| `qms interact DOC_ID --progress` | Show fill status of all prompts |
| `qms interact DOC_ID --compile` | Preview compiled markdown |
| `qms interact DOC_ID --goto id --reason "..."` | Amend a previous response |
| `qms interact DOC_ID --cancel-goto` | Cancel amendment, return to position |
| `qms interact DOC_ID --reopen loop --reason "..."` | Add more iterations to closed loop |

---

**See also:**
- [Interactive Authoring](../08-Interactive-Authoring.md) -- Template tag syntax, source data model, engine mechanics
- [VR Reference](../types/VR.md) -- VR type page with full lifecycle and configuration details
- [Execution Policy](../06-Execution.md) -- Evidence requirements, EI table structure
- [Child Documents](../07-Child-Documents.md) -- VR lifecycle within the child document framework
- [Evidence Writing Guide](evidence-writing-guide.md) -- General evidence standards (applicable to VR observations)
- [QMS-Glossary](../QMS-Glossary.md) -- Term definitions
