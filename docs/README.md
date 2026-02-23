# qms-cli Documentation

qms-cli is a command-line document control system. It manages the lifecycle of controlled documents — creation, review, approval, execution, and closure — using flat-file storage (Markdown, JSON metadata, JSONL audit trails).

## Quick Links

| Guide | For... |
|-------|--------|
| [Getting Started](getting-started.md) | First-time setup and your first document |
| [CLI Reference](cli-reference.md) | Every command, flag, and option |
| [Project Structure](project-structure.md) | Directory layout, metadata, audit trails |
| [Configuration](configuration.md) | qms.config.json, SDLC namespaces |
| [Users and Permissions](users-and-permissions.md) | Groups, agent definitions, permission matrix |
| [MCP Server](mcp-server.md) | Running qms-cli as an MCP tool server |

## What This Is (and Isn't)

These docs cover **how to use the tool**: commands, flags, configuration, setup. They are the software documentation for qms-cli.

For **how to operate a QMS** — policy decisions, governance philosophy, when to create which document type, evidence standards, review expectations — see the [QMS Manual](../manual/).

## Requirements

- Python 3.10+
- No external dependencies for core CLI (standard library only)
- MCP server requires the `mcp` package (`pip install mcp`)
