# Routing Quick Reference

One-page cheat sheet for document routing. Shows what you can do from each status and what happens when you do it.

---

## Where Am I? What Can I Do?

### Non-Executable Documents (SOP, RS, RTM)

| Current Status | Available Actions | Result |
|---------------|-------------------|--------|
| **DRAFT** | `route --review` | IN_REVIEW |
| **DRAFT** | `checkout` / `checkin` | DRAFT (edit cycle) |
| **IN_REVIEW** | `withdraw` | DRAFT |
| **IN_REVIEW** | *(reviewers)* `review` | IN_REVIEW (until all complete, then REVIEWED) |
| **REVIEWED** | `route --approval` | IN_APPROVAL |
| **IN_APPROVAL** | *(approver)* `approve` | EFFECTIVE (v N.0) |
| **IN_APPROVAL** | *(approver)* `reject` | REVIEWED |
| **EFFECTIVE** | `checkout` | DRAFT (starts revision) |
| **EFFECTIVE** | `route --approval --retire` | (retirement approval flow) |

### Executable Documents (CR, INV, TP, ER, VAR, ADD)

| Current Status | Available Actions | Result |
|---------------|-------------------|--------|
| **DRAFT** | `route --review` | IN_REVIEW (pre) |
| **DRAFT** | `checkout` / `checkin` | DRAFT (edit cycle) |
| **IN_REVIEW** | `withdraw` | DRAFT |
| **IN_REVIEW** | *(reviewers)* `review` | IN_REVIEW until all complete, then REVIEWED |
| **REVIEWED** | `route --approval` | IN_APPROVAL (pre) |
| **IN_APPROVAL** | *(approver)* `approve` | PRE_APPROVED (v N.0) |
| **IN_APPROVAL** | *(approver)* `reject` | REVIEWED |
| **PRE_APPROVED** | `release` | IN_EXECUTION |
| **PRE_APPROVED** | `checkout` | DRAFT (scope revision -- resets to pre-approval cycle) |
| **IN_EXECUTION** | `checkout` / `checkin` | IN_EXECUTION (edit cycle, version increments) |
| **IN_EXECUTION** | `route --review` | POST_REVIEW |
| **POST_REVIEW** | `withdraw` | IN_EXECUTION |
| **POST_REVIEW** | *(reviewers)* `review` | POST_REVIEW until all complete, then POST_REVIEWED |
| **POST_REVIEWED** | `route --approval` | POST_APPROVAL |
| **POST_REVIEWED** | `revert --reason "..."` | IN_EXECUTION |
| **POST_REVIEWED** | `checkout` | IN_EXECUTION |
| **POST_APPROVAL** | *(approver)* `approve` | POST_APPROVED (v N.0) |
| **POST_APPROVAL** | *(approver)* `reject` | POST_REVIEWED |
| **POST_APPROVED** | `close` | CLOSED |

### VR (Verification Record) -- Truncated Lifecycle

| Current Status | Available Actions | Result |
|---------------|-------------------|--------|
| *(created)* | *(auto)* | IN_EXECUTION (born at v1.0, no pre-review) |
| **IN_EXECUTION** | `checkout` / `checkin` | IN_EXECUTION (edit cycle) |
| **IN_EXECUTION** | `route --review` | POST_REVIEW |
| **POST_REVIEW** | `withdraw` | IN_EXECUTION |
| **POST_REVIEWED** | `route --approval` | POST_APPROVAL |
| **POST_APPROVED** | `close` | CLOSED |

---

## Routing Sequences

### Non-Executable: DRAFT to EFFECTIVE

```
DRAFT ──route --review──> IN_REVIEW ──(all review)──> REVIEWED
      ──route --approval──> IN_APPROVAL ──(approve)──> EFFECTIVE
```

### Executable: DRAFT to CLOSED (Happy Path)

```
Pre-Execution:
  DRAFT ──route --review──> IN_REVIEW ──(all review)──> REVIEWED
        ──route --approval──> IN_APPROVAL ──(approve)──> PRE_APPROVED

Execution:
  PRE_APPROVED ──release──> IN_EXECUTION ──(do work)──> IN_EXECUTION

Post-Execution:
  IN_EXECUTION ──route --review──> POST_REVIEW ──(all review)──> POST_REVIEWED
               ──route --approval──> POST_APPROVAL ──(approve)──> POST_APPROVED
               ──close──> CLOSED
```

### VR: IN_EXECUTION to CLOSED

```
(created) ──> IN_EXECUTION ──(fill via qms interact)──> IN_EXECUTION
          ──route --review──> POST_REVIEW ──(all review)──> POST_REVIEWED
          ──route --approval──> POST_APPROVAL ──(approve)──> POST_APPROVED
          ──close──> CLOSED
```

---

## How the CLI Infers Pre/Post Phase

You never specify "pre-review" vs "post-review." The CLI determines this from the document's current status and execution phase:

| Current Status | `route --review` becomes | `route --approval` becomes |
|---------------|--------------------------|---------------------------|
| DRAFT (pre_release) | IN_REVIEW (pre) | *(blocked -- must review first)* |
| REVIEWED | *(blocked -- already reviewed)* | IN_APPROVAL (pre) |
| IN_EXECUTION | POST_REVIEW | *(blocked -- must review first)* |
| POST_REVIEWED | *(blocked -- already reviewed)* | POST_APPROVAL |

---

## Common Routing Errors

### "Approval gate not met"

**Meaning:** You tried `route --approval` but the approval gate is not satisfied.

**Check these conditions (all must be true):**

| Condition | How to Verify |
|-----------|--------------|
| All assigned reviewers submitted outcomes | `qms status {DOC_ID}` -- check reviewer list |
| No reviewer submitted `request-updates` | `qms comments {DOC_ID}` -- look for request-updates outcomes |
| At least one quality-group reviewer recommended | QA must have submitted `recommend` |

**Resolution:** If any reviewer submitted request-updates, address their feedback (checkout, revise, checkin) and re-route for review. The entire review cycle must complete again before approval routing is possible.

### "Document is checked out"

**Meaning:** You tried to route a document that is currently checked out.

**What happens:** The CLI performs an **auto-checkin** before routing. This is by design -- routing implies the document is ready. The auto-checkin:
- Copies the workspace version back to QMS storage
- Increments the minor version (for IN_EXECUTION documents)
- Archives the previous version (for IN_EXECUTION documents)
- Removes the workspace copy
- Then performs the routing

**You do not need to manually checkin before routing.** But verify your workspace content is final before routing, because the auto-checkin captures whatever is currently in the workspace.

### "Not the responsible user"

**Meaning:** You are trying to perform an owner-only action on a document you do not own.

**Who can route:** Only the document owner (the `responsible_user` in metadata). This is typically the person who created the document.

**Resolution:** Only the document owner can route, withdraw, release, revert, or close. If you need someone else's document routed, ask the owner.

### "Document status does not allow this operation"

**Meaning:** The document is not in a status that permits the action you attempted.

**Resolution:** Check `qms status {DOC_ID}` and consult the status tables above to see what actions are available from the current status.

---

## Auto-Checkin Behavior

When you route a document while it is checked out, the CLI auto-checks it in before routing. This applies to:

| Route Command | Auto-Checkin Behavior |
|--------------|----------------------|
| `route --review` from DRAFT | Checkin, then transition to IN_REVIEW |
| `route --review` from IN_EXECUTION | Checkin (with version increment and archival), then transition to POST_REVIEW |
| `route --approval` from REVIEWED | Checkin if checked out, then transition to IN_APPROVAL |
| `route --approval` from POST_REVIEWED | Checkin if checked out, then transition to POST_APPROVAL |

**Key detail for IN_EXECUTION:** Auto-checkin during routing from IN_EXECUTION increments the minor version and archives the previous version, just like a manual checkin would. The version captured at routing time is the version that reviewers see.

---

## QA's Role After Routing

When a document is routed for review:

1. **QA receives an inbox item** automatically (QA is mandatory on all reviews)
2. **QA evaluates the scope** and determines which Technical Units should review
3. **QA assigns TUs** using `qms assign {DOC_ID} --add {TU_IDs} ...`
4. **All assigned reviewers** (QA + assigned TUs/BU) evaluate independently
5. **Status advances to REVIEWED** (or POST_REVIEWED) only when all assigned reviewers have submitted

The author does not assign reviewers. QA does. The author routes; QA assigns.

---

## Action-Status Quick Reference

| Action | Who | Required Status | Result Status |
|--------|-----|----------------|---------------|
| `route --review` | Owner | DRAFT | IN_REVIEW |
| `route --review` | Owner | IN_EXECUTION | POST_REVIEW |
| `review --recommend` | Reviewer | IN_REVIEW / POST_REVIEW | Same (until all complete) |
| `review --request-updates` | Reviewer | IN_REVIEW / POST_REVIEW | Same (until all complete) |
| `route --approval` | Owner | REVIEWED | IN_APPROVAL |
| `route --approval` | Owner | POST_REVIEWED | POST_APPROVAL |
| `approve` | Approver (QA) | IN_APPROVAL | PRE_APPROVED or EFFECTIVE |
| `approve` | Approver (QA) | POST_APPROVAL | POST_APPROVED |
| `reject` | Approver (QA) | IN_APPROVAL | REVIEWED |
| `reject` | Approver (QA) | POST_APPROVAL | POST_REVIEWED |
| `withdraw` | Owner | IN_REVIEW | DRAFT |
| `withdraw` | Owner | IN_APPROVAL | REVIEWED |
| `withdraw` | Owner | POST_REVIEW | IN_EXECUTION |
| `withdraw` | Owner | POST_APPROVAL | POST_REVIEWED |
| `release` | Owner | PRE_APPROVED | IN_EXECUTION |
| `revert` | Owner | POST_REVIEWED | IN_EXECUTION |
| `close` | Owner | POST_APPROVED | CLOSED |
| `cancel` | Owner | Any (v < 1.0) | *(deleted)* |
| `route --approval --retire` | Owner | EFFECTIVE or CLOSED | (retirement approval) |

---

## See Also

- [Review Guide](review-guide.md) -- How to prepare for and conduct reviews
- [Post-Review Checklist](post-review-checklist.md) -- Post-execution review preparation
- [Document Lifecycle Quick Reference](document-lifecycle-quickref.md) -- All document types and their lifecycles
- [Workflows](../03-Workflows.md) -- Full state machine diagrams with ASCII art
- [CLI Reference](../12-CLI-Reference.md) -- Complete command documentation
- [QMS-Glossary](../QMS-Glossary.md) -- Term definitions
