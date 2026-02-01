"""
Entry point for running the QMS MCP server as a module.

Usage:
    python -m qms_mcp                                    # stdio transport (default)
    python -m qms_mcp --transport sse --port 8000        # SSE transport
    python -m qms_mcp --project-root /path/to/project    # explicit project root

Requirements: REQ-MCP-011, REQ-MCP-012, REQ-MCP-013
"""

from .server import main

if __name__ == "__main__":
    main()
