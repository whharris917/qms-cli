# 10. SDLC

The Software Development Lifecycle (SDLC) framework in this QMS is deliberately minimal. It consists of exactly two document types -- a Requirements Specification (RS) and a Requirements Traceability Matrix (RTM). There are no design documents, no architecture specs, no test plans as separate controlled documents. **The code is the design.** The RS says what the system shall do; the RTM proves it does.

## The Two-Document Framework

| Document | Purpose | Contains |
|----------|---------|----------|
| **RS (Requirements Specification)** | Define what the system shall do | Requirements only -- no implementation details |
| **RTM (Requirements Traceability Matrix)** | Prove the requirements are met | Requirement-to-code mapping + verification evidence |

That is the entire SDLC document set. Everything else -- architecture, design decisions, implementation approach -- lives in the code and its commit history.

## Requirements Specification (RS)

The RS is a [non-executable](02-Document-Control.md) controlled document listing the requirements for a system. It follows the standard [document lifecycle](03-Workflows.md): DRAFT -> IN_REVIEW -> IN_APPROVAL -> EFFECTIVE.

### Content

An RS contains:

- **System identification** -- Which system these requirements govern
- **Requirements** -- Each requirement as a discrete, testable statement
- **Revision summary** -- What changed from the previous version

The RS does not contain implementation details, design rationale, or architecture. Those belong in the code.

### Requirement ID Format

```
REQ-{TYPE}-{NNN}
```

| Component | Values | Example |
|-----------|--------|---------|
| `{TYPE}` | Domain abbreviation (e.g., `MCP`, `UI`, `SIM`, `SKETCH`) | `REQ-MCP-001` |
| `{NNN}` | Sequential number, zero-padded to 3 digits | `REQ-UI-042` |

**Examples:**

| ID | Meaning |
|----|---------|
| `REQ-MCP-001` | First requirement for the MCP subsystem |
| `REQ-UI-015` | Fifteenth requirement for the UI subsystem |
| `REQ-SIM-003` | Third requirement for the simulation subsystem |

Requirements are atomic -- each one states a single, verifiable behavior. "The system shall support lines and circles" is two requirements, not one.

## Requirements Traceability Matrix (RTM)

The RTM is the proof artifact. It maps every requirement from the RS to:

1. The code that implements it
2. The verification evidence that proves it works

### Structure

Each row in the RTM covers one requirement:

| Column | Content |
|--------|---------|
| **Requirement ID** | The REQ-{TYPE}-{NNN} from the RS |
| **Requirement text** | Copied from the RS for traceability |
| **Implementation reference** | File path(s) and function(s) that implement the requirement |
| **Verification type** | One of: unit test, qualitative proof, verification record |
| **Verification evidence** | The specific test, proof, or VR reference |
| **Status** | Verified / Not verified |

### Qualified Baseline

The RTM includes a **Qualified Baseline** section that records:

- The qualified commit hash (CI-verified)
- The System Release version
- The date of qualification

This section must contain an actual commit hash, not "TBD" or a placeholder. A placeholder means qualification has not been performed.

## Verification Types

Every requirement must be verified using one of three methods:

### 1. Unit Test

Automated, deterministic test scripts that exercise the requirement programmatically.

| Aspect | Detail |
|--------|--------|
| **When to use** | Behavior is deterministic and automatable |
| **Evidence format** | Test file path + test function name |
| **Repeatability** | Fully repeatable -- runs in CI |

**Example:**

> **REQ-MCP-005:** The CLI shall reject checkout of a document already checked out by another user.
>
> **Verification:** Unit test at `tests/test_checkout.py::test_reject_double_checkout`

### 2. Qualitative Proof

Verification requiring intelligent judgment, documented as prose with code references. Used when the requirement describes a design property, architectural constraint, or behavioral characteristic that cannot be reduced to a pass/fail test.

| Aspect | Detail |
|--------|--------|
| **When to use** | Requirement describes a structural or qualitative property |
| **Evidence format** | Prose explanation referencing specific code paths |
| **Repeatability** | Requires human or AI judgment to verify |

**Example:**

> **REQ-UI-012:** The UI framework shall use a hierarchical widget tree for rendering.
>
> **Verification (qualitative proof):** The `UIManager` class at `ui/ui_manager.py:45` maintains a root container. All widgets are added as children via `add_child()`. Rendering traverses the tree recursively via `render()` at line 112. No widget renders outside this hierarchy.

### 3. Verification Record (VR)

A pre-approved evidence form for structured behavioral verification. VRs are [child documents](07-Child-Documents.md) that capture step-by-step execution results via the [interactive authoring system](08-Interactive-Authoring.md).

| Aspect | Detail |
|--------|--------|
| **When to use** | Requirement needs structured, multi-step verification with recorded observations |
| **Evidence format** | Reference to the VR document ID (e.g., `CR-045-VR-001`) |
| **Repeatability** | Re-execution requires a new VR |

**Example:**

> **REQ-SIM-008:** Particles shall collide with static geometry boundaries.
>
> **Verification:** VR `CR-045-VR-001` -- Steps: (1) Create line entity, (2) Compile to static atoms, (3) Emit particles toward line, (4) Observe deflection. Result: PASS.

## Choosing a Verification Type

```
Is the requirement testable by an automated script?
├── Yes ──► Unit Test
└── No
    ├── Does it describe a structural/qualitative property? ──► Qualitative Proof
    └── Does it need step-by-step observed behavior? ──► Verification Record (VR)
```

## Qualification

Qualification is an **event**, not a document. There is no separate "qualification protocol" or "validation report." Qualification occurs when:

1. All requirements in the RS are verified in the RTM
2. All unit tests pass at a specific commit (CI-verified)
3. The RTM records that commit hash as the qualified baseline
4. Both the RS and RTM are EFFECTIVE (approved)

The qualified commit hash, the EFFECTIVE RS, and the EFFECTIVE RTM together constitute the qualified state of the system. The event of all three becoming true simultaneously is qualification.

### Single Commit Requirement

Qualification must reference a **single commit**. All tests must pass at one specific commit hash. You cannot qualify a system by combining test results from different commits -- that would mean the code state was never verified as a whole.

## CR Closure Prerequisites for SDLC-Governed Systems

When a [CR](types/CR.md) modifies code in a system that has SDLC documents, the CR cannot close until:

| Prerequisite | Why |
|-------------|-----|
| RS is EFFECTIVE (updated if requirements changed) | The requirements baseline must reflect the current system |
| RTM is EFFECTIVE (updated with new/changed verifications) | The proof must cover the current requirements |
| Qualified commit recorded in RTM | The code state must be documented |
| All tests pass at the qualified commit | The code must actually work |

If the CR does not change requirements (e.g., a refactor that preserves behavior), the existing RS remains valid but the RTM must still be updated to reference the new qualified commit, since the underlying code changed.

## The Principle: "The Code Is the Design"

Traditional SDLC frameworks produce design documents, architecture specifications, and detailed design descriptions as separate controlled artifacts. This QMS does not.

The code itself is the design. Architecture decisions are expressed in the code structure. Design rationale lives in commit messages, CR descriptions, and code comments. The only controlled SDLC documents are the RS (what the system shall do) and the RTM (proof it does it).

This is not anti-documentation -- it is a recognition that maintaining separate design documents in sync with rapidly evolving code creates busywork without adding safety. The RS and RTM capture the two things that matter: intent and proof.

## Related Documents

- [09-Code-Governance.md](09-Code-Governance.md) -- Execution branches, merge gate, qualified commits
- [04-Change-Control.md](04-Change-Control.md) -- CR lifecycle and execution
- [07-Child-Documents.md](07-Child-Documents.md) -- Verification Records (VRs) as child documents
- [RS Reference](types/RS.md) -- Detailed RS creation, CLI enforcement, SDLC namespaces
- [RTM Reference](types/RTM.md) -- Detailed RTM creation, qualified baseline references
- [12-CLI-Reference.md](12-CLI-Reference.md) -- CLI commands for creating and managing RS/RTM documents
- [QMS-Glossary.md](QMS-Glossary.md) -- Term definitions
