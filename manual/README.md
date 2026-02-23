# QMS Manual

Operational documentation for the Quality Management System — policy, governance philosophy, workflows, evidence standards, and review expectations. This is the "how to operate a QMS" layer.

For software documentation about the CLI tool itself (installation, commands, configuration), see [docs/](../docs/).

## Structure

| File | Covers | Source SOPs |
|------|--------|-------------|
| [01-Overview.md](01-Overview.md) | What the QMS is, the recursive governance loop, design philosophy | All |
| [02-Document-Control.md](02-Document-Control.md) | Document types, naming, versioning, statuses, directory structure, three-tier metadata | SOP-001 |
| [03-Workflows.md](03-Workflows.md) | Review, approval, rejection, release, close, cancel, retire — the full state machine | SOP-001, SOP-002 |
| [04-Change-Control.md](04-Change-Control.md) | CR content requirements, review teams, execution, post-review gates | SOP-002 |
| [05-Deviation-Management.md](05-Deviation-Management.md) | When to investigate, INV content, CAPAs, closure criteria | SOP-003 |
| [06-Execution.md](06-Execution.md) | Executable block, EI tables, evidence, scope integrity, outcome documentation | SOP-004 |
| [07-Child-Documents.md](07-Child-Documents.md) | ER, VAR, ADD, VR — lifecycle, content, naming, scope handoff | SOP-004 §9–9C |
| [08-Interactive-Authoring.md](08-Interactive-Authoring.md) | Interactive templates, source files, interaction lifecycle, response model, navigation | SOP-004 §11 |
| [09-Code-Governance.md](09-Code-Governance.md) | Execution branches, qualified commits, merge gate, genesis sandbox, adoption | SOP-005 |
| [10-SDLC.md](10-SDLC.md) | RS, RTM, verification types, qualification, CR closure prerequisites | SOP-006 |
| [11-Agent-Orchestration.md](11-Agent-Orchestration.md) | Agent roles, communication boundaries, identity, conflict resolution | SOP-007 |
| [12-CLI-Reference.md](12-CLI-Reference.md) | Consolidated command reference with examples | SOP-001 §13 |

## Related Files

- [QMS-Glossary.md](QMS-Glossary.md) — Consolidated term definitions
- [QMS-Policy.md](QMS-Policy.md) — Core policy decisions and judgment criteria
- [START_HERE.md](START_HERE.md) — Decision tree for common workflows
- [FAQ.md](FAQ.md) — Frequently asked questions
