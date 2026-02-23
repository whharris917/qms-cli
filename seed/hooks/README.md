# QMS Hooks

Hooks are scripts that run automatically in response to Claude Code events. They provide enforcement and automation without requiring manual discipline.

## Included Hooks

### qms-write-guard.py

**Type:** PreToolUse (fires before Write/Edit operations)

Blocks direct writes to QMS-managed directories:
- `QMS/.meta/` — document metadata (managed by CLI)
- `QMS/.audit/` — audit trails (managed by CLI)
- `QMS/.archive/` — version archive (managed by CLI)
- `qms-cli/` — the CLI tool itself (governed submodule)

To protect additional directories (e.g., your application's governed submodule), edit the `PROTECTED_PATHS` list in the script.

## Configuration

Hooks are configured in `.claude/settings.local.json`. The write guard hook should be configured as:

```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Write|Edit",
        "hooks": [
          {
            "type": "command",
            "command": "python .claude/hooks/qms-write-guard.py"
          }
        ]
      }
    ]
  }
}
```

## Adding Custom Hooks

You can add additional hooks for other events:
- **PreToolUse**: Fires before a tool is used (for enforcement)
- **PostToolUse**: Fires after a tool is used (for logging)
- **PreCompact**: Fires before context compaction (for state preservation)
- **SessionStart**: Fires when a session starts (for initialization)

See the Claude Code documentation for full hook configuration details.
