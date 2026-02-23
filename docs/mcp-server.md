# MCP Server

qms-cli includes an MCP (Model Context Protocol) server that exposes all CLI commands as native tool calls. This allows AI agents to interact with the QMS through structured tool interfaces rather than parsing CLI output.

## Starting the Server

### Stdio Transport (default)

For local use with Claude Code or other MCP clients:

```bash
python -m qms_mcp
```

The client spawns the server as a subprocess and communicates over stdin/stdout.

### Streamable HTTP Transport

For remote access (containers, networked agents):

```bash
python -m qms_mcp --transport streamable-http --port 8000
```

For container access (bind to all interfaces):

```bash
python -m qms_mcp --transport streamable-http --host 0.0.0.0 --port 8000 --project-root /path/to/project
```

### Server Options

| Flag | Description | Default |
|------|-------------|---------|
| `--transport` | Transport protocol: `stdio`, `streamable-http` | `stdio` |
| `--host` | Host address to bind | `127.0.0.1` |
| `--port` | Port to bind | `8000` |
| `--project-root` | Project root directory | Auto-discovered from cwd |

The `QMS_PROJECT_ROOT` environment variable can also set the project root.

## Configuring Claude Code

### Local (stdio)

```bash
claude mcp add qms -- python -m qms_mcp --project-root /path/to/project
```

### Remote (HTTP)

```bash
claude mcp add --transport http qms http://localhost:8000/mcp
```

### Container Access

When the MCP server runs on the host and the client runs in a Docker container:

```bash
# On host: start server
python -m qms_mcp --transport streamable-http --host 0.0.0.0 --port 8000

# In container: configure client
claude mcp add --transport http qms http://host.docker.internal:8000/mcp
```

## Available Tools

Every CLI command has a corresponding MCP tool. Tools accept the same parameters as CLI flags and return structured JSON responses.

See the [CLI Reference — MCP Equivalents](cli-reference.md#mcp-equivalents) for the complete mapping.

## Dependencies

The MCP server requires the `mcp` Python package:

```bash
pip install mcp
```

The core CLI has no external dependencies.
