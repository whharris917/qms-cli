# Document Type: TEMPLATE

## Overview

TEMPLATE documents are **non-executable, name-based** controlled documents that define the structure and guidance for other document types. They are themselves governed by document control -- a template is a QMS document that goes through the full [non-executable review/approval lifecycle](../03-Workflows.md). This means modifying a CR template requires a [Change Record](CR.md) that modifies the template.

Templates exist in **two locations** that must stay aligned:
- **`QMS/TEMPLATE/`** -- the active QMS instance copy (governed by document control)
- **`qms-cli/seed/templates/`** -- the seed copy (governed by SDLC, used when bootstrapping new QMS instances)

---

## Identity

| Property | Value |
|----------|-------|
| **Executable** | No |
| **Singleton** | No (but name-based, not numbered) |
| **Has Template** | N/A (templates are templates) |
| **Folder-per-doc** | No |
| **Parent Required** | No |
| **Requires `--name`** | Yes |

---

## Naming Convention

TEMPLATE documents use a name-based ID pattern rather than sequential numbering:

```
TEMPLATE-{NAME}
```

The NAME must be uppercase letters only. The doc_id regex enforced by `qms_schema.py`:

```python
"TEMPLATE": re.compile(r"^TEMPLATE-[A-Z]+$")
```

| Name | Document ID | Filesystem Path |
|------|-------------|-----------------|
| CR | `TEMPLATE-CR` | `QMS/TEMPLATE/TEMPLATE-CR.md` |
| SOP | `TEMPLATE-SOP` | `QMS/TEMPLATE/TEMPLATE-SOP.md` |
| VR | `TEMPLATE-VR` | `QMS/TEMPLATE/TEMPLATE-VR.md` |
| INV | `TEMPLATE-INV` | `QMS/TEMPLATE/TEMPLATE-INV.md` |

### Existing Templates

At the time of this writing, the following templates exist in both `QMS/TEMPLATE/` and `qms-cli/seed/templates/`:

| Template ID | Purpose |
|-------------|---------|
| `TEMPLATE-CR` | Change Record |
| `TEMPLATE-SOP` | Standard Operating Procedure |
| `TEMPLATE-TP` | Test Protocol |
| `TEMPLATE-ER` | Execution Record |
| `TEMPLATE-INV` | Investigation |
| `TEMPLATE-VAR` | Variance |
| `TEMPLATE-ADD` | Addendum |
| `TEMPLATE-VR` | Verification Record |
| `TEMPLATE-TC` | Test Case |

---

## How the CLI Creates TEMPLATE Documents

### The `--name` Argument

Creating a TEMPLATE document requires the `--name` flag. The create command enforces this:

```python
if doc_type == "TEMPLATE":
    name = getattr(args, 'name', None)
    if not name:
        print("Error: TEMPLATE documents require --name argument.")
        return 1
    doc_id = f"TEMPLATE-{name.upper()}"
```

### Creation Command

```bash
python qms-cli/qms.py --user claude create TEMPLATE --name CR --title "Change Record Template"
```

### Existence Check

The create command checks both effective and draft paths. Since `TEMPLATE-CR` already exists as effective, attempting to create it again will fail:

```
Error: TEMPLATE-CR already exists
```

### Template for Templates

When a TEMPLATE is created, `load_template_for_type("TEMPLATE", "TEMPLATE-CR", title)` looks for `QMS/TEMPLATE/TEMPLATE-TEMPLATE.md`. This does not exist, so it falls back to the minimal template scaffolding.

### Initial Metadata

```json
{
    "doc_id": "TEMPLATE-CR",
    "doc_type": "TEMPLATE",
    "version": "0.1",
    "status": "DRAFT",
    "executable": false,
    "execution_phase": null,
    "responsible_user": "claude",
    "checked_out": true
}
```

The `.meta` file is stored at `QMS/.meta/TEMPLATE/TEMPLATE-CR.json`.

---

## The Dual-Copy System

### QMS Copy (`QMS/TEMPLATE/`)

This is the **active instance copy**. It is a controlled document governed by standard document control:

- Checked out / checked in via the QMS CLI
- Goes through review/approval lifecycle
- Has version history, audit trail, metadata sidecar
- Used by the CLI at runtime when creating new documents of the corresponding type

When a new document is created (e.g., `create CR --title "..."`), the function `load_template_for_type()` reads from `QMS/TEMPLATE/TEMPLATE-CR.md`:

```python
def load_template_for_type(doc_type, doc_id, title):
    template_id = f"TEMPLATE-{doc_type}"
    template_path = QMS_ROOT / "TEMPLATE" / f"{template_id}.md"
    if not template_path.exists():
        return create_minimal_template(doc_id, title)
    # ... parse and return template content
```

### Seed Copy (`qms-cli/seed/templates/`)

This is the **bootstrapping copy**. It lives inside the `qms-cli` submodule and is used:

1. When initializing a new QMS instance (the seed templates populate `QMS/TEMPLATE/`)
2. By the interactive authoring engine (`qms interact`) for VR documents
3. By the interactive checkin/checkout system for documents with `.interact` sessions
4. By the `close` command for VR auto-close compilation

The seed copy is governed by SDLC (the `qms-cli` submodule has its own CI and PR workflow), not directly by QMS document control.

### Alignment Requirement

When a CR modifies a template, **both copies must be updated**:

1. **QMS copy**: Checkout via CLI, edit, checkin (standard document control)
2. **Seed copy**: Follow the SOP-005 execution branch workflow -- develop in `.test-env/`, create execution branch, run CI, merge via PR, then update submodule pointer

CRs that modify templates should include an alignment verification EI to confirm both copies match after changes are applied.

---

## Template Document Structure

Every controlled template in `QMS/TEMPLATE/` has a specific internal structure:

### Structure Overview

```
---                                    # Template's own frontmatter (controlled)
title: Change Record Template
revision_summary: 'CR-100: description'
---

<!-- TEMPLATE DOCUMENT NOTICE -->      # Metadata comment (stripped by CLI)

---                                    # Example frontmatter (copied to new docs)
title: '{{TITLE}}'
revision_summary: 'Initial draft'
---

<!-- TEMPLATE USAGE GUIDE -->          # Author guidance (preserved in new docs)

# CR-XXX: {{TITLE}}                   # Document body with placeholders
...
```

### Two Frontmatter Blocks

Templates have **two** YAML frontmatter blocks separated by `---`:

1. **Template frontmatter** (lines 1-4): The template document's own metadata (`title`, `revision_summary`). This is what the QMS tracks as the template's controlled content.

2. **Example frontmatter** (after the TEMPLATE DOCUMENT NOTICE): The frontmatter that will be copied into new documents created from this template. Contains `{{TITLE}}` placeholder.

### Comment Blocks

**TEMPLATE DOCUMENT NOTICE**: A comment block that explains the template is a controlled document. This block is **stripped** by `strip_template_comments()` when creating a new document from the template:

```python
pattern = r'<!--\s*={70,82}\s*TEMPLATE DOCUMENT NOTICE\s*={70,82}\s*.*?={70,82}\s*-->\s*'
```

**TEMPLATE USAGE GUIDE**: A comment block providing authoring guidance for the document type. This block is **intentionally preserved** in new documents so the author can read it and then delete it manually.

### Template Parsing Logic

`load_template_for_type()` splits the template content on `---` delimiters:

```python
parts = content.split("---")
# parts[0]: before first ---
# parts[1]: template's own frontmatter
# parts[2]: between first --- and second --- (TEMPLATE DOCUMENT NOTICE)
# parts[3]: example frontmatter (parsed as YAML)
# parts[4+]: document body (joined back with ---)
```

After parsing:
- `parts[3]` is parsed as example frontmatter
- `parts[4+]` are joined back as the body
- TEMPLATE DOCUMENT NOTICE is stripped from the body
- `{{TITLE}}` is replaced with the actual title
- `{TYPE}-XXX` is replaced with the actual doc_id

---

## Interactive Templates (Tag System)

Some templates (currently only `TEMPLATE-VR`) use the **interactive template tag system** for guided authoring via `qms interact`. See [Interactive Authoring](../08-Interactive-Authoring.md) for the full system documentation. These templates embed HTML comment tags that define a state machine graph.

### Tag Vocabulary

Defined in `interact_parser.py` (REQ-INT-001):

| Tag | Syntax | Purpose |
|-----|--------|---------|
| `@template` | `@template: NAME \| version: N \| start: id` | Template header with metadata |
| `@prompt` | `@prompt: id \| next: id [\| commit: true] [\| default: value]` | Content prompt node |
| `@gate` | `@gate: id \| type: yesno \| yes: id \| no: id` | Flow-control decision node |
| `@loop` | `@loop: name` | Repeating block start |
| `@end-loop` | `@end-loop: name` | Repeating block end |
| `@end-prompt` | `@end-prompt` | Guidance boundary marker |
| `@end` | `@end` | Terminal state |

### Tag Attributes

| Attribute | Used In | Description |
|-----------|---------|-------------|
| `id` | prompt, gate | Node identifier (bare value or explicit) |
| `next` | prompt | Unconditional transition target |
| `type` | gate | Gate type (`yesno`) |
| `yes` / `no` | gate | Conditional transition targets |
| `commit` | prompt | When `true`, engine commits project state on response |
| `default` | prompt | Auto-fill value (author can override) |

### Parsed Structure

Tags are parsed into a `TemplateGraph` containing:

```python
@dataclass
class TemplateGraph:
    header: TemplateHeader     # name, version, start prompt
    nodes: dict                # id -> PromptNode | GateNode
    loops: dict                # name -> LoopDef
    raw_template: str
```

### Prompt Nodes

Each `@prompt` captures guidance text from the markdown between its tag and the next tag:

```python
@dataclass
class PromptNode:
    id: str
    next: str              # Next node ID
    commit: bool           # Trigger git commit on response
    default: Optional[str]
    guidance: str          # Extracted from markdown between tags
    loop: Optional[str]    # Loop membership
    iteration_indexed: bool
```

### Gate Nodes

Gates route flow without producing compiled content:

```python
@dataclass
class GateNode:
    id: str
    gate_type: str         # "yesno"
    yes: str               # Target on yes
    no: str                # Target on no
    guidance: str
    loop: Optional[str]
    iteration_indexed: bool
```

### Example: VR Template Tags

From `TEMPLATE-VR` (seed copy):

```markdown
<!-- @template: VR | version: 5 | start: related_eis -->

<!-- @prompt: related_eis | next: objective -->
Which execution item(s)...
<!-- @end-prompt -->

<!-- @loop: steps -->
<!-- @prompt: step_instructions | next: step_expected -->
What are you about to do?...
<!-- @prompt: step_actual | next: step_outcome | commit: true -->
What did you observe?...
<!-- @gate: more_steps | type: yesno | yes: step_instructions | no: summary_outcome -->
<!-- @end-loop: steps -->

<!-- @prompt: summary_outcome | next: summary_narrative -->
<!-- @prompt: summary_narrative | next: end -->
<!-- @end -->
```

### Placeholder Substitution

In the compiled output, `{{prompt_id}}` is replaced with the active response value. For loop-iterated prompts, `{{_n}}` is replaced with the iteration counter.

---

## Interactive Session Lifecycle

### VR Creation

When a VR document is created, the create command initializes an interactive session:

1. Reads the **seed** template (`qms-cli/seed/templates/TEMPLATE-VR.md`)
2. Parses it into a `TemplateGraph`
3. Creates a `source` data structure (`.interact` session file)
4. Saves the session to the workspace

```python
def _init_vr_interactive_session(user, doc_id, doc_type, parent_id, title, workspace_path):
    template_path = Path(__file__).parent.parent / "seed" / "templates" / f"TEMPLATE-{doc_type}.md"
    template_text = template_path.read_text(encoding="utf-8")
    graph = parse_template(template_text)
    source = create_source(doc_id=doc_id, template_name=graph.header.name, ...)
    session_path = workspace_path.parent / f"{doc_id}.interact"
    save_session(source, session_path)
```

### Interactive Checkin

When an interactive document is checked in:

1. The `.interact` session is loaded
2. The **seed** template is loaded (not the QMS copy)
3. The session is compiled to markdown via `compile_document(source, template_text)`
4. The compiled markdown is written to the QMS draft path
5. The source data is saved to `.meta/` as `{doc_id}.source.json` (permanent record)
6. The `.interact` file and workspace placeholder are cleaned up

### Interactive Checkout

When an interactive document is checked out:

1. The **seed** template is loaded
2. If `.source.json` exists in `.meta/`, it is loaded to resume the session
3. Otherwise, a new source is created
4. A new `.interact` session file is saved to workspace

---

## Lifecycle (Non-Executable Workflow)

```
DRAFT --> IN_REVIEW --> REVIEWED --> IN_APPROVAL --> APPROVED --> EFFECTIVE
```

Same as all non-executable documents. On approval:
1. Draft archived
2. Draft promoted to effective copy in `QMS/TEMPLATE/`
3. Previous effective version archived
4. Version bumped to major, owner cleared

---

## CLI Commands

```bash
# Create a new template
python qms-cli/qms.py --user claude create TEMPLATE --name CR --title "Change Record Template"

# Check status
python qms-cli/qms.py --user claude status TEMPLATE-CR

# Checkout for editing
python qms-cli/qms.py --user claude checkout TEMPLATE-CR

# Checkin after editing
python qms-cli/qms.py --user claude checkin TEMPLATE-CR

# Route for review
python qms-cli/qms.py --user claude route TEMPLATE-CR --review

# Route for approval
python qms-cli/qms.py --user claude route TEMPLATE-CR --approval
```

### Error: Missing --name

```bash
python qms-cli/qms.py --user claude create TEMPLATE --title "Some Template"
```

```
Error: TEMPLATE documents require --name argument.

Usage: qms --user {user} create TEMPLATE --name TYPE --title "Title"

Examples:
  qms --user claude create TEMPLATE --name CR --title "CR Template"
  qms --user claude create TEMPLATE --name SOP --title "SOP Template"
```

---

## Filesystem Layout

```
QMS/
  TEMPLATE/
    TEMPLATE-CR.md                # Effective (controlled) template
    TEMPLATE-CR-draft.md          # Draft (when checked out for revision)
    TEMPLATE-SOP.md
    TEMPLATE-VR.md
    ...
  .meta/
    TEMPLATE/
      TEMPLATE-CR.json            # Metadata sidecar
      TEMPLATE-SOP.json
      ...
  .audit/
    TEMPLATE/
      TEMPLATE-CR.audit.json      # Audit trail
  .archive/
    TEMPLATE/
      TEMPLATE-CR-v1.0.md         # Archived versions

qms-cli/
  seed/
    templates/
      TEMPLATE-CR.md              # Seed copy (for bootstrapping + interactive)
      TEMPLATE-SOP.md
      TEMPLATE-VR.md              # Interactive template (has @tags)
      ...
```

---

## Key Distinctions: QMS Copy vs Seed Copy

| Aspect | QMS Copy (`QMS/TEMPLATE/`) | Seed Copy (`qms-cli/seed/templates/`) |
|--------|---------------------------|---------------------------------------|
| **Governance** | QMS document control (checkout/checkin) | SDLC (CI, PR, submodule update) |
| **Used for** | Creating new documents at runtime | Bootstrapping new QMS instances; interactive engine compilation |
| **Has metadata sidecar** | Yes (`.meta/TEMPLATE/`) | No |
| **Has audit trail** | Yes (`.audit/TEMPLATE/`) | No (tracked by git) |
| **Versioned by** | QMS version (0.1, 1.0, 2.0) | Git commit history |
| **Modifiable by** | QMS CLI (checkout/edit/checkin) | Direct file edit + PR merge |
| **Template notice stripped** | Yes (on `load_template_for_type`) | No (read raw by interact engine) |

---

## See Also

- [Interactive Authoring](../08-Interactive-Authoring.md) -- Template tags, VR authoring, source data model
- [Document Control](../02-Document-Control.md) -- Document types, naming, and metadata architecture
- [VR Reference](VR.md) -- The primary interactive template consumer
- [Code Governance](../09-Code-Governance.md) -- Seed copy governance via SDLC
- [QMS Glossary](../QMS-Glossary.md) -- Term definitions
