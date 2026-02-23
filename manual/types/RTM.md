# Document Type: RTM (Requirements Traceability Matrix)

## Overview

RTM documents are **non-executable, singleton** SDLC documents that trace requirements to their verification evidence. They are the companion to [RS](RS.md) documents: the RS defines *what* must be built, the RTM proves *that it was built and verified*. RTMs are namespaced under the same SDLC namespace system as RS documents. See [SDLC](../10-SDLC.md) for the full requirements framework and qualification process.

There is no RTM template in `QMS/TEMPLATE/` or `qms-cli/seed/templates/`. RTM documents are created with a minimal fallback template.

---

## Identity

| Property | Value |
|----------|-------|
| **Executable** | No |
| **Singleton** | Yes (one per namespace) |
| **Has Template** | No (`TEMPLATE-RTM` does not exist; uses minimal fallback) |
| **Folder-per-doc** | No |
| **Parent Required** | No |

---

## Naming Convention

RTM documents use the SDLC namespace naming pattern:

```
SDLC-{NAMESPACE}-RTM
```

| Namespace | Document ID | Filesystem Path |
|-----------|-------------|-----------------|
| FLOW | `SDLC-FLOW-RTM` | `QMS/SDLC-FLOW/SDLC-FLOW-RTM.md` |
| QMS | `SDLC-QMS-RTM` | `QMS/SDLC-QMS/SDLC-QMS-RTM.md` |

The doc_id regex enforced by `qms_schema.py`:

```python
# Built-in pattern (hard-coded for FLOW):
"RTM": re.compile(r"^SDLC-FLOW-RTM$")
# QMS-RTM pattern:
"QMS-RTM": re.compile(r"^SDLC-QMS-RTM$")
```

---

## How the CLI Creates RTM Documents

### Dynamic Type Generation

Like RS, RTM is not a base document type in `DOCUMENT_TYPES`. It is dynamically generated per namespace via `get_all_document_types()`:

```python
# For each namespace (e.g., FLOW):
all_types["FLOW-RTM"] = {
    "path": "SDLC-FLOW",          # Filesystem directory under QMS/
    "executable": False,
    "prefix": "SDLC-FLOW-RTM",    # Used as the doc_id directly (singleton)
    "singleton": True,
}
```

The `create` command type argument is the dynamic key, e.g., `FLOW-RTM`:

```bash
python qms-cli/qms.py --user claude create FLOW-RTM --title "My App Requirements Traceability Matrix"
```

### Singleton ID Assignment

Because `config.get("singleton")` is `True`, the create command sets:

```python
doc_id = config["prefix"]  # "SDLC-FLOW-RTM"
```

No sequential numbering is used. There is exactly one RTM per namespace.

### Template Fallback

When `load_template_for_type("FLOW-RTM", "SDLC-FLOW-RTM", title)` is called, it looks for `QMS/TEMPLATE/TEMPLATE-FLOW-RTM.md`. This file does not exist, so it falls back to `create_minimal_template()` which produces a generic document scaffold.

### Initial Metadata

```json
{
    "doc_id": "SDLC-FLOW-RTM",
    "doc_type": "FLOW-RTM",
    "version": "0.1",
    "status": "DRAFT",
    "executable": false,
    "execution_phase": null,
    "responsible_user": "claude",
    "checked_out": true
}
```

The `.meta` file is stored at `QMS/.meta/FLOW-RTM/SDLC-FLOW-RTM.json`.

---

## Relationship to RS and Qualified Baselines

RTMs exist in a paired relationship with RS documents within each namespace. The typical pattern during a code CR execution:

1. **RS is checked out** and requirements are added/modified
2. RS goes through review/approval and becomes EFFECTIVE
3. **Implementation** is done on a development branch
4. **Tests are written and CI passes** on the execution branch
5. **RTM is checked out** and verification evidence is recorded
6. RTM goes through review/approval and becomes EFFECTIVE
7. **Both RS and RTM must be EFFECTIVE** before code can be merged to main

### Qualified Baseline References

The RTM's primary function is to map each requirement ID from the RS to its verification evidence. The key artifact referenced in the RTM is the **[qualified commit](../09-Code-Governance.md) hash** -- the CI-verified commit on the execution branch.

Important constraints enforced by the project's SDLC process:
- The RTM must reference the **execution branch commit hash**, not the merge commit
- The qualified commit must be reachable on main via the merge commit
- RS and RTM must both reach EFFECTIVE status before the merge PR is created

### RS/RTM Concurrent Revision

RS and RTM live in the same filesystem directory (`QMS/SDLC-{NS}/`) but are independent documents. They can be checked out, edited, and approved independently. However, the SDLC process requires them to be coordinated during code CRs.

---

## SDLC Namespace System

RTM shares the same namespace infrastructure as RS. See the RS reference page for full details on:

- Built-in namespaces (`FLOW`, `QMS`)
- Custom namespace registration via `namespace add`
- Namespace persistence in `QMS/.meta/sdlc_namespaces.json`
- The `get_all_sdlc_namespaces()` merge logic

When a namespace is registered, both `{NS}-RS` and `{NS}-RTM` types become available simultaneously.

---

## Lifecycle (Non-Executable Workflow)

```
DRAFT --> IN_REVIEW --> REVIEWED --> IN_APPROVAL --> APPROVED --> EFFECTIVE
                                                                    |
                                                                    v
                                                                 RETIRED
```

### Key Transitions

| From | Action | To |
|------|--------|-----|
| DRAFT | Route for review | IN_REVIEW |
| IN_REVIEW | All reviewers recommend | REVIEWED |
| REVIEWED | Route for approval | IN_APPROVAL |
| IN_APPROVAL | All approvers approve | APPROVED -> EFFECTIVE |
| EFFECTIVE | Checkout (new revision) | DRAFT (new minor version) |

### Approval Behavior

Same as all non-executable documents. On approval:
1. Draft archived
2. Draft promoted to effective copy
3. Previous effective version archived
4. Version bumped to major (N+1.0), owner cleared
5. Status transitions: APPROVED -> EFFECTIVE (automatic)

### Revision Cycle

RTMs are frequently revised as new requirements are added to the RS and verified. Each revision cycle:
1. Checkout from EFFECTIVE creates draft at `N.1`
2. Effective copy preserved in place (REQ-WF-020)
3. After review/approval, new version becomes EFFECTIVE at `(N+1).0`

---

## Doc Type Resolution

The `get_doc_type()` function in `qms_paths.py` handles RTM identically to RS:

```python
for namespace in get_all_sdlc_namespaces():
    prefix = f"SDLC-{namespace}-"
    if doc_id.startswith(prefix):
        suffix = doc_id.replace(prefix, "")
        if suffix in ["RS", "RTM"]:
            return f"{namespace}-{suffix}"  # e.g., "FLOW-RTM"
```

---

## CLI Commands

```bash
# Create
python qms-cli/qms.py --user claude create FLOW-RTM --title "My App Requirements Traceability Matrix"

# Check status
python qms-cli/qms.py --user claude status SDLC-FLOW-RTM

# Checkout for editing
python qms-cli/qms.py --user claude checkout SDLC-FLOW-RTM

# Checkin after editing
python qms-cli/qms.py --user claude checkin SDLC-FLOW-RTM

# Route for review
python qms-cli/qms.py --user claude route SDLC-FLOW-RTM --review

# Route for approval
python qms-cli/qms.py --user claude route SDLC-FLOW-RTM --approval
```

---

## Filesystem Layout

```
QMS/
  SDLC-FLOW/
    SDLC-FLOW-RS.md              # RS effective version (companion document)
    SDLC-FLOW-RTM.md             # RTM effective version
    SDLC-FLOW-RTM-draft.md       # RTM draft version (when checked out)
  .meta/
    FLOW-RTM/
      SDLC-FLOW-RTM.json         # Metadata sidecar
  .audit/
    FLOW-RTM/
      SDLC-FLOW-RTM.audit.json   # Audit trail
  .archive/
    SDLC-FLOW/
      SDLC-FLOW-RTM-v1.0.md      # Archived versions
```

---

## See Also

- [SDLC](../10-SDLC.md) -- Verification types, qualification, the "code is the design" principle
- [RS Reference](RS.md) -- Companion document defining requirements
- [Code Governance](../09-Code-Governance.md) -- Qualified commits, merge gate, execution branches
- [Change Control](../04-Change-Control.md) -- CR closure prerequisites for SDLC-governed systems
- [QMS Glossary](../QMS-Glossary.md) -- Term definitions
