# Users and Permissions

## User Identity

Every CLI command requires `--user {USERNAME}` to identify the actor. The CLI resolves the user's permission group and enforces access control on every operation.

## Permission Groups

Users belong to one of four groups, arranged in a hierarchy:

| Group | Role | Inherits from |
|-------|------|---------------|
| **Administrator** | Full system access | Initiator |
| **Initiator** | Creates and manages documents through workflow | — |
| **Quality** | Assigns reviewers, reviews, approves | — |
| **Reviewer** | Reviews and approves assigned documents | — |

Administrator inherits all Initiator permissions plus administrative commands (`fix`, `user --add`).

## Default Users

`qms init` creates workspaces for four default users:

| User | Group | Purpose |
|------|-------|---------|
| `lead` | Administrator | Human project lead |
| `claude` | Administrator | AI orchestrator |
| `qa` | Quality | Quality assurance agent |
| `tu` | Reviewer | Generic technical unit reviewer |

## Adding Users

Administrators can add users with the `user` command:

```bash
qms --user lead user --add tu_backend --group reviewer
qms --user lead user --add bu --group reviewer
```

This creates:
1. An agent definition file at `.claude/agents/{username}.md`
2. Workspace and inbox directories at `.claude/users/{username}/`

## Agent Definition Files

Each non-hardcoded user has an agent definition file at `.claude/agents/{username}.md`. The file must contain YAML frontmatter with a `group` field:

```yaml
---
group: reviewer
---

# Technical Unit: Backend

You are a backend domain expert...
```

The CLI reads the `group` field to determine the user's permissions. The rest of the file is free-form — typically agent instructions for AI-driven users.

### Hardcoded Users

`lead` and `claude` are hardcoded as administrators. They do not require agent definition files, though they may have them for other purposes.

## Permission Matrix

See the [CLI Reference](cli-reference.md#permission-matrix) for the complete command-by-permission mapping.

### Key Restrictions

- **Owner-only commands:** `checkin`, `route`, `release`, `revert`, `close` — only the responsible user (the one who checked out the document) can perform these.
- **Assigned-only commands:** `review`, `approve`, `reject` — the user must be on the document's review team.
- **Quality-only commands:** `assign` — only the Quality group can assign reviewers.
- **Administrator-only commands:** `fix`, `user --add`.
