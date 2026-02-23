# 9. Code Governance

Source code is treated as a **qualified system** -- analogous to a validated piece of equipment in GMP manufacturing. Git is the qualified platform; branches, commits, and merges are the controlled operations performed on it. Every code change is authorized by a Change Record, executed on an isolated branch, verified through CI, and merged only after all quality gates are satisfied.

## The GMP Analogy

In pharmaceutical manufacturing, production equipment must be qualified before use: Installation Qualification (IQ), Operational Qualification (OQ), Performance Qualification (PQ). Changes to qualified equipment require change control.

Git plays the same role here. The `main` branch is the qualified state of each system. A **qualified commit** is the equivalent of an IQ/OQ/PQ milestone -- it is the CI-verified commit hash at which all tests pass and all SDLC documents are approved. Changes to `main` require a CR, an execution branch, and satisfaction of the merge gate.

## Systems

A **system** is a distinct codebase governed under the QMS. Each system lives in its own git repository (mounted as a submodule in the project root):

| System | Repository | Submodule Path |
|--------|-----------|----------------|
| *Your App* | *github.com/org/my-app* | `my-app/` |
| QMS CLI | *github.com/org/qms-cli* | `qms-cli/` |

Each system has its own [Requirements Specification (RS)](types/RS.md), [Requirements Traceability Matrix (RTM)](types/RTM.md), and release history.

## The Execution Branch Workflow

Every CR that modifies code follows this sequence:

```
main ──────────────────────────────────────────────────────► main
  │                                                           ▲
  └──► create branch ──► implement ──► test ──► qualify ──► merge
         (EI-1)           (EI-2)      (EI-3)    (EI-4)    (EI-5)
```

### Step-by-step:

| Step | Activity | Details |
|------|----------|---------|
| **1. Create execution branch** | Branch from `main` in the target system's repo | Branch name typically matches the CR (e.g., `cr-045-feature-name`) |
| **2. Implement** | Write code, commit iteratively | Commits are development artifacts -- not yet qualified |
| **3. Test** | Run test suite, verify behavior | All automated tests must pass; manual verification as needed |
| **4. Qualify** | Update SDLC documents (RS, RTM) | RS must be EFFECTIVE; RTM must be EFFECTIVE with verified requirements |
| **5. Merge** | Merge execution branch to `main` | Only after merge gate prerequisites are met |
| **6. Update submodule pointer** | In the project root, update the submodule ref | `git add my-app && git commit` to record the new qualified state |

## Development Environments

Code development happens in designated locations, never in the QMS-controlled directory tree:

| Environment | Location | Purpose |
|-------------|----------|---------|
| **Local development** | `.test-env/` | Isolated local development |
| **Production (read-only)** | Submodule paths (e.g., `my-app/`, `qms-cli/`) | The qualified codebase -- do not develop here directly |

The execution branch is created in the system's own repository, cloned or checked out in the development environment, and only merged back to `main` after qualification.

## Qualified Commits

A **qualified commit** is not just any commit that passes tests. It is the specific git commit hash representing the code state under which a System Release was qualified. It has three properties:

1. **CI-verified** -- The automated test suite passed at this exact commit
2. **RS-backed** -- An EFFECTIVE Requirements Specification defines what the system shall do
3. **RTM-verified** -- An EFFECTIVE Requirements Traceability Matrix proves the requirements are met

The qualified commit hash is recorded in the RTM's "Qualified Baseline" section. This creates a permanent, auditable link between the approved requirements, the verification evidence, and the exact code state.

> **Important:** The RTM must contain an actual CI-verified commit hash in its Qualified Baseline section, not "TBD" or a placeholder. A placeholder means qualification has not occurred.

## The Merge Gate

Code may only be merged from an execution branch to `main` when **all three prerequisites** are satisfied:

| # | Prerequisite | Verification |
|---|-------------|--------------|
| 1 | All tests pass (CI-verified) | Automated test suite runs green at the merge commit |
| 2 | RS is EFFECTIVE | The system's Requirements Specification has been approved |
| 3 | RTM is EFFECTIVE | The Requirements Traceability Matrix has been approved with all requirements verified |

If any prerequisite is not met, the merge is blocked. There is no override mechanism.

## Prohibited Merge Types

**Squash merges are prohibited.** When merging an execution branch to `main`, always use a standard merge (or fast-forward if linear).

**Why:** Squash merges rewrite the commit history into a single commit, destroying the individual commit hashes that SDLC documents (RTM qualified baselines, CR evidence) reference. A commit hash cited in an RTM as the qualified baseline must exist in the `main` branch history. Squashing makes it unreachable.

## Genesis Sandbox

Not all code starts under QMS governance. New systems that do not yet have requirements, architecture, or even a clear scope begin in a **Genesis Sandbox**.

| Aspect | Detail |
|--------|--------|
| **Branch pattern** | `genesis/{system-name}` |
| **Governance** | None -- no CRs, no reviews, no SDLC documents |
| **Purpose** | Foundational exploration, proof-of-concept, initial architecture |
| **Duration** | Until the system is mature enough to define requirements |
| **Exit** | Via an Adoption CR |

The Genesis Sandbox is explicitly outside the QMS. This is intentional -- requiring full change control for exploratory work on a system that does not yet have a requirements baseline would produce process overhead with no quality benefit.

## Adoption CRs

An **Adoption CR** is the mechanism that brings a system from the Genesis Sandbox into production governance. It bridges the gap between ungoverned exploration and qualified operation.

An Adoption CR:

1. Creates the system's first Requirements Specification (RS)
2. Creates the system's first Requirements Traceability Matrix (RTM)
3. Qualifies the existing codebase against those requirements
4. Establishes the first qualified commit and System Release
5. Merges the `genesis/` branch to `main` (through the normal merge gate)

After adoption, the system is fully governed -- all subsequent changes require CRs with the standard execution branch workflow.

## System Release Versioning

System Releases follow the format:

```
{SYSTEM}-{MAJOR}.{MINOR}
```

| Component | Meaning |
|-----------|---------|
| `{SYSTEM}` | System identifier (e.g., `FLOW-STATE`, `QMS-CLI`) |
| `{MAJOR}` | Incremented for breaking changes or major feature additions |
| `{MINOR}` | Incremented for non-breaking changes, fixes, enhancements |

**Examples:** `FLOW-STATE-1.0`, `QMS-CLI-2.3`

Each release is tied to a specific qualified commit and a pair of EFFECTIVE SDLC documents (RS + RTM).

## Rollback Procedures

### Execution Branch Rollback

If problems are discovered during execution (before merge), the execution branch can simply be abandoned or reset. No impact to `main`.

### Main Branch Rollback

If a defect is discovered after merge to `main`, rollback follows the standard change control process:

1. **Open an [Investigation](05-Deviation-Management.md)** (INV) to document the deviation
2. **Create a new [CR](04-Change-Control.md)** authorizing the fix or revert
3. **Execute the CR** on a new execution branch (which may include `git revert` of the problematic merge)
4. **Re-qualify** -- update RS/RTM if requirements changed, or verify existing requirements still pass

There is no "quick revert" outside of change control. Even reverting a bad merge requires a CR, because the revert itself changes the qualified state of the system.

## Related Documents

- [10-SDLC.md](10-SDLC.md) -- RS and RTM details, verification types, qualification
- [04-Change-Control.md](04-Change-Control.md) -- CR lifecycle and execution
- [06-Execution.md](06-Execution.md) -- Execution items and evidence capture
- [12-CLI-Reference.md](12-CLI-Reference.md) -- CLI commands for document management
- [QMS-Glossary.md](QMS-Glossary.md) -- Term definitions
