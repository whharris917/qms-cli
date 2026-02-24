# Frequently Asked Questions

Practical answers to common questions that arise during QMS-governed work. These are the questions people actually ask when they're in the middle of doing something and aren't sure what the right move is.

> **New to the QMS?** Start with [START_HERE.md](START_HERE.md) for a guided walkthrough. Come back here when you hit a specific question.

> **Looking for a term?** See the [QMS-Glossary](QMS-Glossary.md).

> **Tip:** Use Ctrl+F to search for keywords related to your situation.

---

## The Basics (No Shame in Asking)

### Q: What even is a "document" in the QMS? I thought we were writing code.

A QMS document is a formal record that authorizes, tracks, and evidences work. A Change Record (CR) isn't just paperwork — it's the authorization to make a change, the plan for how you'll make it, and the evidence that you made it correctly. Think of it as a combination of a project plan, a work log, and an audit trail. The code you write is *part of* the CR's execution — the CR is the container that gives the code its authorization and traceability.

### Q: What's the difference between "executable" and "non-executable" documents?

**Non-executable** documents (SOP, RS, RTM) define rules or requirements. They get reviewed, approved, and become "effective" (in force). That's it — there's no "execution phase" because there's no work to do beyond writing the document itself.

**Executable** documents (CR, INV, TP, ER, VAR, ADD, VR) authorize and track *work*. They have a planning phase (reviewed and approved before you start), an execution phase (you do the work), and a verification phase (reviewed and approved after you finish). The extra phases exist because the work itself needs oversight, not just the plan.

### Q: What does "EFFECTIVE" mean? I keep seeing it.

EFFECTIVE means the document is approved and currently in force. For an SOP, it means "this is the current procedure — follow it." For an RS, it means "these are the current requirements." It's the QMS equivalent of "this is the live version." An effective document stays effective until it's either revised (creating a new version) or retired.

### Q: What does "pre-approved" mean vs "approved"?

For executable documents, there are two approval gates. **Pre-approved** means the *plan* was reviewed and approved — you're authorized to start work. **Post-approved** means the *completed work* was reviewed and approved — you can close the document. Pre-approval says "this plan is sound." Post-approval says "this execution was sound."

### Q: Why can't I just fix the code and commit it? Why do I need all this process?

Because the QMS provides three things raw commits don't: **authorization** (someone reviewed the plan before you started), **traceability** (you can trace any line of code back to the CR that authorized it), and **verification** (someone confirmed the work was done correctly). This matters when you need to answer "why was this change made?" six months from now, or when you need to prove that a feature was actually tested. The process is the proof.

### Q: What are the three strands? I keep hearing about them.

The QMS's authority is split across three irreducible sources:
1. **CLI code** (mechanism) — the state machines, permissions, and workflow rules. This is how the system works.
2. **Templates** (structure) — what documents look like, what sections they have. This is the shape of documents.
3. **QMS-Policy** (judgment) — when to investigate, what constitutes adequate evidence, how agents should interact. This is the stuff that requires human/AI judgment.

Everything else (these docs, the FAQ, the guides) is educational material that helps you understand and use the three strands. See [QMS-Policy](QMS-Policy.md).

---

## Execution & Evidence

### Q: What if my EI was written incorrectly, but the step passes my original intent?

It depends on how wrong the description is. If it's a minor wording issue (e.g., "Update the config file" when you actually updated a settings module), execute the intent, and note in the execution summary: "EI description said X; actual work was Y; the intent was Z and is satisfied." This is a documentation discrepancy, not a failure.

If the description is materially wrong (e.g., "Add unit tests for module A" but module A doesn't exist and you tested module B instead), mark it **Fail** and create a [VAR](types/VAR.md). The pre-approved plan was flawed and needs formal correction. See the [scope change guide](guides/scope-change-guide.md) for more scenarios.

### Q: What if I discover during execution that an EI is unnecessary?

You cannot silently skip it. The EI was part of the approved scope. Mark it **Fail** and create a [VAR](types/VAR.md) explaining why the task is no longer applicable and confirming that skipping it doesn't affect the overall objectives. A Type 2 VAR is usually appropriate since the parent's remaining work isn't blocked. Yes, this feels like overhead for something obvious — but it's the mechanism that prevents scope from silently disappearing.

### Q: What if I need to do work that was not in my pre-approved plan?

If the new work is minor and directly supports an existing EI (e.g., a helper function needed to implement a planned feature), capture it as part of that EI's evidence. If it's a distinct unit of work that changes the approved scope, create a [VAR](types/VAR.md). If it's completely unrelated to the current document, create a new CR. You cannot add new rows to an already-approved EI table — the static fields are locked.

### Q: What counts as adequate evidence for an EI?

Apply the **third-party reviewer test**: could someone who wasn't present during execution, reading only your evidence, independently conclude the work was done?

**Good evidence:** "Implemented authentication module refactor. Commit `abc1234` on branch `cr-056`. pytest: 42 passed, 0 failed. See CR-056-VR-001 for behavioral verification."

**Bad evidence:** "Done. Tests pass."

The difference is traceability. Good evidence points to specific artifacts. Bad evidence is just an assertion. See the [evidence writing guide](guides/evidence-writing-guide.md).

### Q: Can I update evidence after the fact if I forgot to record it?

Evidence must be contemporaneous — recorded at the time of execution. If you forgot to capture output:

1. **Preferred:** Re-execute the step and capture fresh evidence now, noting "Step re-executed for evidence capture."
2. **If re-execution isn't possible:** Document whatever evidence is available and note the gap honestly.

Do NOT fabricate evidence, backdate observations, or write "tests passed" from memory. Reviewers will assess whether the available evidence is sufficient. An honest gap is better than fabricated evidence. See [QMS-Policy](QMS-Policy.md) Section 5.

### Q: When do I need a VR vs just recording evidence in the EI table?

**EI table evidence** is for work that produces a single verifiable artifact: a commit hash, a test suite result, a document reference.

**VR (Verification Record)** is for structured behavioral verification — testing a capability through a multi-step procedure where each step has expected and actual results. If you need to launch the app, perform a sequence of actions, and verify specific behaviors at each step, that's a VR.

The VR flag is set during planning (pre-approval). If an EI has `VR=Yes`, you must create a VR child document. See the [VR authoring guide](guides/vr-authoring-guide.md).

### Q: What if my VR reveals the feature doesn't work as expected?

Record the actual result honestly — the VR step outcome is **Fail**. Back in the parent document, the associated EI is also Fail. Create a [VAR](types/VAR.md) to handle the fix. The original VR's failure evidence is preserved forever (the audit trail is append-only). After fixing the code, you may need a new VR to verify the fix works. Never overwrite or delete a failed VR result.

### Q: What's the difference between "Pass" and "Fail" for an EI?

**Pass** = the task was completed as described in the Task Description. **Fail** = it wasn't, for any reason. A Fail doesn't mean you did something wrong — it means the plan and reality diverged. Every Fail requires a child document (VAR for non-test, ER for test) explaining what happened and how it's being resolved. An EI with no outcome recorded is not acceptable.

### Q: Do I need to commit after every single EI?

Not necessarily after every EI, but you need traceable evidence for each one. If multiple EIs are completed in a single commit, reference that commit from each EI's execution summary. The important thing is that every EI's evidence points to something verifiable. Check in the document frequently — that creates recovery points and makes your progress visible.

---

## Failure Handling

### Q: When do I create a VAR vs an ER?

**ER** = test failure (during TP/TC execution). **VAR** = everything else (during CR, INV, VAR, ADD execution). That's the rule. ERs re-execute the entire test case. VARs encapsulate resolution work with their own review/approval cycle. See the [failure decision guide](guides/failure-decision-guide.md).

### Q: When should I choose Type 1 vs Type 2 VAR?

Ask: **Would I be uncomfortable closing the parent while this VAR is still in execution?**

- **Yes** → Type 1. The parent waits for the VAR to fully close.
- **No** → Type 2. The parent can close once the VAR is pre-approved.

Examples: A code fix that must be merged before the parent CR's merge gate = Type 1. A follow-on documentation update = Type 2. **When in doubt, Type 1.** It's always the safe default.

### Q: What if a Type 2 VAR should have been Type 1?

Treat it as Type 1 going forward — don't close the parent until the VAR is fully closed, even if it's classified as Type 2. If you catch this before pre-approval, revise the classification. If you catch it after pre-approval, the safest path is behavioral: just wait for the VAR to close before closing the parent. Raise the concern with QA during review so it's documented.

### Q: Can I convert a Type 1 VAR to Type 2 (or vice versa)?

The type is a static field — locked after pre-approval. Before pre-approval, change it freely. After pre-approval, changing it technically requires a child VAR documenting the deviation. In practice, it's usually simpler to work within the existing classification. If the mismatch is causing real problems, discuss with the Lead.

### Q: What if the re-test in my ER also fails?

Create a **nested ER** — an ER that's a child of the original ER (e.g., `CR-005-TP-ER-001-ER-001`). Each ER in the chain documents one failure and its resolution attempt. There's no limit to nesting depth, but if you're three ERs deep, something systemic is probably wrong and an [INV](types/INV.md) may be warranted.

### Q: What if I discover a problem after the parent document has closed?

Create an **ADD** (Addendum Report). ADDs are specifically for post-closure corrections. The parent must be CLOSED (the CLI enforces this). The ADD goes through its own full lifecycle. The parent document stays closed — you're supplementing it, not reopening it. See [types/ADD.md](types/ADD.md).

### Q: When does a failure warrant an INV instead of a VAR?

Use an INV when the failure is **systemic, unclear, or involves a process breakdown**. A VAR handles "I couldn't do step 3 because the API changed." An INV handles "Why do our tests keep missing this class of bug?" or "Why did a document get approved with missing evidence?" If you see a pattern — multiple VARs pointing to the same root cause — that's a strong signal for an INV. See [Deviation Management](05-Deviation-Management.md).

### Q: What happens to in-progress child documents if the parent needs to close?

| Child Type | Parent can close when child is... |
|------------|----------------------------------|
| Type 1 VAR | CLOSED |
| Type 2 VAR | PRE_APPROVED or later |
| ER | CLOSED |
| VR | CLOSED (auto-closed when parent closes) |
| ADD | N/A — ADDs are created *after* the parent closes |

The CLI checks these prerequisites automatically. If a child isn't ready, the close command will fail with an explanation.

### Q: I created a VAR but now I think an ADD would have been more appropriate (or vice versa). What do I do?

If the VAR/ADD is still in DRAFT (never approved), cancel it and create the correct document type. If it's already been pre-approved or is in execution, finish it as-is — the content is what matters, not the document type label. Note the observation in the execution comments for the record.

---

## Review & Approval

### Q: What happens if a reviewer requests updates?

The `request-updates` outcome **blocks the approval gate**. You cannot route for approval while any reviewer has outstanding requested updates. Here's the path:

1. Read the reviewer's comment: `qms comments {DOC_ID}`
2. Withdraw from review (or it may already be back in DRAFT/IN_EXECUTION)
3. Check out the document
4. Address the feedback
5. Check in
6. Route for review again

You must get ALL reviewers to recommend before you can route for approval.

### Q: Can I route for approval if one reviewer recommended and another requested updates?

No. **Every** reviewer must recommend. Even one `request-updates` blocks the gate. This is enforced by the CLI — there's no override. Address the feedback, re-route for review, get everyone to recommend, then route for approval. See [Workflows](03-Workflows.md).

### Q: What if I disagree with a reviewer's feedback?

Two options:
1. **Discuss it.** Explain your reasoning. Most disagreements resolve once the reviewer understands context they didn't have.
2. **Escalate to the Lead.** If you genuinely believe the feedback is wrong, the Lead can direct QA to reassign or provide guidance.

What you **cannot** do: ignore the feedback and force the document forward. The CLI won't let you, and even if it could, that would defeat the purpose of review.

### Q: What does QA look for vs what do TUs look for?

| Reviewer | Asks... |
|----------|---------|
| **QA** | "Is this document complete? Is evidence adequate? Was the process followed? Is scope consistent?" |
| **TU** | "Is the technical approach sound? Will this actually work? Are there risks or edge cases being missed?" |
| **BU** | "Is this good for the user? Does it add product value? Is it usable?" |

QA catches structural and procedural gaps. TUs catch technical flaws. Both are required for the approval gate.

### Q: Can I withdraw from review to make changes?

Yes. Withdrawal returns the document to its previous state (DRAFT for pre-review, IN_EXECUTION for post-review). You can also just check out the document — if you're the owner and the doc is in review, checkout performs an automatic withdrawal. Withdraw early if you know changes are needed — don't wait for reviewers to formally request updates on something you already know is wrong.

### Q: What if the approval gate blocks me and I think the review was wrong?

The gate **cannot be overridden**. There is no "force approve" mechanism, and that's intentional. Your path is through the Lead, not around the system. Explain your position, provide your reasoning. The Lead can direct QA to reassign the review or the reviewer can resubmit. But the gate stays.

### Q: Can I be both the author and a reviewer of the same document?

No. Review independence means the person who wrote the document cannot review it. The CLI will block a self-review. This separation exists because the author is too close to the work to provide an independent assessment.

---

## Scope & Planning

### Q: What if my pre-approved scope turns out to be too broad?

Every approved EI must have a recorded outcome. You can't just ignore the ones you don't need. For each unnecessary EI, mark it **Fail** and create a VAR (a single VAR can cover multiple dropped items). A Type 2 VAR is usually appropriate. This is a signal to write smaller, more focused CRs in the future.

### Q: What if my pre-approved scope turns out to be too narrow?

The additional work needs a container. If it's related to this document's objectives, create a VAR. If it's independent work, create a new CR. Do not silently expand scope. The pre/post approval structure only provides assurance if execution matches the plan.

### Q: Can I add EIs during execution?

No. The EI table's static fields are locked at pre-approval. You cannot add, remove, or modify task descriptions in an approved document. New work goes into child documents (VARs with their own EIs). This immutability is what makes the system auditable.

### Q: What is scope handoff and when do I need it?

Scope handoff is the explicit transfer of responsibility from parent to child document. It answers three questions:
1. What did the parent accomplish so far?
2. What does the child absorb?
3. Was anything lost in the transfer?

You need it whenever creating a VAR or ADD. It prevents the failure mode where work silently disappears between parent and child.

### Q: How do I handle a scope item that's technically complete but doesn't match the plan?

The EI outcome is **Fail** — the Task Description defines the approved scope, and the work doesn't match it. Create a VAR documenting: what was approved, what was built, why they differ, and whether the actual result is acceptable. The VAR's review determines whether the implementation is adequate or needs rework.

### Q: What if execution reveals the requirements themselves were wrong?

This is bigger than a VAR. If the RS needs correction, you'll need either a separate CR to update the RS, or the current CR's VAR can include RS updates. Either way, an RS change requires its own review/approval cycle. Coordinate with the Lead — RS changes can ripple through RTM, other CRs, and verification plans.

### Q: My pre-approved plan calls for approach X, but during execution I realized approach Y is better. Can I just use approach Y?

If the *outcome* is the same (the EI's objective is met) and only the *method* differs, execute approach Y and document the discrepancy in the execution summary: "Plan specified approach X; approach Y was used because [reason]; outcome matches approved intent."

If approach Y changes the *outcome* or affects other EIs, that's a scope change — create a VAR.

---

## Code Governance

### Q: What is a qualified commit and when do I need one?

A qualified commit is a specific git commit on the execution branch where CI passes. It's the moment your code is verified. The commit hash gets recorded in the RTM as evidence that requirements are satisfied. You need one for every code CR that goes through the merge gate. Not every commit during development is qualified — only the final CI-verified one. See [Code Governance](09-Code-Governance.md).

### Q: What if CI fails on my execution branch?

Fix the code and push again. CI failures during development are normal and don't require any QMS action. The qualified commit is the one that eventually passes, not every intermediate attempt. However, if CI failures reveal that your approach is fundamentally broken and you need to deviate from the approved plan, *that* deviation requires a VAR.

### Q: Can I merge to main before the CR is fully closed?

Yes — in fact, merging typically happens *during* execution (as one of the final EIs), before post-review and closure. But you cannot merge before qualification is complete: RS must be EFFECTIVE, RTM must be EFFECTIVE, and CI must pass. The typical sequence is: qualify → merge → post-review → close. See [SDLC](10-SDLC.md).

### Q: What if I need to make a hotfix that can't wait for full CR governance?

There is no fast-track mechanism. Even urgent fixes need a CR. However, a narrowly-scoped CR with a clear fix can move through the system quickly — the bottleneck is usually scope complexity, not process overhead. Coordinate with the Lead and QA to prioritize review. After the fix, consider an INV to understand why the defect wasn't caught earlier.

### Q: When do I need to update the RS and RTM?

Whenever your CR adds, modifies, or removes a system capability. New features = new requirements in RS + new verification evidence in RTM. Implementation-only changes (same behavior, different code) may not need RS changes, but the RTM's qualified commit hash still needs updating. When in doubt, update both.

### Q: Why can't I use squash merges?

Squash merges rewrite commit history into a single commit on main. The QMS references specific commit hashes as evidence (in RTMs, CRs, VRs). If you squash, those referenced commits become unreachable from main's history, breaking the traceability chain. Always use standard merges (or fast-forward) when merging execution branches. See [Code Governance](09-Code-Governance.md).

### Q: What if I accidentally committed to main instead of an execution branch?

This is a deviation. The main branch should only receive changes through reviewed PRs from execution branches. If it's a small, recent commit, coordinate with the Lead to assess options (which may include reverting and re-applying through a proper CR). If it's already pushed and others have pulled, an INV may be needed to document the deviation and prevent recurrence.

---

## Document Management

### Q: What if I checked out a document but don't want to make changes anymore?

Check it back in: `qms checkin {DOC_ID}`. Even if you made no changes. Leaving a document checked out blocks everyone else from editing it. Check your workspace periodically with `qms workspace` to make sure you don't have orphaned checkouts.

### Q: What if someone else needs to edit a document I have checked out?

Check it in first. The QMS enforces exclusive checkout — only one user at a time. If you're mid-work, check in what you have (even if incomplete), let the other user make their changes, then check out again. There's no mechanism to transfer checkouts between users.

### Q: Can I work on multiple documents simultaneously?

Yes. Each checkout is independent. Use `qms workspace` to see everything you have checked out. Be mindful of dependencies — if you're editing both a CR and its child VAR, make sure they're consistent before checking either in.

### Q: What's the difference between cancel and retire?

| | Cancel | Retire |
|---|--------|--------|
| **For** | Documents that were never approved (v < 1.0) | Documents that were once effective/closed |
| **Effect** | Permanently deleted (including metadata and audit trail) | Archived and marked RETIRED (audit trail preserved) |
| **Use case** | Abandoning drafts, false starts, duplicates | Superseded procedures, obsolete specs |
| **Reversible?** | No — everything is deleted | No — but the archive is preserved |

### Q: When should I check in vs keep working in my workspace?

**Check in frequently.** After each completed EI, after significant progress, before long breaks. Check-ins create recovery points, make your progress visible to others, and generate audit trail entries. There's no penalty for frequent check-ins — only risk in infrequent ones.

### Q: I see "checked_out: true" in a document's status but nobody seems to be working on it. What do I do?

This is a stale checkout — someone checked out the document and didn't check it back in. If you're an administrator, you can use `qms fix {DOC_ID}` to clear the orphaned checkout flag. If you're not an administrator, ask the Lead to clear it. Don't try to work around it by manually editing files.

### Q: What is the workspace and where does my checked-out document live?

When you check out a document, the CLI copies it to `.claude/users/{your-username}/workspace/{DOC_ID}.md`. This is your personal working copy. You edit this file directly (or via interactive authoring for VRs). When you check in, the CLI copies your workspace version back to the canonical location in `QMS/{TYPE}/` and removes the workspace copy. Use `qms workspace` to list everything currently in your workspace. See [Document Control](02-Document-Control.md) for the full directory structure.

### Q: What happens when I check out an effective document?

A new draft is created at version N.1 (one minor revision above the current effective version). The effective version stays in place — it remains in force while you work on the draft. When the draft is eventually approved, it becomes the new effective version and the old one is archived. The system never has a gap where no effective version exists.

---

## Interactive Authoring (VR)

### Q: The VR prompt is asking me something I don't understand. What do I do?

Read the guidance text — it's the prose between the template tags that explains what the prompt is asking for and why. If the guidance text isn't sufficient, check the [VR authoring guide](guides/vr-authoring-guide.md) for examples of good responses. If you're still stuck, ask the Lead.

### Q: I made a mistake in a VR response. Can I go back and fix it?

Yes, but you can't overwrite the original. Use `qms interact {DOC_ID} --goto {prompt_id} --reason "explanation"` to amend a previous response. The original response is preserved with strikethrough in the compiled document, and your new response is appended with the reason for the amendment. This creates a visible amendment trail — which is intentional (append-only data integrity).

### Q: The VR gate prompt is asking me yes/no but I want to add another step. What do I do?

If the gate is "Are there more steps?" answer **Yes** to continue the loop and add another step. Answer **No** when you're truly done. If you closed the loop too early and need to add more steps, use `qms interact {DOC_ID} --reopen {loop_name} --reason "explanation"` to reopen the loop.

### Q: My VR has a "commit: true" prompt. What does that mean?

When you respond to that prompt, the interaction engine automatically creates a git commit capturing the project state at that moment. This pins your observation to a specific code state — it's evidence that what you observed was real at that commit. You don't need to do anything special; the engine handles the commit and records the hash in your response.

### Q: What happens to my VR when the parent document closes?

VRs are automatically closed (cascade close) when their parent closes. If you have a VR still checked out when the parent closes, the CLI auto-compiles it from its source data and closes it. You don't need to manually close VRs.

---

## Process Philosophy

### Q: Why does the QMS feel like so much overhead for a small project?

Because the QMS is doing two things: governing the project AND experimenting with recursive self-improvement. The process overhead you feel is partially the cost of building the methodology itself. Once the process stabilizes, the overhead drops — most of the "weight" is in learning the system, not in operating it. The QMS is designed to discover its own inefficiencies and fix them (via INVs and CAPAs).

### Q: Why can't we just use GitHub issues and PRs like normal projects?

PRs provide code review. The QMS provides something broader: **authorization** (the CR approves the work before it starts), **scope control** (the approved plan can't be silently changed), **traceability** (every artifact traces to its authorization), and **process learning** (failures are investigated, and the process improves). GitHub issues/PRs are a subset of what the QMS provides. The QMS uses PRs as part of the merge gate.

### Q: What's the point of pre-approval if I'm going to do the work anyway?

Pre-approval catches bad plans before work begins. It's cheaper to fix a plan than to fix completed work. Pre-approval also establishes the scope contract — post-review can then verify "did you do what you said you'd do?" without that baseline, post-review is just "does this look okay?" which is a much weaker check.

### Q: Why are Investigations not punishment?

An INV is a learning mechanism, not a blame mechanism. It asks "what went wrong in the *process* that allowed this to happen?" not "who screwed up?" The output is always a process improvement (CAPA), never a personnel action. If the process has a gap that let a problem through, the INV fixes the gap. If the process is fine and someone made a one-time error, a VAR is sufficient — no INV needed.

### Q: Can the QMS itself be wrong?

Yes. That's the whole point of the recursive governance loop. When the QMS produces a bad outcome, an INV analyzes the failure, and CAPAs improve the process — using the same document control mechanisms. The QMS governs its own evolution. If a procedure is wrong, a CR revises it. If a procedure is missing, a CR creates one. The system is designed to learn from its own mistakes.

---

## Navigation

| Topic | Document |
|-------|----------|
| Guided walkthrough | [START_HERE.md](START_HERE.md) |
| Document types and metadata | [Document Control](02-Document-Control.md) |
| State machines and transitions | [Workflows](03-Workflows.md) |
| Change Records | [Change Control](04-Change-Control.md) |
| Investigations and CAPAs | [Deviation Management](05-Deviation-Management.md) |
| Execution and evidence | [Execution](06-Execution.md) |
| Child documents (ER, VAR, ADD, VR) | [Child Documents](07-Child-Documents.md) |
| Interactive authoring (VRs) | [Interactive Authoring](08-Interactive-Authoring.md) |
| Code governance and merge gate | [Code Governance](09-Code-Governance.md) |
| RS, RTM, and SDLC | [SDLC](10-SDLC.md) |
| Agent roles and communication | [Agent Orchestration](11-Agent-Orchestration.md) |
| CLI commands | [CLI Reference](12-CLI-Reference.md) |
| Core policy decisions | [QMS-Policy](QMS-Policy.md) |
| Term definitions | [QMS-Glossary](QMS-Glossary.md) |

### Q: My question isn't answered here. What do I do?

Raise it with the Lead. Novel situations arise — when they do, the Lead and QA will determine the appropriate path. Document the situation and resolution so it can be added to this FAQ.
