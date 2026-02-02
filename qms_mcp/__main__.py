"""
Entry point for running the QMS MCP server as a module.

Usage:
    python -m qms_mcp                                              # stdio transport (default)
    python -m qms_mcp --transport streamable-http --port 8000      # streamable-http (recommended)
    python -m qms_mcp --transport sse --port 8000                  # SSE transport (deprecated)
    python -m qms_mcp --project-root /path/to/project              # explicit project root

For Docker container access:
    python -m qms_mcp --transport streamable-http --host 0.0.0.0 --port 8000 --project-root ..

Requirements: REQ-MCP-011, REQ-MCP-012, REQ-MCP-013, REQ-MCP-014
"""

from .server import main

if __name__ == "__main__":
    main()
