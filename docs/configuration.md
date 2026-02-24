# Configuration

## Project Root Discovery

qms-cli locates the project root by searching for `qms.config.json`, walking up from the current working directory. This is the only file the CLI requires to identify a project.

## qms.config.json

Created by `qms init`. Minimal structure:

```json
{
  "version": "1.0",
  "created": "2026-01-15T14:30:00+00:00",
  "sdlc_namespaces": []
}
```

| Field | Description |
|-------|-------------|
| `version` | Config file format version |
| `created` | ISO 8601 timestamp of project initialization |
| `sdlc_namespaces` | Reserved for future use (namespaces are currently managed via `.meta/`) |

## SDLC Namespaces

Namespaces partition Requirements Specifications (RS) and Requirements Traceability Matrices (RTM) by system. Each namespace creates a pair of document types and a dedicated storage directory.

### Listing Namespaces

```bash
qms --user claude namespace list
```

### Adding a Namespace

```bash
qms --user claude namespace add FLOW
```

This registers the `FLOW` namespace, creating:
- Document types: `FLOW-RS`, `FLOW-RTM`
- Storage directory: `QMS/SDLC-FLOW/`

### Built-in Namespaces

The CLI ships with no built-in namespaces. Projects register their own via the `namespace add` command.

## Environment Variables

| Variable | Description |
|----------|-------------|
| `QMS_PROJECT_ROOT` | Override project root discovery (used by MCP server) |
