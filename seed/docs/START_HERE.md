# What Should I Do Next?

Start with what's in front of you right now, then follow the link.

> **First time here?** The QMS (Quality Management System) tracks all changes to the project through controlled documents. You create a document describing what you want to do, it gets reviewed, you do the work, and it gets reviewed again. That's the core loop. Everything else is details.

---

## What's your situation?

- **I need to make a change to the codebase or documents** → [I need to make a change](#i-need-to-make-a-change)
- **I'm in the middle of executing a document** → [I'm executing](#im-executing)
- **Something went wrong** → [Something went wrong](#something-went-wrong)
- **I have a document to review** → [I need to review something](#i-need-to-review-something)
- **I need to approve or reject a document** → [I need to approve or reject](#i-need-to-approve-or-reject)
- **A document got rejected and I don't know what to do** → [My document was rejected](#my-document-was-rejected)
- **I finished a document and need to wrap it up** → [I'm done executing](#im-done-executing)
- **I'm stuck and nothing here matches** → [I'm lost](#im-lost)
- **I just want to look something up** → [Quick reference](#quick-reference)

---

## I need to make a change

**What kind of change?**

- **Code change (new feature, bug fix, refactor)** → You need a CR (Change Record). A CR describes what you're changing and why, gets reviewed, then you do the work.
  - [What goes in a CR](04-Change-Control.md) | [CR reference](types/CR.md) | [How to route it](guides/routing-quickref.md)

- **Update an SOP, template, or process document** → You still need a CR to authorize the change. One of the CR's execution items will be "check out and revise SOP-XXX."
  - [Change Control](04-Change-Control.md)

- **Fix something that was missed after a document closed** → You need an ADD (Addendum Report). ADDs are for "we closed this, then realized we missed something."
  - [More on ADDs](#i-closed-a-document-but-found-a-problem) | [ADD reference](types/ADD.md)

- **I'm not sure if this needs a CR** → Ask yourself: does this change anything under QMS control? That includes code in governed submodules, documents in `QMS/`, and templates in `QMS/TEMPLATE/`. If yes, you need a CR. Things that do NOT need a CR: session notes, QMS-Docs, and project documentation files outside `QMS/`.

> **Common mistake:** Starting to write code before creating a CR. All code changes must be authorized by a CR. Create the CR first, get it pre-approved, then start coding.

---

## I'm executing

You have a pre-approved document (CR, INV, VAR, ADD, etc.) and you're doing the work described in it.

**What's happening?**

- **Everything is going fine, I just need to record my work** → Each EI (Execution Item) needs evidence in the "Execution Summary" column: what you did, a commit hash or artifact reference, and Pass/Fail.
  - [How to write good evidence](guides/evidence-writing-guide.md)

- **This EI has "Yes" in the VR column** → You need to create a VR (Verification Record) — a structured test that proves the feature works. The VR walks you through prompts interactively.
  - [VR authoring guide](guides/vr-authoring-guide.md) | [VR reference](types/VR.md)

- **A step failed** → Don't panic. Go to [Something went wrong](#something-went-wrong).

- **I need to do work that wasn't in my plan** → You cannot silently add work to a pre-approved document. Go to [My scope needs to change](#my-scope-needs-to-change).

- **My EI says one thing but I need to do something slightly different** → Go to [My scope needs to change](#my-scope-needs-to-change).

- **I want to skip an EI because it turned out to be unnecessary** → You cannot skip it. Go to [My scope needs to change](#my-scope-needs-to-change).

- **I'm done with all EIs** → Go to [I'm done executing](#im-done-executing).

> **Common mistake:** Finishing all the work and THEN filling in the evidence. Evidence must be recorded as you go (contemporaneously), not reconstructed from memory afterward.

---

## I'm done executing

You've completed all EIs in your document. Now what?

**Before you route for post-review, check ALL of these:**

- [ ] Every EI has an outcome recorded (Pass or Fail)
- [ ] Every Pass EI has traceable evidence (commit hash, document ID, test output — not just "done")
- [ ] Every Fail EI has a child document attached (VAR or ER)
- [ ] All Type 1 VARs are CLOSED
- [ ] All Type 2 VARs are at least PRE_APPROVED
- [ ] Every EI with VR=Yes has a completed VR document
- [ ] The execution summary section is filled in
- [ ] You've checked in the document

**For code CRs, also check:**

- [ ] RS (Requirements Specification) is EFFECTIVE
- [ ] RTM (Requirements Traceability Matrix) is EFFECTIVE with real commit hash (not "TBD")
- [ ] Execution branch has been merged to main (standard merge, NOT squash)
- [ ] Merge commit hash is recorded in your evidence

If anything is missing, fix it before routing. Routing with gaps guarantees a rejection.

- [Full post-review checklist](guides/post-review-checklist.md)
- [How to route](guides/routing-quickref.md)

> **Common mistake:** Routing for post-review while child documents (VARs, VRs) are still open. Check their status first.

---

## Something went wrong

**Take a breath. Failures are normal and the QMS has a path for every one of them.**

**What kind of failure?**

- **A test step failed (during TP/TC execution)** → Create an **ER** (Exception Report). The ER re-executes the entire test case from scratch, not just the failed step — because the test script itself might be wrong.
  - [ER reference](types/ER.md) | [Failure decision guide](guides/failure-decision-guide.md)

- **An execution item failed (during CR, INV, or other non-test execution)** → Create a **VAR** (Variance Report). But first, decide [which VAR type](#which-var-type).
  - [VAR reference](types/VAR.md) | [Failure decision guide](guides/failure-decision-guide.md)

- **I closed a document and then found a problem** → [I closed a document but found a problem](#i-closed-a-document-but-found-a-problem)

- **This keeps happening / it's not just my document** → You might need an **INV** (Investigation). Go to [Do I need an investigation?](#do-i-need-an-investigation)

- **I don't know which type of failure document to create** → Use this table:

| Situation | Document | Why |
|-----------|----------|-----|
| Test step failed | ER | Test-specific, re-executes test case |
| Non-test EI failed | VAR | Encapsulates resolution work |
| Problem found after closure | ADD | Post-closure correction |
| Systemic / recurring issue | INV | Root cause analysis needed |

Still unsure? → [Failure decision guide](guides/failure-decision-guide.md) has a full flowchart.

> **Common mistake:** Ignoring a failure and moving on. Every failure must be formally documented, even if the fix is trivial. The document trail is how we know it was fixed.

---

## Which VAR type?

**The question:** Can the parent document close without this fix being 100% proven?

```
Is the fix critical to the parent's objectives?
├── YES → Type 1 (parent waits for VAR to fully close)
├── NO, the variance is contained and understood → Type 2 (parent can close after VAR is pre-approved)
└── I'M NOT SURE → Type 1 (this is always the safe default)
```

**Examples:**

| Scenario | Type | Reasoning |
|----------|------|-----------|
| Code fix that must be merged before parent CR's merge gate | Type 1 | Parent can't merge without the fix |
| Documentation update that can happen anytime | Type 2 | Parent's code objectives are met |
| Bug in a non-critical path discovered during execution | Type 2 | Contained, understood, parent can close |
| Architectural flaw that undermines the change | Type 1 | Parent's objectives are at risk |

> **Rule of thumb:** If you'd be uncomfortable closing the parent while the VAR is still in execution, it's Type 1.

---

## I closed a document but found a problem

**How serious is it?**

- **Something was missed or needs correction, but the original closure was fine at the time** → Create an **ADD** (Addendum Report) against the closed parent. The ADD has its own full lifecycle. The parent stays closed.
  - [ADD reference](types/ADD.md)

- **The closure itself was wrong — evidence was inadequate or a scope item was missed** → This is a quality event. Someone approved something that shouldn't have been approved.
  - [Do I need an investigation?](#do-i-need-an-investigation)

> **Key distinction:** ADDs are "we legitimately didn't know about this." Investigations are "we should have caught this."

---

## Do I need an investigation?

**The threshold question:** Did something go wrong in a way that could happen again?

```
Could this happen again?
├── YES, or I don't know → INV
│   ├── Root cause isn't obvious
│   ├── The same kind of failure has occurred before
│   └── A procedure was followed but produced wrong results
├── NO, one-time mechanical error → VAR or ADD (no INV needed)
│   ├── Typo in a document
│   ├── One-off tool misconfiguration
│   └── Obvious user error with obvious fix
└── QA says it needs an INV → Create the INV (QA's call)
```

- [Deviation Management](05-Deviation-Management.md) | [INV reference](types/INV.md)

> **Don't be afraid of Investigations.** An INV isn't punishment — it's the mechanism for making the process better. If something is broken enough to investigate, it's broken enough that fixing it makes everyone's life easier.

---

## My scope needs to change

**The golden rule:** Pre-approved scope is a contract. You can't unilaterally change it.

| Situation | What to do |
|-----------|------------|
| An EI is unnecessary | Mark it **Fail**, create a Type 2 VAR explaining why it's not needed. You cannot delete or skip an EI. |
| I need to do extra work | Create a VAR (if related to this document) or a new CR (if independent). Do not add rows to the EI table. |
| My EI description is wrong but I know what was intended | Execute the intent. In the execution summary, document what was written vs what you actually did and why. This is a documentation discrepancy, not a scope failure. |
| My EI description is wrong AND the intent was wrong | **Stop.** Create a Type 1 VAR. The pre-approved plan was flawed. |
| Scope is too broad (can't finish everything) | Every unfinished EI needs Fail + VAR. Consider smaller CRs in the future. |
| Scope is too narrow (need more work) | VAR for related work. New CR for unrelated work. |

- [Scope change guide](guides/scope-change-guide.md)

> **The hardest rule to internalize:** You cannot silently drop an EI. Even if everyone agrees it's unnecessary. Even if the fix is obvious. The approved scope was reviewed and agreed to — changing it requires a paper trail. This isn't bureaucracy for its own sake; it's how we prevent scope items from silently disappearing.

---

## I need to review something

**Step 1: Check your inbox.** The inbox tells you what's assigned to you and what type of review is needed.

**Step 2: Read the document.** All of it. Not just the parts you think are relevant to your domain.

**Step 3: Decide your outcome.** You have exactly two choices:

| Outcome | When to use | What happens |
|---------|-------------|--------------|
| **Recommend** | The document is acceptable. You may have minor preferences but nothing is *wrong*. | Document moves toward approval. |
| **Request updates** | Something needs to change before this should proceed. | **Blocks** the approval gate. Author must revise and re-route. |

**The key distinction:** "I would do it differently" → **recommend**. "This is incorrect/incomplete/will cause problems" → **request updates**.

**What to focus on (by role):**

| Role | Focus area | You're asking... |
|------|------------|-----------------|
| **QA** | Process compliance, scope, evidence quality, completeness | "Is this document complete and correct as a QMS artifact?" |
| **TU** | Technical accuracy in your domain | "Will this actually work? Are there technical risks?" |
| **BU** | User experience, product value | "Is this good for the user? Does it add value?" |

- [Full review guide](guides/review-guide.md)

> **Common mistake:** Requesting updates for style preferences. If the code works, the evidence is adequate, and the approach is sound — even if you'd structure it differently — that's a recommend.

---

## I need to approve or reject

**Approval is not review.** Review asks "is this acceptable?" Approval asks "am I willing to put my name on this?"

| Decision | When | What you do |
|----------|------|-------------|
| **Approve** | You're confident the document is ready | Approve. No comment required. |
| **Reject** | Something must be fixed | Reject with a comment explaining exactly what's wrong. The document goes back to its reviewed state and must go through another full review cycle. |

**If you're unsure → reject.** It is always better to send something back than to approve something you're not confident in. Rejections are normal and expected.

- [Workflow details](03-Workflows.md)

> **Common mistake:** Approving because the review was positive. Review and approval are independent judgments. Even if all reviewers recommended, you can still reject at approval if you see a problem they missed.

---

## My document was rejected

**This is normal. Don't panic.**

A rejection means an approver found something that needs to be fixed. Here's what to do:

1. **Read the rejection comment.** Use `qms comments {DOC_ID}` to see what the approver said.
2. **Check out the document.** Make the requested changes.
3. **Check it in.**
4. **Route for review again.** Yes, the full review cycle — not straight to approval. This is enforced by the CLI.
5. **After all reviewers recommend again**, route for approval.

You cannot skip re-review and go straight to re-approval. The CLI will block you. This exists because the changes you made in response to rejection need to be reviewed too.

> **Common mistake:** Getting frustrated and trying to route directly to approval after fixing the issue. The system requires a full review → approval cycle after rejection. Every time, no exceptions.

---

## I'm lost

**Try these in order:**

1. **Check your inbox** — `qms inbox`. You may have pending review or approval tasks assigned to you.
2. **Check your workspace** — `qms workspace`. You may have documents checked out that need attention.
3. **Check active document status** — `qms status {DOC_ID}` for any document you're working on. Is it waiting for you?
4. **Check your project's planning documents** — these have the current project focus and forward plan.
5. **Ask the Lead** — if none of the above clarifies your next move.

> **You are not expected to figure everything out yourself.** The QMS is complex. Asking for help is always the right call when you're unsure.

---

## Quick reference

| I want to... | Go to... |
|--------------|----------|
| Understand the QMS at a high level | [Overview](01-Overview.md) |
| Look up a term I don't recognize | [QMS-Glossary](QMS-Glossary.md) |
| Understand all the document types | [Document Control](02-Document-Control.md) |
| See a lifecycle diagram | [Lifecycle Quickref](guides/document-lifecycle-quickref.md) |
| Know what CLI command to run | [CLI Reference](12-CLI-Reference.md) |
| See what status I'm in and what I can do next | [Routing Quickref](guides/routing-quickref.md) |
| Write good execution evidence | [Evidence Writing Guide](guides/evidence-writing-guide.md) |
| Figure out what to do when something fails | [Failure Decision Guide](guides/failure-decision-guide.md) |
| Create and fill out a VR | [VR Authoring Guide](guides/vr-authoring-guide.md) |
| Prepare for post-review | [Post-Review Checklist](guides/post-review-checklist.md) |
| Handle a scope change mid-execution | [Scope Change Guide](guides/scope-change-guide.md) |
| Review a document well | [Review Guide](guides/review-guide.md) |
| Find answers to common questions | [FAQ](FAQ.md) |
| Read the core policy decisions | [QMS-Policy](QMS-Policy.md) |
| Understand how agents work together | [Agent Orchestration](11-Agent-Orchestration.md) |
