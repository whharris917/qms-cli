# 3. Workflows

This document defines the lifecycle state machines for both executable and non-executable documents. Every transition described here is enforced by the CLI -- you cannot skip states or bypass gates.

For document type definitions and naming conventions, see [02-Document-Control.md](02-Document-Control.md).

## Non-Executable Document Lifecycle

Non-executable documents ([SOP](types/SOP.md), [RS](types/RS.md), [RTM](types/RTM.md)) follow a linear authoring-review-approval cycle.

### State Machine

```
                    ┌──────────────────────────────┐
                    │                              │
                    ▼                              │
  CREATE ──► DRAFT ──► IN_REVIEW ──► REVIEWED ──► IN_APPROVAL ──► EFFECTIVE
               ▲          │              │              │
               │          │              │              │
               │          ▼              │              ▼
               │      [withdraw]         │          [reject]
               │          │              │              │
               └──────────┘              │              │
               │                         │              │
               └─────────────────────────┘              │
               │                                        │
               └────────────────────────────────────────┘
                                                        │
                                                        │
                                          EFFECTIVE ──► RETIRED
                                         (via retire
                                          approval)
```

### Transitions

| From | To | Action | Who | Notes |
|------|----|--------|-----|-------|
| (none) | DRAFT | `create` | Initiator | Document created at version 0.1 |
| DRAFT | DRAFT | `checkout` / `checkin` | Owner | Edit cycle; version minor increments on check-in |
| DRAFT | IN_REVIEW | `route --review` | Owner | Submits for review |
| IN_REVIEW | DRAFT | `withdraw` | Owner | Pulls back from review |
| IN_REVIEW | IN_REVIEW | `review --recommend` | Reviewer | Records positive review |
| IN_REVIEW | IN_REVIEW | `review --request-updates` | Reviewer | Records review requesting changes |
| IN_REVIEW | REVIEWED | (automatic) | System | Triggers when all assigned reviewers have responded |
| REVIEWED | DRAFT | (implied by rejection logic) | Owner | If any reviewer requested updates, owner must revise and re-route |
| REVIEWED | IN_APPROVAL | `route --approval` | Owner | Only if no outstanding request-updates |
| IN_APPROVAL | EFFECTIVE | `approve` | Approver | Version increments to N.0 |
| IN_APPROVAL | REVIEWED | `reject` | Approver | Returns with rejection comment; owner must revise |
| EFFECTIVE | DRAFT | `checkout` | Owner | Starts a revision cycle (version N.1) |
| EFFECTIVE | (retire flow) | `route --approval --retire` | Owner | Initiates retirement |
| (retire approval) | RETIRED | `approve` | Approver | Terminal state |

### The Approval Gate

A document cannot be routed for approval if any reviewer submitted `request-updates`. The CLI blocks this transition. The owner must:

1. Check out the document
2. Address the requested changes
3. Check in
4. Re-route for review

Only after all reviewers recommend (or the review team is reassigned) can the document proceed to approval.

## Executable Document Lifecycle

Executable documents ([CR](types/CR.md), [INV](types/INV.md), [TP](types/TP.md), [ER](types/ER.md), [VAR](types/VAR.md), [ADD](types/ADD.md)) follow a two-phase lifecycle: **pre-execution** (authoring and approval of the plan) and **post-execution** (review and approval of the completed work).

### State Machine

```
                              PRE-EXECUTION PHASE
  ┌──────────────────────────────────────────────────────────────┐
  │                                                              │
  │  CREATE ──► DRAFT ──► IN_REVIEW ──► REVIEWED ──► IN_APPROVAL ──► PRE_APPROVED
  │               ▲          │              │              │              │
  │               │       [withdraw]        │          [reject]          │
  │               └──────────┘              │              │              │
  │               └─────────────────────────┘              │              │
  │               └────────────────────────────────────────┘              │
  │                                                                      │
  └──────────────────────────────────────────────────────────────────────┘
                                                                         │
                                                                    [release]
                                                                         │
                              POST-EXECUTION PHASE                       │
  ┌──────────────────────────────────────────────────────────────────────┘
  │                                                              │
  │  IN_EXECUTION ──► POST_REVIEW ──► POST_REVIEWED ──► POST_APPROVAL ──► POST_APPROVED
  │       ▲               │                │                  │                │
  │       │           [withdraw]           │              [reject]              │
  │       │               │                │                  │                │
  │       └───────────────┘                │                  │                │
  │       └────────────────────────────────┘                  │                │
  │       └───────────────────────────────────────────────────┘                │
  │                                                                            │
  └────────────────────────────────────────────────────────────────────────────┘
                                                                               │
                                                                           [close]
                                                                               │
                                                                               ▼
                                                                            CLOSED
```

### Pre-Execution Phase Transitions

These are identical to the non-executable lifecycle, except the approval target is `PRE_APPROVED` instead of `EFFECTIVE`.

| From | To | Action | Who | Notes |
|------|----|--------|-----|-------|
| (none) | DRAFT | `create` | Initiator | Version 0.1 |
| DRAFT | DRAFT | `checkout` / `checkin` | Owner | Edit cycle |
| DRAFT | IN_REVIEW | `route --review` | Owner | Submits plan for review |
| IN_REVIEW | DRAFT | `withdraw` | Owner | |
| IN_REVIEW | REVIEWED | (automatic) | System | All reviewers responded |
| REVIEWED | IN_APPROVAL | `route --approval` | Owner | Requires no outstanding request-updates |
| IN_APPROVAL | PRE_APPROVED | `approve` | Approver | Plan approved; version becomes N.0 |
| IN_APPROVAL | REVIEWED | `reject` | Approver | Returns with comment |

### Execution Phase Transitions

| From | To | Action | Who | Notes |
|------|----|--------|-----|-------|
| PRE_APPROVED | IN_EXECUTION | `release` | Owner | Begins execution; EIs can now be worked |
| IN_EXECUTION | IN_EXECUTION | `checkout` / `checkin` | Owner | Record evidence in executable block |
| IN_EXECUTION | POST_REVIEW | `route --review` | Owner | Submits completed work for post-review |

### Post-Execution Phase Transitions

| From | To | Action | Who | Notes |
|------|----|--------|-----|-------|
| POST_REVIEW | IN_EXECUTION | `withdraw` | Owner | Pull back for more work |
| POST_REVIEW | POST_REVIEWED | (automatic) | System | All reviewers responded |
| POST_REVIEWED | IN_EXECUTION | `revert` | Owner | Requires reason; returns to execution |
| POST_REVIEWED | POST_APPROVAL | `route --approval` | Owner | Requires no outstanding request-updates |
| POST_APPROVAL | POST_APPROVED | `approve` | Approver | Execution approved |
| POST_APPROVAL | POST_REVIEWED | `reject` | Approver | Returns with comment |
| POST_APPROVED | CLOSED | `close` | Owner | Terminal state |

### How the CLI Infers Pre/Post Phase

When you run `route --review` or `route --approval`, the CLI examines the document's current status to determine which phase applies:

| Current Status | `route --review` becomes | `route --approval` becomes |
|---------------|--------------------------|---------------------------|
| DRAFT | IN_REVIEW (pre) | (blocked -- must review first) |
| REVIEWED | (blocked -- already reviewed) | IN_APPROVAL (pre) |
| IN_EXECUTION | POST_REVIEW (post) | (blocked -- must review first) |
| POST_REVIEWED | (blocked -- already reviewed) | POST_APPROVAL (post) |

You never need to specify "pre-review" vs "post-review" -- the CLI figures it out from context.

## Verification Record (VR) Lifecycle

VRs are a special case. They are **born pre-approved** and skip the entire pre-execution phase. Their lifecycle begins at execution.

### State Machine

```
  CREATE ──► IN_EXECUTION ──► POST_REVIEW ──► POST_REVIEWED ──► POST_APPROVAL ──► POST_APPROVED
                  ▲                │                │                  │                │
                  │            [withdraw]           │              [reject]              │
                  └────────────────┘                │                  │                │
                  └────────────────────────────────┘                  │                │
                  └───────────────────────────────────────────────────┘                │
                                                                                       │
                                                                                   [close]
                                                                                       │
                                                                                       ▼
                                                                                    CLOSED
```

VRs are used for structured behavioral verification where the approval of the verification method happened as part of the parent document. The VR itself just needs to capture evidence and get post-reviewed. See [VR Reference](types/VR.md) and [Interactive Authoring](08-Interactive-Authoring.md) for the template-driven authoring system.

## Common Operations

### Review

Reviewers can submit one of two outcomes:

| Outcome | CLI Flag | Effect |
|---------|----------|--------|
| **Recommend** | `review --recommend` | Positive review; clears the reviewer's task |
| **Request Updates** | `review --request-updates` | Blocks approval routing until addressed |

Both outcomes accept an optional `--comment` for rationale or feedback.

### Rejection

Approvers can reject a document during the approval phase. Rejection:
- Requires a comment explaining the rationale
- Returns the document to the preceding reviewed state (REVIEWED or POST_REVIEWED)
- The owner must revise and re-route

### Withdrawal

Document owners can withdraw from review or approval at any time. This returns the document to its previous editable state:

| Withdrawn From | Returns To |
|---------------|------------|
| IN_REVIEW | DRAFT |
| IN_APPROVAL | REVIEWED |
| POST_REVIEW | IN_EXECUTION |
| POST_APPROVAL | POST_REVIEWED |

### Cancellation

Documents that have **never been approved** (version < 1.0) can be permanently cancelled:

```
qms cancel CR-045 --confirm
```

This is a destructive operation. It removes the document from active tracking. Documents that have been approved at least once cannot be cancelled -- they must be retired instead.

### Retirement

Effective or closed documents can be retired when they are no longer needed:

```
qms route SOP-003 --approval --retire
```

Retirement follows the approval workflow -- it requires an approver to confirm. Once retired, the document reaches a terminal state and cannot be reactivated.

### Administrative Fix

Administrators can apply minor corrections to EFFECTIVE documents without a full revision cycle:

```
qms fix SOP-001
```

This is restricted to administrators and intended for typographical corrections, not substantive changes. The fix is recorded in the audit trail.

## The Revert Operation

During post-review, the owner may discover that execution work is incomplete or needs correction. The `revert` command returns an executable document from POST_REVIEWED to IN_EXECUTION:

```
qms revert CR-045 --reason "EI-3 evidence incomplete"
```

A reason is required and is recorded in the audit trail. This allows the owner to do additional execution work before re-submitting for post-review.

## Child Document Impact on Parent Closure

Some [child documents](07-Child-Documents.md) must reach specific states before their parent can close:

| Child Type | Requirement for Parent Closure |
|------------|-------------------------------|
| **VAR (Type 1)** | Must be CLOSED |
| **VAR (Type 2)** | Must be PRE_APPROVED (or further) |
| **TP** | Must be CLOSED |
| **ER** | Must be CLOSED |
| **ADD** | Independent lifecycle (parent already CLOSED) |
| **VR** | Must be CLOSED |

The CLI enforces these prerequisites. You cannot close a parent CR if its child VAR (Type 1) is still IN_EXECUTION.

## Putting It Together: A Typical CR Lifecycle

```
1.  claude: create CR --title "Add collision detection"     → CR-092 (DRAFT, v0.1)
2.  claude: checkout CR-092                                  → Working copy in workspace
3.  claude: [edit document content]
4.  claude: checkin CR-092                                   → v0.2
5.  claude: route CR-092 --review                            → IN_REVIEW
6.  qa:     assign CR-092 --add tu_sim                       → TU added to review team
7.  qa:     review CR-092 --recommend --comment "LGTM"       → QA reviewed
8.  tu_sim: review CR-092 --recommend                        → All reviewed → REVIEWED
9.  claude: route CR-092 --approval                          → IN_APPROVAL
10. qa:     approve CR-092                                   → PRE_APPROVED (v1.0)
11. claude: release CR-092                                   → IN_EXECUTION
12. claude: checkout CR-092                                  → Edit executable block
13. claude: [complete EI-1, EI-2, EI-3 with evidence]
14. claude: checkin CR-092                                   → v1.1
15. claude: route CR-092 --review                            → POST_REVIEW
16. qa:     review CR-092 --recommend                        → POST_REVIEWED
17. claude: route CR-092 --approval                          → POST_APPROVAL
18. qa:     approve CR-092                                   → POST_APPROVED (v2.0)
19. claude: close CR-092                                     → CLOSED
```

## Further Reading

- [02-Document-Control.md](02-Document-Control.md) -- Document types, naming, versioning
- [04-Change-Control.md](04-Change-Control.md) -- CR-specific content and requirements
- [06-Execution.md](06-Execution.md) -- Executable block structure and EI documentation
- [07-Child-Documents.md](07-Child-Documents.md) -- VAR, ER, ADD, VR child document details
- [12-CLI-Reference.md](12-CLI-Reference.md) -- Full CLI command reference
- [QMS-Glossary.md](QMS-Glossary.md) -- Term definitions
