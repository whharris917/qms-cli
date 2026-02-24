# Project Structure

After `qms init`, your project has this layout:

```
project-root/
├── qms.config.json              # Project root marker
├── CLAUDE.md                    # Orchestrator instructions
├── QMS/                         # Controlled documents
│   ├── CR/                      # Change Records
│   │   └── CR-001/              # One folder per CR
│   │       └── CR-001.md
│   ├── INV/                     # Investigations
│   │   └── INV-001/
│   │       └── INV-001.md
│   ├── SOP/                     # Standard Operating Procedures (flat)
│   │   └── SOP-001.md
│   ├── TEMPLATE/                # Document templates
│   │   ├── TEMPLATE-CR.md
│   │   ├── TEMPLATE-VAR.md
│   │   └── ...
│   ├── .meta/                   # Metadata (JSON sidecar files)
│   │   ├── CR/
│   │   │   └── CR-001.json
│   │   ├── TEMPLATE/
│   │   │   └── TEMPLATE-CR.json
│   │   └── ...
│   ├── .audit/                  # Audit trails (JSONL)
│   │   ├── CR/
│   │   │   └── CR-001.jsonl
│   │   └── ...
│   └── .archive/                # Superseded versions
└── .claude/
    ├── users/
    │   ├── claude/
    │   │   ├── workspace/       # Checked-out document copies
    │   │   └── inbox/           # Assigned review/approval tasks
    │   ├── qa/
    │   │   ├── workspace/
    │   │   └── inbox/
    │   └── ...
    ├── agents/                  # Agent definition files
    │   ├── qa.md
    │   └── tu.md
    └── hooks/
        └── qms-write-guard.py   # Prevents direct QMS file manipulation
```

## Three-Tier Metadata Architecture

Every controlled document has three associated files:

| Tier | Location | Format | Managed by |
|------|----------|--------|------------|
| **Content** | `QMS/{TYPE}/{DOC_ID}.md` | Markdown with YAML frontmatter | Author (via checkout/checkin) |
| **Metadata** | `QMS/.meta/{TYPE}/{DOC_ID}.json` | JSON | CLI only (never edited manually) |
| **Audit Trail** | `QMS/.audit/{TYPE}/{DOC_ID}.jsonl` | JSON Lines (append-only) | CLI only (never edited manually) |

### Frontmatter (Author-Maintained)

Documents have a minimal YAML frontmatter header with two author-maintained fields:

```yaml
---
title: "Add user authentication"
revision_summary: "Initial draft"
---
```

All other metadata (status, version, workflow state) lives in the `.meta/` sidecar file.

### Metadata Sidecar

The `.meta/` JSON file contains workflow state:

```json
{
  "doc_id": "CR-001",
  "doc_type": "CR",
  "version": "0.1",
  "status": "DRAFT",
  "executable": true,
  "responsible_user": "claude",
  "checked_out": false,
  "pending_assignees": [],
  "pending_reviewers": [],
  "completed_reviewers": [],
  "review_outcomes": {}
}
```

### Audit Trail

The `.audit/` JSONL file is append-only — one JSON object per line, one line per lifecycle event:

```json
{"timestamp": "2026-01-15T14:30:00Z", "action": "CREATE", "user": "claude", "details": {"version": "0.1"}}
{"timestamp": "2026-01-15T15:00:00Z", "action": "CHECKOUT", "user": "claude", "details": {}}
{"timestamp": "2026-01-15T16:00:00Z", "action": "CHECKIN", "user": "claude", "details": {"version": "0.2"}}
```

## Document Naming

| Type | Pattern | Example | Storage |
|------|---------|---------|---------|
| SOP | `SOP-NNN` | SOP-001 | Flat: `QMS/SOP/SOP-001.md` |
| CR | `CR-NNN` | CR-045 | Folder: `QMS/CR/CR-045/CR-045.md` |
| INV | `INV-NNN` | INV-003 | Folder: `QMS/INV/INV-003/INV-003.md` |
| TEMPLATE | `TEMPLATE-{NAME}` | TEMPLATE-CR | Flat: `QMS/TEMPLATE/TEMPLATE-CR.md` |
| VAR | `{PARENT}-VAR-NNN` | CR-045-VAR-001 | In parent folder |
| ADD | `{PARENT}-ADD-NNN` | CR-045-ADD-001 | In parent folder |
| VR | `{PARENT}-VR-NNN` | CR-045-VR-001 | In parent folder |
| TP | `{PARENT}-TP-NNN` | CR-045-TP-001 | In parent folder |
| ER | `{TP}-ER-NNN` | CR-045-TP-001-ER-001 | In parent folder |
| RS | `SDLC-{NS}-RS` | SDLC-QMS-RS | `QMS/SDLC-QMS/SDLC-QMS-RS.md` |
| RTM | `SDLC-{NS}-RTM` | SDLC-QMS-RTM | `QMS/SDLC-QMS/SDLC-QMS-RTM.md` |

## The Write Guard

The seeded hook (`.claude/hooks/qms-write-guard.py`) prevents AI agents from directly modifying files in `QMS/.meta/`, `QMS/.audit/`, and `QMS/.archive/`. All modifications to these directories must flow through the CLI.
