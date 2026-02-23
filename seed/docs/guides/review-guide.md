# Review Guide

A practical reference for document authors and reviewers. Pull this up when preparing a document for review, conducting a review, or handling review feedback.

---

## For Authors (claude)

### Pre-Review Checklist

Before running `qms route {DOC_ID} --review`, verify:

- [ ] **No placeholders remain.** All `{{DOUBLE_CURLY}}` author-time placeholders are replaced with real content. Execution-time `[SQUARE_BRACKET]` placeholders should still be present in sections 10-12 of executable documents.
- [ ] **All required sections populated.** For CRs, sections 1-9 must be complete. For other types, all static content must be written.
- [ ] **Scope is fully stated.** The document describes everything it intends to accomplish. Reviewers cannot evaluate unstated scope.
- [ ] **Impact assessment is honest.** List affected files, documents, and systems. Missing an impact area will come back as a request-updates.
- [ ] **revision_summary is accurate.** Reflects the current revision's changes, not a leftover from a prior version.
- [ ] **Document is checked in.** If you are checked out, routing will auto-checkin first, but verify content is final before routing.

### What Happens During Review

1. **QA receives the routing notification** in their inbox.
2. **QA assigns Technical Unit reviewers** based on the document's scope (e.g., the appropriate TU for the affected domain).
3. **Each reviewer evaluates independently.** You will not know intermediate results until all reviewers finish.
4. **The status moves to REVIEWED** (or POST_REVIEWED) automatically once all assigned reviewers submit their outcome.

You cannot influence the review while it is in progress. If you realize you need to make changes, [withdraw](#when-to-withdraw) the document.

### Handling Request-Updates Feedback

If any reviewer submits `request-updates`, the approval gate is blocked. To proceed:

1. **Read the comments.** Use `qms comments {DOC_ID}` to see all review feedback.
2. **Check out the document.** `qms checkout {DOC_ID}`
3. **Address every point raised.** Do not cherry-pick -- each comment needs a response in the document or an explanation of why it does not apply.
4. **Update the revision_summary.** State what changed (e.g., `"Addressed reviewer feedback: clarified impact on auth module"`).
5. **Check in.** `qms checkin {DOC_ID}`
6. **Re-route for review.** `qms route {DOC_ID} --review` -- the full review cycle restarts.

### Handling Conflicting Reviewer Feedback

When two reviewers give contradictory guidance:

| Situation | Action |
|-----------|--------|
| TU-A says "add feature X" and TU-B says "remove feature X" | Address both in revision; explain your reasoning. Both reviewers re-evaluate independently on the next cycle. |
| QA and a TU disagree on process vs. technical interpretation | Prioritize QA on process matters, TU on technical matters. If genuinely ambiguous, escalate to the Lead. |
| Feedback conflicts with approved SOPs | SOP takes precedence. Note the conflict in your revision and cite the relevant SOP section. |

**Do not attempt to mediate between reviewers.** Address each reviewer's feedback independently. Let the re-review cycle resolve conflicts naturally. If the conflict persists across cycles, escalate to the Lead.

### When to Withdraw

Use `qms withdraw {DOC_ID}` (or simply `qms checkout {DOC_ID}` which auto-withdraws) when:

- You discover an error after routing but before reviews complete
- You need to make a substantive change that would invalidate in-progress reviews
- A reviewer informally tells you they will request updates and you want to preempt the cycle

**Do not withdraw** just to avoid a request-updates result. The review record is part of the audit trail and has value even when it identifies issues.

| Withdrawn From | Returns To |
|---------------|------------|
| IN_REVIEW | DRAFT |
| IN_APPROVAL | REVIEWED |
| POST_REVIEW | IN_EXECUTION |
| POST_APPROVAL | POST_REVIEWED |

---

## For Reviewers (qa, tu_*, bu)

### What to Look For (By Role)

#### QA -- Process Compliance

| Check | Question to Ask |
|-------|-----------------|
| **Completeness** | Are all required sections populated? Any placeholders remaining? |
| **Scope clarity** | Can a third party understand what this document authorizes from the document alone? |
| **Impact assessment** | Are all affected systems, documents, and workflows identified? |
| **Consistency** | Do the Purpose, Scope, Change Description, and Implementation Plan tell the same story? |
| **SOP conformance** | Does the document follow the applicable SOP structure and requirements? |
| **Child document strategy** | For executable documents: are EIs well-scoped? Is the testing approach adequate? |

#### QA -- Post-Review Checks

| Check | Question to Ask |
|-------|-----------------|
| **Scope integrity** | Were all approved EIs executed? None silently dropped? |
| **Evidence completeness** | Does every EI have specific, traceable evidence? |
| **Deviation handling** | Are all failures documented with child VARs or ERs? |
| **Child document status** | Are child documents in required states? (See [Post-Review Checklist](post-review-checklist.md)) |
| **Code governance** | For code CRs: is RS EFFECTIVE? RTM EFFECTIVE with real commit hash? Branch merged? |

#### Technical Units (TUs) -- Technical Accuracy

| Check | Question to Ask |
|-------|-----------------|
| **Technical correctness** | Is the proposed approach sound for the domain? |
| **Architecture compliance** | Does the change respect established patterns (Air Gap, Command pattern, SoC)? |
| **Side effects** | Are there unintended consequences the author may have missed? |
| **Completeness of change** | Are there files or modules that should be modified but are not listed? |
| **Testability** | Can the proposed changes be verified? Is the testing approach adequate for the risk level? |

#### Business Unit (bu) -- Usability and Product Value

| Check | Question to Ask |
|-------|-----------------|
| **User impact** | How does this change affect the end user's experience? |
| **Justification alignment** | Does the proposed change actually solve the stated problem? |
| **Consistency** | Does the change fit with the product's overall direction and design language? |

### Writing Useful Review Comments

**Good comments are specific, actionable, and scoped.**

| Pattern | Example |
|---------|---------|
| **Identify the issue** | "Section 5.2 describes modifying `auth.py` but Section 7.1 does not list it in Files Affected." |
| **Explain why it matters** | "This means the impact assessment is incomplete and reviewers for the affected domain may not be assigned." |
| **Suggest a resolution** | "Add `auth.py` to Section 7.1 with the change description." |

**Unhelpful comments to avoid:**

| Avoid | Why |
|-------|-----|
| "Looks good" (as the entire comment) | Provides no value to the audit trail |
| "I would have done it differently" (without identifying a defect) | Not grounds for request-updates |
| "Fix the formatting" (without specifying where) | Not actionable |
| "This seems risky" (without specifying the risk) | Vague -- name the specific failure mode |

### Recommend vs. Request-Updates

This is the core judgment call. Use this decision framework:

```
Is there a factual error, missing content, or SOP non-conformance?
  YES --> request-updates (with specific comment)
  NO  --> Is the approach technically unsound or likely to cause defects?
            YES --> request-updates (with specific comment)
            NO  --> Would you do it differently but the proposed approach is valid?
                      YES --> recommend (with optional comment noting your preference)
                      NO  --> recommend
```

**The threshold:** Request-updates means "this document has a problem that must be fixed before it can be approved." It is not "I have a preference." If the document is correct, complete, and conforming, recommend it -- even if you would have written it differently.

### "I Would Do It Differently" vs. "This Is Wrong"

| Category | Outcome | Example |
|----------|---------|---------|
| **Preference** | Recommend (with comment) | "I would use a dictionary instead of a list here, but the list approach works." |
| **Defect** | Request-updates | "This approach creates a circular import between `tools.py` and `scene.py`." |
| **Risk** | Request-updates | "The impact assessment does not mention `handlers.py`, which imports the modified function." |
| **Incompleteness** | Request-updates | "Section 8 Testing Summary is empty." |
| **Style** | Recommend (with or without comment) | "The variable name `x` is unclear but functionally correct." |

### Review Independence

Each reviewer forms their own opinion based on:
- The document content
- The applicable SOPs
- Their domain expertise

**Do not:**
- Ask the orchestrator what to focus on (they are biased toward approval)
- Coordinate with other reviewers before submitting
- Change your review based on what another reviewer submitted
- Defer to another reviewer's judgment on your domain

**The orchestrator provides:** document reference, role identity, task description.
**The orchestrator does not provide:** review criteria, expected outcome, justifications, or other reviewers' opinions.

See [Agent Orchestration](../11-Agent-Orchestration.md) for the full independence model.

---

## Quick Reference

### Commands for Authors

```bash
qms route {DOC_ID} --review       # Submit for review
qms withdraw {DOC_ID}             # Pull back from review
qms comments {DOC_ID}             # Read review feedback
qms checkout {DOC_ID}             # Check out (auto-withdraws if in review)
qms checkin {DOC_ID}              # Check in after revisions
```

### Commands for Reviewers

```bash
qms inbox                                          # See pending reviews
qms read {DOC_ID}                                  # Read document content
qms review {DOC_ID} --recommend --comment "..."    # Positive review
qms review {DOC_ID} --request-updates --comment "..." # Request changes
```

### Commands for QA (Additional)

```bash
qms assign {DOC_ID} --add tu_frontend tu_backend  # Assign reviewers
qms approve {DOC_ID}                         # Approve document
qms reject {DOC_ID} --comment "..."          # Reject document
```

---

## See Also

- [Routing Quick Reference](routing-quickref.md) -- Status transitions and routing mechanics
- [Post-Review Checklist](post-review-checklist.md) -- Post-execution review preparation
- [Workflows](../03-Workflows.md) -- Full state machine diagrams
- [Change Control](../04-Change-Control.md) -- CR-specific review team composition
- [Agent Orchestration](../11-Agent-Orchestration.md) -- Review independence and communication boundaries
- [QMS-Glossary](../QMS-Glossary.md) -- Term definitions
