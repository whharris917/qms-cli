"""
QMS Write Guard Hook (PreToolUse)

Blocks direct writes to QMS-managed directories that should only be
modified through the QMS CLI. This prevents accidental corruption of
document metadata, audit trails, and archive files.

To add project-specific protected directories (e.g., governed submodules),
add entries to the PROTECTED_PATHS list below.

Hook type: PreToolUse (fires before Write/Edit operations)
Configure in .claude/settings.local.json:
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
"""

import json
import sys

# Paths that should never be written to directly.
# Add your project's governed submodules or other protected paths here.
PROTECTED_PATHS = [
    {
        "path": "QMS/.meta/",
        "message": "QMS metadata is managed by the CLI. Use qms commands instead of direct writes.",
    },
    {
        "path": "QMS/.audit/",
        "message": "QMS audit trails are managed by the CLI. Use qms commands instead of direct writes.",
    },
    {
        "path": "QMS/.archive/",
        "message": "QMS archive is managed by the CLI. Use qms commands instead of direct writes.",
    },
    {
        "path": "qms-cli/",
        "message": "qms-cli is a governed submodule. Develop in .test-env/qms-cli/ and merge to main via PR.",
    },
    # Example: add your own governed submodules here:
    # {
    #     "path": "my-app/",
    #     "message": "my-app is a governed submodule. Develop in .test-env/my-app/ and merge to main via PR.",
    # },
]


def main():
    # Read hook input from stdin
    hook_input = json.loads(sys.stdin.read())

    tool_name = hook_input.get("tool_name", "")
    tool_input = hook_input.get("tool_input", {})

    # Only check Write and Edit operations
    if tool_name not in ("Write", "Edit"):
        # Allow all other tools
        print(json.dumps({"decision": "approve"}))
        return

    file_path = tool_input.get("file_path", "")

    # Normalize path separators
    file_path = file_path.replace("\\", "/")

    for protected in PROTECTED_PATHS:
        if protected["path"] in file_path:
            print(
                json.dumps(
                    {
                        "decision": "block",
                        "reason": protected["message"],
                    }
                )
            )
            return

    # Path is not protected — allow the write
    print(json.dumps({"decision": "approve"}))


if __name__ == "__main__":
    main()
