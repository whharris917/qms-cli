"""
QMS MCP Server Package

Exposes QMS CLI operations as MCP (Model Context Protocol) tools
for native integration with AI agents like Claude Code.

Usage:
    python -m qms_mcp
    # or
    from qms_mcp import main; main()
"""

from .server import main, mcp

__all__ = ["main", "mcp"]
