# Document Type: RS (Requirements Specification)

## Overview

RS documents are **non-executable, singleton** SDLC documents that define requirements for a controlled system. They are namespaced under an SDLC namespace (e.g., `FLOW`, `QMS`) and follow the [non-executable document workflow](../03-Workflows.md). See [SDLC](../10-SDLC.md) for the requirements framework and qualification process.

There is no RS template in `QMS/TEMPLATE/` or `qms-cli/seed/templates/`. RS documents are created with a minimal fallback template.

---

## Identity

| Property | Value |
|----------|-------|
| **Executable** | No |
| **Singleton** | Yes (one per namespace) |
| **Has Template** | No (`TEMPLATE-RS` does not exist; uses minimal fallback) |
| **Folder-per-doc** | No |
| **Parent Required** | No |

---

## Naming Convention

RS documents use the SDLC namespace naming pattern:

```
SDLC-{NAMESPACE}-RS
```

| Namespace | Document ID | Filesystem Path |
|-----------|-------------|-----------------|
| FLOW | `SDLC-FLOW-RS` | `QMS/SDLC-FLOW/SDLC-FLOW-RS.md` |
| QMS | `SDLC-QMS-RS` | `QMS/SDLC-QMS/SDLC-QMS-RS.md` |

The doc_id regex enforced by `qms_schema.py`:

```python
# Built-in pattern (hard-coded for FLOW):
"RS": re.compile(r"^SDLC-FLOW-RS$")
# QMS-RS pattern:
"QMS-RS": re.compile(r"^SDLC-QMS-RS$")
```

---

## How the CLI Creates RS Documents

### Dynamic Type Generation

RS is not a base document type in `DOCUMENT_TYPES`. Instead, the CLI dynamically generates RS types for each registered SDLC namespace via `get_all_document_types()` in `qms_config.py`:

```python
# For each namespace (e.g., FLOW):
all_types["FLOW-RS"] = {
    "path": "SDLC-FLOW",        # Filesystem directory under QMS/
    "executable": False,
    "prefix": "SDLC-FLOW-RS",   # Used as the doc_id directly (singleton)
    "singleton": True,
}
```

The `create` command type argument is the dynamic key, e.g., `FLOW-RS`:

```bash
python qms-cli/qms.py --user claude create FLOW-RS --title "My App Requirements"
```

### Singleton ID Assignment

Because `config.get("singleton")` is `True`, the create command sets:

```python
doc_id = config["prefix"]  # "SDLC-FLOW-RS"
```

No sequential numbering is used. There is exactly one RS per namespace.

### Template Fallback

When `load_template_for_type("FLOW-RS", "SDLC-FLOW-RS", title)` is called, it looks for `QMS/TEMPLATE/TEMPLATE-FLOW-RS.md`. This file does not exist, so it falls back to `create_minimal_template()`:

```python
def create_minimal_template(doc_id, title):
    frontmatter = {"title": title, "revision_summary": "Initial draft"}
    body = f"""# {doc_id}: {title}

## 1. Purpose
[Describe the purpose of this document]
---
## 2. Scope
[Define what this document covers]
---
## 3. Content
[Main content here]
---
**END OF DOCUMENT**
"""
    return frontmatter, body
```

### Initial Metadata

Created with standard non-executable initial metadata:

```json
{
    "doc_id": "SDLC-FLOW-RS",
    "doc_type": "FLOW-RS",
    "version": "0.1",
    "status": "DRAFT",
    "executable": false,
    "execution_phase": null,
    "responsible_user": "claude",
    "checked_out": true
}
```

The `.meta` file is stored at `QMS/.meta/FLOW-RS/SDLC-FLOW-RS.json`.

---

## SDLC Namespace System

### Built-in Namespaces

Defined in `qms_config.py`:

```python
SDLC_NAMESPACES = {
    "FLOW": {"path": "SDLC-FLOW"},
    "QMS": {"path": "SDLC-QMS"},
}
```

### Custom Namespaces

Additional namespaces can be registered by administrators via the `namespace add` command:

```bash
python qms-cli/qms.py --user lead namespace add ACME
```

This:
1. Creates `QMS/SDLC-ACME/` directory
2. Persists the namespace to `QMS/.meta/sdlc_namespaces.json`
3. Makes `ACME-RS` and `ACME-RTM` available as document types

Custom namespaces are merged with built-in defaults at runtime via `get_all_sdlc_namespaces()`.

### Listing Namespaces

```bash
python qms-cli/qms.py --user claude namespace list
```

Output:
```
Registered SDLC Namespaces:
============================================================
  FLOW:
    Path: SDLC-FLOW
    Types: FLOW-RS, FLOW-RTM

  QMS:
    Path: SDLC-QMS
    Types: QMS-RS, QMS-RTM
```

### Permissions

Only users in the `administrator` group (`lead`, `claude`) can add namespaces. All users can list namespaces.

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
| EFFECTIVE | Route for retirement | IN_APPROVAL (with retiring flag) |

### Approval Behavior for Non-Executable Documents

When approved, non-executable documents immediately transition through APPROVED to EFFECTIVE:

1. Draft is archived as the pre-approval version
2. Draft is promoted to effective copy (draft file renamed, `-draft` suffix removed)
3. Previous effective version (if any) is archived
4. Meta is updated: status=EFFECTIVE, version bumped to major (N+1.0), owner cleared

### Revision Cycle

When an EFFECTIVE RS is checked out for revision:
1. A new draft is created from the effective copy
2. Version incremented to `N.1` (minor from current major)
3. Effective copy remains in place (preserved per REQ-WF-020)
4. Standard review/approval cycle follows
5. On approval, new version supersedes old effective

---

## Doc Type Resolution

The `get_doc_type()` function in `qms_paths.py` resolves RS doc IDs:

```python
for namespace in get_all_sdlc_namespaces():
    prefix = f"SDLC-{namespace}-"
    if doc_id.startswith(prefix):
        suffix = doc_id.replace(prefix, "")
        if suffix in ["RS", "RTM"]:
            return f"{namespace}-{suffix}"  # e.g., "FLOW-RS"
```

---

## CLI Commands

```bash
# Create
python qms-cli/qms.py --user claude create FLOW-RS --title "My App Requirements Specification"

# Check status
python qms-cli/qms.py --user claude status SDLC-FLOW-RS

# Checkout for editing
python qms-cli/qms.py --user claude checkout SDLC-FLOW-RS

# Checkin after editing
python qms-cli/qms.py --user claude checkin SDLC-FLOW-RS

# Route for review
python qms-cli/qms.py --user claude route SDLC-FLOW-RS --review

# Route for approval
python qms-cli/qms.py --user claude route SDLC-FLOW-RS --approval
```

---

## Filesystem Layout

```
QMS/
  SDLC-FLOW/
    SDLC-FLOW-RS.md              # Effective version
    SDLC-FLOW-RS-draft.md        # Draft version (when checked out)
  .meta/
    FLOW-RS/
      SDLC-FLOW-RS.json          # Metadata sidecar
  .audit/
    FLOW-RS/
      SDLC-FLOW-RS.audit.json    # Audit trail
  .archive/
    SDLC-FLOW/
      SDLC-FLOW-RS-v1.0.md       # Archived versions
```

---

## See Also

- [SDLC](../10-SDLC.md) -- Requirements framework, verification types, qualification
- [RTM Reference](RTM.md) -- Companion document that proves RS requirements are met
- [Code Governance](../09-Code-Governance.md) -- Merge gate requires EFFECTIVE RS
- [Change Control](../04-Change-Control.md) -- CR closure prerequisites for SDLC-governed systems
- [QMS Glossary](../QMS-Glossary.md) -- Term definitions
